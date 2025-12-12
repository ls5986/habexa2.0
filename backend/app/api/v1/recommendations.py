"""
Recommendations API - Intelligent order recommendations
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from app.api.deps import get_current_user
from app.services.recommendation_service import RecommendationService
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class GenerateRecommendationsRequest(BaseModel):
    supplier_id: str
    goal_type: str  # 'meet_minimum', 'target_profit', 'restock_inventory'
    goal_params: Dict[str, Any]  # Goal-specific parameters
    constraints: Optional[Dict[str, Any]] = None


class RecommendationConstraints(BaseModel):
    min_roi: float = 25.0
    max_fba_sellers: int = 30
    max_days_to_sell: int = 60
    avoid_hazmat: bool = True
    pricing_mode: str = '365d_avg'  # 'current', '30d_avg', '90d_avg', '365d_avg'


@router.post("/generate")
async def generate_recommendations(
    request: GenerateRecommendationsRequest,
    current_user = Depends(get_current_user)
):
    """
    Generate intelligent order recommendations for a supplier.
    
    Goal Types:
    - meet_minimum: Meet supplier minimum order (goal_params: {"budget": 2000})
    - target_profit: Hit profit target (goal_params: {"profit_target": 10000, "max_budget": 15000})
    - restock_inventory: Restock low inventory (goal_params: {"max_budget": 5000})
    """
    user_id = str(current_user.id)
    
    try:
        # Verify supplier belongs to user
        supplier_result = supabase.table('suppliers').select('id').eq(
            'id', request.supplier_id
        ).eq('user_id', user_id).limit(1).execute()
        
        if not supplier_result.data:
            raise HTTPException(404, "Supplier not found")
        
        # Default constraints
        constraints = request.constraints or {}
        
        # Initialize service
        service = RecommendationService(user_id)
        
        # Generate recommendations
        result = await service.generate_recommendations(
            supplier_id=request.supplier_id,
            goal_type=request.goal_type,
            goal_params=request.goal_params,
            constraints=constraints
        )
        
        if not result.get('success'):
            raise HTTPException(500, result.get('error', 'Recommendation generation failed'))
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recommendation generation failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.get("/runs/{run_id}")
async def get_recommendation_run(
    run_id: str,
    current_user = Depends(get_current_user)
):
    """Get recommendation run details with results."""
    user_id = str(current_user.id)
    
    try:
        # Get run
        run_result = supabase.table('recommendation_runs').select('*').eq(
            'id', run_id
        ).eq('user_id', user_id).limit(1).execute()
        
        if not run_result.data:
            raise HTTPException(404, "Recommendation run not found")
        
        run = run_result.data[0]
        
        # Get results
        results_result = supabase.table('recommendation_results').select(
            '''
            *,
            product:products(asin, title, image_url, brand),
            product_source:product_sources(wholesale_cost, pack_size, moq)
            '''
        ).eq('run_id', run_id).eq('user_id', user_id).order('total_score', desc=True).execute()
        
        # Get filter failures
        failures_result = supabase.table('recommendation_filter_failures').select(
            '''
            *,
            product:products(asin, title)
            '''
        ).eq('run_id', run_id).execute()
        
        return {
            'run': run,
            'results': results_result.data or [],
            'filter_failures': failures_result.data or [],
            'results_count': len(results_result.data) if results_result.data else 0
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recommendation run: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.get("/runs")
async def list_recommendation_runs(
    supplier_id: Optional[str] = None,
    limit: int = 20,
    current_user = Depends(get_current_user)
):
    """List recommendation runs for user."""
    user_id = str(current_user.id)
    
    try:
        query = supabase.table('recommendation_runs').select(
            '''
            *,
            supplier:suppliers(name)
            '''
        ).eq('user_id', user_id)
        
        if supplier_id:
            query = query.eq('supplier_id', supplier_id)
        
        result = query.order('created_at', desc=True).limit(limit).execute()
        
        return {
            'runs': result.data or [],
            'count': len(result.data) if result.data else 0
        }
    
    except Exception as e:
        logger.error(f"Failed to list runs: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.post("/runs/{run_id}/add-to-buy-list")
async def add_recommendations_to_buy_list(
    run_id: str,
    buy_list_id: Optional[str] = Body(None),
    current_user = Depends(get_current_user)
):
    """Add recommended products to a buy list."""
    user_id = str(current_user.id)
    
    try:
        # Get run and results
        run_result = supabase.table('recommendation_runs').select('id').eq(
            'id', run_id
        ).eq('user_id', user_id).limit(1).execute()
        
        if not run_result.data:
            raise HTTPException(404, "Recommendation run not found")
        
        results_result = supabase.table('recommendation_results').select('*').eq(
            'run_id', run_id
        ).eq('is_selected', True).execute()
        
        if not results_result.data:
            raise HTTPException(400, "No selected products to add")
        
        # Create buy list if needed
        if not buy_list_id:
            buy_list_data = {
                'user_id': user_id,
                'name': f'Recommendation {run_id[:8]}',
                'status': 'draft'
            }
            buy_list_result = supabase.table('buy_lists').insert(buy_list_data).execute()
            buy_list_id = buy_list_result.data[0]['id'] if buy_list_result.data else None
        
        # Add items to buy list
        items = []
        for result in results_result.data:
            items.append({
                'buy_list_id': buy_list_id,
                'product_id': result['product_id'],
                'product_source_id': result.get('product_source_id'),
                'quantity': result['recommended_quantity'],
                'unit_cost': result['recommended_cost'] / result['recommended_quantity'] if result['recommended_quantity'] > 0 else 0,
                'total_cost': result['recommended_cost'],
                'expected_profitability': result['expected_profit']
            })
        
        if items:
            supabase.table('buy_list_items').insert(items).execute()
        
        return {
            'success': True,
            'buy_list_id': buy_list_id,
            'items_added': len(items)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add to buy list: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.put("/results/{result_id}/toggle")
async def toggle_result_selection(
    result_id: str,
    is_selected: bool = Body(..., embed=True),
    current_user = Depends(get_current_user)
):
    """Toggle product selection in recommendation results."""
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        result_check = supabase.table('recommendation_results').select('id').eq(
            'id', result_id
        ).eq('user_id', user_id).limit(1).execute()
        
        if not result_check.data:
            raise HTTPException(404, "Result not found")
        
        # Update
        supabase.table('recommendation_results').update({
            'is_selected': is_selected
        }).eq('id', result_id).execute()
        
        return {'success': True, 'is_selected': is_selected}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle selection: {e}", exc_info=True)
        raise HTTPException(500, str(e))

