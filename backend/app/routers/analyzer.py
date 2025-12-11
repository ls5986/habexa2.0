"""
Product Analyzer Dashboard API.

Advanced filtering, sorting, bulk operations, and exports.
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import csv
import io

from app.api.deps import get_current_user
from app.services.supabase_client import supabase
from app.services.profitability_calculator import ProfitabilityCalculator

router = APIRouter(prefix="/analyzer", tags=["analyzer"])
logger = logging.getLogger(__name__)


class AnalyzerFilters(BaseModel):
    """Filters for analyzer dashboard."""
    # Text search
    search: Optional[str] = None  # ASIN or title
    
    # Category filters
    category: Optional[str] = None
    supplier_id: Optional[str] = None
    
    # Profitability filters
    min_roi: Optional[float] = None
    max_roi: Optional[float] = None
    min_margin: Optional[float] = None
    min_profit: Optional[float] = None
    profit_tier: Optional[str] = None  # 'excellent', 'good', 'marginal', 'unprofitable'
    
    # Market filters
    min_est_sales: Optional[int] = None
    max_bsr: Optional[int] = None
    max_fba_sellers: Optional[int] = None
    
    # Boolean flags
    is_profitable: Optional[bool] = None
    is_top_level: Optional[bool] = None
    amazon_sells: Optional[bool] = None
    is_hazmat: Optional[bool] = None
    is_variation: Optional[bool] = None


@router.post("/products")
async def get_analyzer_products(
    filters: AnalyzerFilters = Body(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    sort_by: str = Query('roi_percentage'),
    sort_order: str = Query('desc', regex='^(asc|desc)$'),
    current_user = Depends(get_current_user)
):
    """
    Get products for analyzer dashboard with advanced filtering.
    
    Supports:
    - Text search (ASIN, title)
    - Category/supplier filtering
    - Profitability range filtering
    - Market metrics filtering
    - Boolean flag filtering
    - Sorting on any column
    - Pagination
    """
    user_id = str(current_user.id)
    
    try:
        # Build base query - use product_deals view for joined data
        query = supabase.table('product_deals').select(
            '''
            *,
            products!inner(
                id,
                asin,
                title,
                image_url,
                category,
                brand,
                package_quantity,
                buy_box_price,
                current_sales_rank,
                fba_seller_count,
                seller_count,
                amazon_sells,
                amazon_in_stock,
                is_hazmat,
                brand_sells,
                is_variation,
                parent_asin,
                variation_count,
                profit_amount,
                roi_percentage,
                margin_percentage,
                break_even_price,
                is_profitable,
                profit_tier,
                risk_level,
                est_monthly_sales,
                sales_rank_30_day_avg,
                sales_rank_90_day_avg,
                lowest_price,
                avg_buybox_90d,
                fba_fees,
                fees_total,
                analyzed_at,
                created_at
            )
            ''',
            count='exact'
        ).eq('user_id', user_id)
        
        # Apply filters
        if filters.search:
            # Search in ASIN or title
            search_term = f"%{filters.search}%"
            # Use separate queries for OR conditions
            query = query.or_(f"products.asin.ilike.{search_term},products.title.ilike.{search_term}")
        
        if filters.category:
            query = query.eq('products.category', filters.category)
        
        if filters.supplier_id:
            query = query.eq('supplier_id', filters.supplier_id)
        
        # Profitability filters
        if filters.min_roi is not None:
            query = query.gte('products.roi_percentage', filters.min_roi)
        
        if filters.max_roi is not None:
            query = query.lte('products.roi_percentage', filters.max_roi)
        
        if filters.min_margin is not None:
            query = query.gte('products.margin_percentage', filters.min_margin)
        
        if filters.min_profit is not None:
            query = query.gte('products.profit_amount', filters.min_profit)
        
        if filters.profit_tier:
            query = query.eq('products.profit_tier', filters.profit_tier)
        
        # Market filters
        if filters.min_est_sales is not None:
            query = query.gte('products.est_monthly_sales', filters.min_est_sales)
        
        if filters.max_bsr is not None:
            query = query.lte('products.current_sales_rank', filters.max_bsr)
        
        if filters.max_fba_sellers is not None:
            query = query.lte('products.fba_seller_count', filters.max_fba_sellers)
        
        # Boolean filters
        if filters.is_profitable is not None:
            query = query.eq('products.is_profitable', filters.is_profitable)
        
        if filters.amazon_sells is not None:
            query = query.eq('products.amazon_sells', filters.amazon_sells)
        
        if filters.is_hazmat is not None:
            query = query.eq('products.is_hazmat', filters.is_hazmat)
        
        if filters.is_variation is not None:
            query = query.eq('products.is_variation', filters.is_variation)
        
        # Sorting - map frontend sort fields to database columns
        sort_field_map = {
            'roi_percentage': 'products.roi_percentage',
            'margin_percentage': 'products.margin_percentage',
            'profit_amount': 'products.profit_amount',
            'est_monthly_sales': 'products.est_monthly_sales',
            'current_sales_rank': 'products.current_sales_rank',
            'asin': 'products.asin',
            'title': 'products.title',
            'category': 'products.category',
            'fba_seller_count': 'products.fba_seller_count',
            'seller_count': 'products.seller_count',
        }
        
        db_sort_field = sort_field_map.get(sort_by, 'products.roi_percentage')
        
        if sort_order == 'desc':
            query = query.order(db_sort_field, desc=True)
        else:
            query = query.order(db_sort_field)
        
        # Pagination
        offset = (page - 1) * page_size
        query = query.range(offset, offset + page_size - 1)
        
        # Execute
        response = query.execute()
        
        # Format products for frontend
        products = []
        for item in response.data:
            # Extract product data (may be nested)
            product = item.get('products') if isinstance(item.get('products'), dict) else item
            
            products.append({
                'id': product.get('id') or item.get('product_id'),
                'deal_id': item.get('deal_id'),
                'asin': product.get('asin') or item.get('asin'),
                'title': product.get('title') or item.get('title'),
                'image_url': product.get('image_url') or item.get('image_url'),
                'category': product.get('category') or item.get('category'),
                'brand': product.get('brand') or item.get('brand'),
                'package_quantity': product.get('package_quantity') or item.get('package_quantity') or 1,
                'amazon_link': f"https://amazon.com/dp/{product.get('asin') or item.get('asin')}" if (product.get('asin') or item.get('asin')) else None,
                
                # Pricing
                'wholesale_cost': float(item.get('wholesale_cost', 0)) if item.get('wholesale_cost') else None,
                'buy_cost': float(item.get('buy_cost', 0)) if item.get('buy_cost') else None,
                'sell_price': float(product.get('buy_box_price') or item.get('sell_price', 0)) if (product.get('buy_box_price') or item.get('sell_price')) else None,
                'break_even_price': float(product.get('break_even_price', 0)) if product.get('break_even_price') else None,
                
                # Profitability
                'profit': float(product.get('profit_amount', 0)) if product.get('profit_amount') else None,
                'margin': float(product.get('margin_percentage', 0)) if product.get('margin_percentage') else None,
                'roi': float(product.get('roi_percentage', 0)) if product.get('roi_percentage') else None,
                'is_profitable': product.get('is_profitable') or item.get('is_profitable'),
                'profit_tier': product.get('profit_tier') or item.get('profit_tier'),
                'risk_level': product.get('risk_level') or item.get('risk_level'),
                
                # Market data
                'est_monthly_sales': product.get('est_monthly_sales') or item.get('est_monthly_sales'),
                'bsr': product.get('current_sales_rank') or item.get('bsr'),
                'bsr_30d': product.get('sales_rank_30_day_avg'),
                'bsr_90d': product.get('sales_rank_90_day_avg'),
                'lowest_90d': float(product.get('lowest_price', 0)) if product.get('lowest_price') else None,
                'avg_buybox_90d': float(product.get('avg_buybox_90d', 0)) if product.get('avg_buybox_90d') else None,
                
                # Competition
                'fba_sellers': product.get('fba_seller_count') or item.get('fba_seller_count'),
                'total_sellers': product.get('seller_count') or item.get('seller_count'),
                'amazon_sells': product.get('amazon_sells') or item.get('amazon_sells'),
                'amazon_in_stock': product.get('amazon_in_stock'),
                
                # Flags
                'is_hazmat': product.get('is_hazmat') or item.get('is_hazmat'),
                'brand_sells': product.get('brand_sells') or item.get('brand_sells'),
                'is_variation': product.get('is_variation') or item.get('is_variation'),
                'parent_asin': product.get('parent_asin'),
                'variation_count': product.get('variation_count'),
                'is_top_level': item.get('is_top_level_category'),
                
                # Fees
                'fba_fee': float(product.get('fba_fees', 0)) if product.get('fba_fees') else None,
                'total_fees': float(product.get('fees_total', 0)) if product.get('fees_total') else None,
                
                # Supplier
                'supplier_name': item.get('supplier_name'),
                'supplier_id': item.get('supplier_id'),
                'pack_size': item.get('pack_size', 1),
                
                # Timestamps
                'analyzed_at': product.get('analyzed_at'),
                'created_at': product.get('created_at') or item.get('deal_created_at')
            })
        
        return {
            'products': products,
            'total': response.count or 0,
            'page': page,
            'page_size': page_size,
            'total_pages': ((response.count or 0) + page_size - 1) // page_size if response.count else 0
        }
        
    except Exception as e:
        logger.error(f"Analyzer query failed: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to fetch products: {str(e)}")


@router.get("/stats")
async def get_analyzer_stats(
    current_user = Depends(get_current_user)
):
    """
    Get summary statistics for analyzer dashboard.
    """
    user_id = str(current_user.id)
    
    try:
        # Get aggregate stats from products table
        response = supabase.table('products').select(
            'profit_amount, roi_percentage, margin_percentage, is_profitable, profit_tier, est_monthly_sales'
        ).eq('user_id', user_id).execute()
        
        data = response.data or []
        
        if not data:
            return {
                'total_products': 0,
                'profitable_count': 0,
                'avg_roi': 0,
                'avg_margin': 0,
                'total_profit_potential': 0,
                'excellent_count': 0,
                'good_count': 0,
                'marginal_count': 0,
                'unprofitable_count': 0
            }
        
        # Calculate stats
        total = len(data)
        profitable = sum(1 for p in data if p.get('is_profitable'))
        
        roi_values = [p['roi_percentage'] for p in data if p.get('roi_percentage') is not None]
        avg_roi = sum(roi_values) / len(roi_values) if roi_values else 0
        
        margin_values = [p['margin_percentage'] for p in data if p.get('margin_percentage') is not None]
        avg_margin = sum(margin_values) / len(margin_values) if margin_values else 0
        
        # Monthly profit potential (profit × estimated sales)
        profit_potential = sum(
            float(p.get('profit_amount') or 0) * (p.get('est_monthly_sales') or 0)
            for p in data
        )
        
        # Count by tier
        excellent = sum(1 for p in data if p.get('profit_tier') == 'excellent')
        good = sum(1 for p in data if p.get('profit_tier') == 'good')
        marginal = sum(1 for p in data if p.get('profit_tier') == 'marginal')
        unprofitable = sum(1 for p in data if p.get('profit_tier') == 'unprofitable')
        
        return {
            'total_products': total,
            'profitable_count': profitable,
            'avg_roi': round(avg_roi, 2),
            'avg_margin': round(avg_margin, 2),
            'total_profit_potential': round(profit_potential, 2),
            'excellent_count': excellent,
            'good_count': good,
            'marginal_count': marginal,
            'unprofitable_count': unprofitable
        }
        
    except Exception as e:
        logger.error(f"Stats query failed: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to fetch stats: {str(e)}")


@router.post("/bulk-analyze")
async def bulk_analyze_products(
    product_ids: List[str] = Body(...),
    current_user = Depends(get_current_user)
):
    """
    Re-calculate profitability for multiple products.
    Useful when prices change or user wants to refresh data.
    """
    user_id = str(current_user.id)
    
    try:
        logger.info(f"🔥 Bulk analyzing {len(product_ids)} products for user {user_id}")
        
        analyzed = 0
        errors = []
        
        for product_id in product_ids:
            try:
                # Get product with source data
                product_response = supabase.table('products').select(
                    'id, asin, sell_price, amazon_price_current, buy_box_price, fba_fees, fees_total, item_weight, current_sales_rank, category, bsr'
                ).eq('id', product_id).eq('user_id', user_id).single().execute()
                
                if not product_response.data:
                    errors.append(f"{product_id}: Product not found")
                    continue
                
                product = product_response.data
                
                # Get product_source
                source_response = supabase.table('product_sources').select(
                    'id, wholesale_cost, buy_cost, pack_size'
                ).eq('product_id', product_id).limit(1).execute()
                
                if not source_response.data:
                    errors.append(f"{product.get('asin', product_id)}: No supplier cost data")
                    continue
                
                source = source_response.data[0]
                
                # Get sell price
                sell_price = product.get('sell_price') or product.get('amazon_price_current') or product.get('buy_box_price')
                if not sell_price:
                    errors.append(f"{product.get('asin', product_id)}: No sell price")
                    continue
                
                # Get costs
                wholesale_cost = source.get('wholesale_cost') or source.get('buy_cost')
                if not wholesale_cost:
                    errors.append(f"{product.get('asin', product_id)}: No wholesale cost")
                    continue
                
                # Calculate profitability
                calculated = ProfitabilityCalculator.calculate(
                    product_data=product,
                    product_source_data=source
                )
                
                # Update products table
                supabase.table('products').update({
                    'profit_amount': calculated.get('profit_amount'),
                    'roi_percentage': calculated.get('roi_percentage'),
                    'margin_percentage': calculated.get('margin_percentage'),
                    'break_even_price': calculated.get('break_even_price'),
                    'is_profitable': calculated.get('is_profitable'),
                    'profit_tier': calculated.get('profit_tier'),
                    'risk_level': calculated.get('risk_level'),
                    'est_monthly_sales': calculated.get('est_monthly_sales'),
                    'analyzed_at': datetime.utcnow().isoformat()
                }).eq('id', product_id).execute()
                
                # Update product_sources table
                supabase.table('product_sources').update({
                    'profit': calculated.get('profit_amount'),
                    'roi': calculated.get('roi_percentage'),
                    'margin': calculated.get('margin_percentage')
                }).eq('id', source['id']).execute()
                
                analyzed += 1
                
            except Exception as e:
                logger.error(f"Failed to analyze {product_id}: {e}", exc_info=True)
                errors.append(f"{product_id}: {str(e)}")
        
        logger.info(f"✅ Analyzed {analyzed}/{len(product_ids)} products")
        
        return {
            'success': True,
            'analyzed': analyzed,
            'failed': len(errors),
            'errors': errors[:10]  # First 10 errors
        }
        
    except Exception as e:
        logger.error(f"Bulk analysis failed: {e}", exc_info=True)
        raise HTTPException(500, f"Bulk analysis failed: {str(e)}")


@router.post("/export")
async def export_products(
    filters: AnalyzerFilters = Body(...),
    product_ids: Optional[List[str]] = Body(None),
    format: str = Query('csv', regex='^(csv|excel)$'),
    current_user = Depends(get_current_user)
):
    """
    Export products to CSV.
    
    Can export:
    - All products matching filters
    - Specific selected products (if product_ids provided)
    """
    user_id = str(current_user.id)
    
    try:
        # Build query using product_deals view
        query = supabase.table('product_deals').select(
            '''
            *,
            products!inner(
                asin, title, category, brand, package_quantity, 
                buy_box_price, current_sales_rank, fba_seller_count, seller_count,
                amazon_sells, is_hazmat, profit_amount, roi_percentage, margin_percentage,
                est_monthly_sales, is_profitable, profit_tier
            )
            '''
        ).eq('user_id', user_id)
        
        # If specific IDs provided, use those
        if product_ids:
            query = query.in_('product_id', product_ids)
        else:
            # Apply filters
            if filters.search:
                search_term = f"%{filters.search}%"
                query = query.or_(f"products.asin.ilike.{search_term},products.title.ilike.{search_term}")
            
            if filters.category:
                query = query.eq('products.category', filters.category)
            
            if filters.min_roi is not None:
                query = query.gte('products.roi_percentage', filters.min_roi)
        
        # Get all results (no pagination for export)
        response = query.execute()
        
        # Generate CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'ASIN', 'Title', 'Category', 'Brand', 'Package Qty',
            'Supplier', 'Wholesale Cost', 'Sell Price', 'Profit', 'ROI %', 'Margin %',
            'Est Monthly Sales', 'BSR', 'FBA Sellers', 'Total Sellers',
            'Amazon Sells?', 'Hazmat?', 'Profitable?', 'Profit Tier'
        ])
        
        writer.writeheader()
        
        for item in response.data:
            product = item.get('products') if isinstance(item.get('products'), dict) else item
            
            writer.writerow({
                'ASIN': product.get('asin') or item.get('asin'),
                'Title': product.get('title') or item.get('title'),
                'Category': product.get('category') or item.get('category'),
                'Brand': product.get('brand') or item.get('brand'),
                'Package Qty': product.get('package_quantity') or item.get('package_quantity') or 1,
                'Supplier': item.get('supplier_name'),
                'Wholesale Cost': item.get('wholesale_cost'),
                'Sell Price': product.get('buy_box_price') or item.get('sell_price'),
                'Profit': product.get('profit_amount'),
                'ROI %': product.get('roi_percentage'),
                'Margin %': product.get('margin_percentage'),
                'Est Monthly Sales': product.get('est_monthly_sales'),
                'BSR': product.get('current_sales_rank') or item.get('bsr'),
                'FBA Sellers': product.get('fba_seller_count') or item.get('fba_seller_count'),
                'Total Sellers': product.get('seller_count') or item.get('seller_count'),
                'Amazon Sells?': 'Yes' if (product.get('amazon_sells') or item.get('amazon_sells')) else 'No',
                'Hazmat?': 'Yes' if (product.get('is_hazmat') or item.get('is_hazmat')) else 'No',
                'Profitable?': 'Yes' if (product.get('is_profitable') or item.get('is_profitable')) else 'No',
                'Profit Tier': product.get('profit_tier') or item.get('profit_tier')
            })
        
        output.seek(0)
        
        # Return as downloadable file
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=habexa_products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            }
        )
        
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        raise HTTPException(500, f"Export failed: {str(e)}")


@router.get("/categories")
async def get_categories(
    current_user = Depends(get_current_user)
):
    """Get list of categories for filter dropdown."""
    user_id = str(current_user.id)
    
    try:
        response = supabase.table('products').select('category').eq(
            'user_id', user_id
        ).not_.is_('category', 'null').execute()
        
        # Get unique categories
        categories = list(set(p['category'] for p in (response.data or []) if p.get('category')))
        categories.sort()
        
        return {'categories': categories}
        
    except Exception as e:
        logger.error(f"Failed to get categories: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get categories: {str(e)}")


@router.get("/suppliers")
async def get_suppliers(
    current_user = Depends(get_current_user)
):
    """Get list of suppliers for filter dropdown."""
    user_id = str(current_user.id)
    
    try:
        response = supabase.table('suppliers').select('id, name').eq(
            'user_id', user_id
        ).execute()
        
        return {'suppliers': response.data or []}
        
    except Exception as e:
        logger.error(f"Failed to get suppliers: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to get suppliers: {str(e)}")

