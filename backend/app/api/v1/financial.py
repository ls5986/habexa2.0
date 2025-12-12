"""
Financial Tracking & ROI Analysis API
Cost aggregation, sales tracking, and ROI analysis across the entire workflow.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.services.financial_aggregator import FinancialAggregator
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/financial", tags=["financial"])


@router.get("/product/{product_id}/costs")
async def get_product_costs(
    product_id: str,
    current_user=Depends(get_current_user)
):
    """Get detailed cost breakdown for a product across the entire workflow."""
    user_id = str(current_user.id)
    
    try:
        costs = FinancialAggregator.calculate_product_costs(product_id, user_id)
        return {"costs": costs}
    except Exception as e:
        logger.error(f"Error getting product costs: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get product costs: {str(e)}")


@router.get("/product/{product_id}/roi")
async def get_product_roi(
    product_id: str,
    revenue: Optional[float] = Query(None),
    current_user=Depends(get_current_user)
):
    """Get ROI analysis for a product."""
    user_id = str(current_user.id)
    
    try:
        roi = FinancialAggregator.calculate_product_roi(product_id, user_id, revenue)
        return {"roi": roi}
    except Exception as e:
        logger.error(f"Error getting product ROI: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get product ROI: {str(e)}")


@router.get("/buy-list/{buy_list_id}/costs")
async def get_buy_list_costs(
    buy_list_id: str,
    current_user=Depends(get_current_user)
):
    """Get aggregated costs for an entire buy list."""
    user_id = str(current_user.id)
    
    try:
        # Verify buy list ownership
        buy_list_check = supabase.table("buy_lists")\
            .select("id")\
            .eq("id", buy_list_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not buy_list_check.data:
            raise HTTPException(404, "Buy list not found")
        
        aggregation = FinancialAggregator.aggregate_workflow_costs(
            buy_list_id=buy_list_id,
            user_id=user_id
        )
        
        return {"cost_aggregation": aggregation}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting buy list costs: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get buy list costs: {str(e)}")


@router.get("/supplier-order/{supplier_order_id}/costs")
async def get_supplier_order_costs(
    supplier_order_id: str,
    current_user=Depends(get_current_user)
):
    """Get aggregated costs for a supplier order."""
    user_id = str(current_user.id)
    
    try:
        # Verify supplier order ownership
        order_check = supabase.table("supplier_orders")\
            .select("id")\
            .eq("id", supplier_order_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not order_check.data:
            raise HTTPException(404, "Supplier order not found")
        
        aggregation = FinancialAggregator.aggregate_workflow_costs(
            supplier_order_id=supplier_order_id,
            user_id=user_id
        )
        
        return {"cost_aggregation": aggregation}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting supplier order costs: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get supplier order costs: {str(e)}")


@router.get("/dashboard/summary")
async def get_financial_dashboard_summary(
    period: str = Query("all", regex="^(all|month|quarter|year)$"),
    current_user=Depends(get_current_user)
):
    """
    Get financial dashboard summary statistics.
    
    Returns:
        - Total costs (supplier, 3PL, shipping, fees)
        - Total revenue
        - Total profit
        - Average ROI
        - Product count
        - Unit count
    """
    user_id = str(current_user.id)
    
    try:
        # Get all products for user
        products_res = supabase.table("products")\
            .select("id")\
            .eq("user_id", user_id)\
            .execute()
        
        product_ids = [p.get("id") for p in products_res.data or []]
        
        if not product_ids:
            return {
                "total_supplier_cost": 0,
                "total_tpl_cost": 0,
                "total_shipping_cost": 0,
                "total_fba_fees": 0,
                "total_referral_fees": 0,
                "total_cost": 0,
                "total_revenue": 0,
                "total_profit": 0,
                "average_roi": 0,
                "product_count": 0,
                "unit_count": 0
            }
        
        # Aggregate costs for all products
        total_supplier_cost = 0
        total_tpl_cost = 0
        total_shipping_cost = 0
        total_fba_fees = 0
        total_referral_fees = 0
        total_revenue = 0
        total_profit = 0
        roi_values = []
        
        for product_id in product_ids:
            try:
                costs = FinancialAggregator.calculate_product_costs(product_id, user_id)
                roi_data = FinancialAggregator.calculate_product_roi(product_id, user_id)
                
                total_supplier_cost += costs.get('supplier_cost', 0)
                total_tpl_cost += costs.get('tpl_prep_cost', 0) + costs.get('tpl_storage_cost', 0)
                total_shipping_cost += costs.get('shipping_cost', 0)
                total_fba_fees += costs.get('fba_fees', 0)
                total_referral_fees += costs.get('referral_fee', 0)
                
                total_revenue += roi_data.get('revenue', 0)
                total_profit += roi_data.get('profit', 0)
                
                if roi_data.get('roi_percentage') is not None:
                    roi_values.append(roi_data.get('roi_percentage'))
            except Exception as e:
                logger.warning(f"Error calculating costs for product {product_id}: {e}")
                continue
        
        total_cost = (
            total_supplier_cost +
            total_tpl_cost +
            total_shipping_cost +
            total_fba_fees +
            total_referral_fees
        )
        
        # Calculate average ROI
        average_roi = sum(roi_values) / len(roi_values) if roi_values else 0
        
        # Get unit count from buy lists
        buy_lists_res = supabase.table("buy_lists")\
            .select("total_units")\
            .eq("user_id", user_id)\
            .execute()
        
        unit_count = sum(
            int(bl.get('total_units', 0))
            for bl in buy_lists_res.data or []
        )
        
        return {
            "total_supplier_cost": round(total_supplier_cost, 2),
            "total_tpl_cost": round(total_tpl_cost, 2),
            "total_shipping_cost": round(total_shipping_cost, 2),
            "total_fba_fees": round(total_fba_fees, 2),
            "total_referral_fees": round(total_referral_fees, 2),
            "total_cost": round(total_cost, 2),
            "total_revenue": round(total_revenue, 2),
            "total_profit": round(total_profit, 2),
            "average_roi": round(average_roi, 2),
            "product_count": len(product_ids),
            "unit_count": unit_count
        }
        
    except Exception as e:
        logger.error(f"Error getting financial dashboard summary: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get financial summary: {str(e)}")


@router.get("/dashboard/products")
async def get_financial_dashboard_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    sort_by: str = Query('roi_percentage'),
    sort_order: str = Query('desc', regex='^(asc|desc)$'),
    current_user=Depends(get_current_user)
):
    """
    Get products with financial data for dashboard table.
    Includes cost breakdown and ROI for each product.
    """
    user_id = str(current_user.id)
    
    try:
        # Get products with pagination
        offset = (page - 1) * page_size
        
        products_res = supabase.table("products")\
            .select("id, asin, title, image_url, sell_price, current_sales_rank")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .range(offset, offset + page_size - 1)\
            .execute()
        
        products = []
        for product in products_res.data or []:
            product_id = product.get("id")
            
            try:
                # Calculate costs and ROI
                costs = FinancialAggregator.calculate_product_costs(product_id, user_id)
                roi_data = FinancialAggregator.calculate_product_roi(product_id, user_id)
                
                products.append({
                    "id": product_id,
                    "asin": product.get("asin"),
                    "title": product.get("title"),
                    "image_url": product.get("image_url"),
                    "sell_price": float(product.get("sell_price", 0)) if product.get("sell_price") else None,
                    "current_sales_rank": product.get("current_sales_rank"),
                    
                    # Cost breakdown
                    "supplier_cost": costs.get("supplier_cost", 0),
                    "tpl_cost": costs.get("tpl_prep_cost", 0) + costs.get("tpl_storage_cost", 0),
                    "shipping_cost": costs.get("shipping_cost", 0),
                    "fba_fees": costs.get("fba_fees", 0),
                    "referral_fee": costs.get("referral_fee", 0),
                    "total_cost": costs.get("total_cost", 0),
                    
                    # ROI
                    "revenue": roi_data.get("revenue", 0),
                    "profit": roi_data.get("profit", 0),
                    "roi_percentage": roi_data.get("roi_percentage", 0),
                    "margin_percentage": roi_data.get("margin_percentage", 0),
                })
            except Exception as e:
                logger.warning(f"Error calculating financials for product {product_id}: {e}")
                continue
        
        # Sort products
        reverse = sort_order == 'desc'
        if sort_by == 'roi_percentage':
            products.sort(key=lambda x: x.get('roi_percentage', 0), reverse=reverse)
        elif sort_by == 'profit':
            products.sort(key=lambda x: x.get('profit', 0), reverse=reverse)
        elif sort_by == 'total_cost':
            products.sort(key=lambda x: x.get('total_cost', 0), reverse=reverse)
        elif sort_by == 'revenue':
            products.sort(key=lambda x: x.get('revenue', 0), reverse=reverse)
        
        # Get total count
        count_res = supabase.table("products")\
            .select("id", count='exact')\
            .eq("user_id", user_id)\
            .execute()
        
        total = count_res.count if hasattr(count_res, 'count') else len(products_res.data or [])
        
        return {
            "products": products,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting financial dashboard products: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get financial products: {str(e)}")


@router.post("/product/{product_id}/recalculate")
async def recalculate_product_financials(
    product_id: str,
    current_user=Depends(get_current_user)
):
    """Recalculate and store financial summary for a product."""
    user_id = str(current_user.id)
    
    try:
        # Verify product ownership
        product_check = supabase.table("products")\
            .select("id")\
            .eq("id", product_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not product_check.data:
            raise HTTPException(404, "Product not found")
        
        # Calculate costs and ROI
        costs = FinancialAggregator.calculate_product_costs(product_id, user_id)
        roi_data = FinancialAggregator.calculate_product_roi(product_id, user_id)
        
        # Get product data
        product_res = supabase.table("products")\
            .select("sell_price, fba_fees, referral_fee")\
            .eq("id", product_id)\
            .single()\
            .execute()
        
        product = product_res.data if product_res.data else {}
        
        # Create or update financial summary
        summary_data = {
            "user_id": user_id,
            "product_id": product_id,
            "supplier_cost": costs.get("supplier_cost", 0),
            "tpl_prep_cost": costs.get("tpl_prep_cost", 0),
            "tpl_storage_cost": costs.get("tpl_storage_cost", 0),
            "shipping_cost": costs.get("shipping_cost", 0),
            "fba_fees": costs.get("fba_fees", 0),
            "referral_fee": costs.get("referral_fee", 0),
            "other_fees": costs.get("other_fees", 0),
            "total_cost": costs.get("total_cost", 0),
            "sell_price": float(product.get("sell_price", 0)) if product.get("sell_price") else None,
            "revenue": roi_data.get("revenue", 0),
            "profit": roi_data.get("profit", 0),
            "roi_percentage": roi_data.get("roi_percentage"),
            "margin_percentage": roi_data.get("margin_percentage"),
            "period_type": "lifetime",
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Upsert financial summary
        summary_res = supabase.table("financial_summaries")\
            .upsert(summary_data, on_conflict="user_id,product_id,period_start,period_type")\
            .execute()
        
        # Store cost breakdown
        cost_items = []
        for cost_item in costs.get("cost_breakdown", []):
            cost_items.append({
                "user_id": user_id,
                "financial_summary_id": summary_res.data[0].get("id") if summary_res.data else None,
                "cost_type": cost_item.get("type"),
                "cost_category": cost_item.get("category"),
                "description": cost_item.get("description"),
                "amount": cost_item.get("amount"),
                "quantity": cost_item.get("quantity", 1),
                "unit_cost": cost_item.get("unit_cost"),
                "cost_date": datetime.utcnow().date().isoformat()
            })
        
        if cost_items:
            supabase.table("cost_tracking")\
                .insert(cost_items)\
                .execute()
        
        return {
            "success": True,
            "financial_summary": summary_res.data[0] if summary_res.data else None,
            "costs": costs,
            "roi": roi_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recalculating product financials: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to recalculate financials: {str(e)}")

