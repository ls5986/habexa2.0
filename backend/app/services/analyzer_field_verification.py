"""
Analyzer Field Verification
Verifies that all 45 analyzer fields are properly extracted and stored.
"""
import logging
from typing import Dict, Any, List
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)


class AnalyzerFieldVerifier:
    """
    Verifies that all analyzer fields are properly mapped and extracted.
    """
    
    # All 45 analyzer fields with their sources
    ANALYZER_FIELDS = {
        # UI Only (not stored)
        'select': {'source': 'ui', 'stored': False},
        'image': {'source': 'ui', 'stored': False},
        
        # Core Product Info
        'asin': {'source': 'sp_api', 'path': 'asin'},
        'title': {'source': 'sp_api', 'path': 'summaries[0].itemName'},
        'upc': {'source': 'user_input', 'path': 'csv_upload'},
        'package_quantity': {'source': 'sp_api', 'path': 'attributes.item_package_quantity[0].value'},
        'amazon_link': {'source': 'calculated', 'formula': 'https://amazon.com/dp/{asin}'},
        
        # Category & Classification
        'category': {'source': 'sp_api', 'path': 'summaries[0].browseClassification.displayName'},
        'subcategory': {'source': 'sp_api', 'path': 'summaries[0].browseClassification.displayName (parsed)'},
        'brand': {'source': 'sp_api', 'path': 'summaries[0].brandName'},
        'manufacturer': {'source': 'sp_api', 'path': 'attributes.manufacturer[0].value'},
        'is_top_level': {'source': 'calculated', 'formula': 'category_depth == 1'},
        
        # Pricing Data
        'wholesale_cost': {'source': 'user_input', 'path': 'csv_upload'},
        'buy_box_price': {'source': 'keepa', 'path': 'data.stats.current[0]'},
        'lowest_price_90d': {'source': 'keepa', 'path': 'MIN(data.csv[0]) over 90d'},
        'avg_buybox_90d': {'source': 'keepa', 'path': 'AVG(data.csv[0]) over 90d'},
        'list_price': {'source': 'sp_api', 'path': 'attributes.list_price[0].value.amount'},
        
        # Profitability Metrics (Calculated)
        'profit_amount': {'source': 'calculated', 'formula': 'buy_box_price - total_cost'},
        'roi_percentage': {'source': 'calculated', 'formula': '(profit / total_cost) × 100'},
        'margin_percentage': {'source': 'calculated', 'formula': '(profit / sell_price) × 100'},
        'break_even_price': {'source': 'calculated', 'formula': 'total_cost / (1 - ref_fee_pct)'},
        'profit_tier': {'source': 'calculated', 'formula': 'based on ROI ranges'},
        'is_profitable': {'source': 'calculated', 'formula': 'profit_amount > 0'},
        
        # Sales & Rank Data
        'current_sales_rank': {'source': 'keepa', 'path': 'data.stats.current[3]'},
        'avg_sales_rank_90d': {'source': 'keepa', 'path': 'AVG(data.csv[3]) over 90d'},
        'est_monthly_sales': {'source': 'calculated', 'formula': 'BSR → sales estimate'},
        'sales_rank_drops_90d': {'source': 'keepa', 'path': 'data.stats.salesRankDrops90'},
        
        # Competition Data
        'fba_seller_count': {'source': 'keepa', 'path': 'data.fbaPickupPrice count'},
        'total_seller_count': {'source': 'keepa', 'path': 'data.offerCount'},
        'amazon_in_stock': {'source': 'keepa', 'path': 'data.stats.current[1] !== -1'},
        
        # Product Dimensions
        'item_weight': {'source': 'sp_api', 'path': 'attributes.item_dimensions[0].weight.value'},
        'item_length': {'source': 'sp_api', 'path': 'attributes.item_dimensions[0].length.value'},
        'item_width': {'source': 'sp_api', 'path': 'attributes.item_dimensions[0].width.value'},
        'item_height': {'source': 'sp_api', 'path': 'attributes.item_dimensions[0].height.value'},
        
        # Fee Calculations
        'fba_fees': {'source': 'sp_api', 'path': 'feesEstimate.totalFeesEstimate.amount'},
        'referral_fee': {'source': 'sp_api', 'path': 'feesEstimate.feeDetails (filter referralFee)'},
        'variable_closing_fee': {'source': 'sp_api', 'path': 'feesEstimate.feeDetails (filter variableClosingFee)'},
        
        # Restrictions & Warnings
        'is_hazmat': {'source': 'sp_api', 'path': 'attributes.is_hazmat[0].value'},
        'is_oversized': {'source': 'calculated', 'formula': 'dimensions/weight vs FBA limits'},
        'requires_approval': {'source': 'sp_api', 'path': 'restrictions.reasons'},
        
        # Supplier Info
        'supplier_name': {'source': 'user_input', 'path': 'product_sources.supplier_id → suppliers.name'},
        
        # Review Data
        'review_count': {'source': 'keepa', 'path': 'data.reviewCount'},
        'rating': {'source': 'keepa', 'path': 'data.rating / 10'},
        
        # Metadata
        'analyzed_at': {'source': 'system', 'path': 'timestamp when calculated'},
        'created_at': {'source': 'system', 'path': 'timestamp when created'},
    }
    
    @staticmethod
    def verify_product_fields(product_id: str) -> Dict[str, Any]:
        """
        Verify that a product has all required analyzer fields populated.
        
        Returns:
            {
                'product_id': str,
                'total_fields': 45,
                'populated_fields': int,
                'missing_fields': List[str],
                'coverage_percentage': float,
                'field_status': Dict[str, bool]
            }
        """
        try:
            # Get product with all fields
            product_res = supabase.table('products')\
                .select('*')\
                .eq('id', product_id)\
                .single()\
                .execute()
            
            if not product_res.data:
                return {
                    'error': 'Product not found',
                    'product_id': product_id
                }
            
            product = product_res.data
            
            # Get product source for supplier_name
            source_res = supabase.table('product_sources')\
                .select('supplier_id, suppliers(name)')\
                .eq('product_id', product_id)\
                .limit(1)\
                .execute()
            
            supplier_name = None
            if source_res.data and source_res.data[0].get('suppliers'):
                supplier_name = source_res.data[0]['suppliers'].get('name')
            
            # Check each field
            field_status = {}
            missing_fields = []
            
            for field_name, field_info in AnalyzerFieldVerifier.ANALYZER_FIELDS.items():
                if field_info['stored'] is False:
                    # UI only field, skip
                    field_status[field_name] = True
                    continue
                
                # Check if field exists and has value
                if field_name == 'supplier_name':
                    has_value = supplier_name is not None
                elif field_name == 'subcategory':
                    # Subcategory is parsed from category
                    category = product.get('category', '')
                    has_value = bool(category and '>' in category)
                elif field_name == 'is_top_level':
                    # Calculated from category depth
                    category = product.get('category', '')
                    has_value = category is not None  # Will be calculated
                elif field_name == 'is_oversized':
                    # Calculated from dimensions
                    has_value = product.get('item_weight') is not None  # Will be calculated
                elif field_name == 'amazon_link':
                    # Calculated field
                    has_value = product.get('asin') is not None
                else:
                    # Direct field check
                    has_value = product.get(field_name) is not None
            
                field_status[field_name] = has_value
                
                if not has_value:
                    missing_fields.append(field_name)
            
            populated_count = sum(1 for v in field_status.values() if v)
            total_stored_fields = sum(1 for f in AnalyzerFieldVerifier.ANALYZER_FIELDS.values() if f.get('stored', True))
            
            return {
                'product_id': product_id,
                'total_fields': 45,
                'stored_fields': total_stored_fields,
                'populated_fields': populated_count,
                'missing_fields': missing_fields,
                'coverage_percentage': round((populated_count / total_stored_fields) * 100, 1) if total_stored_fields > 0 else 0,
                'field_status': field_status
            }
            
        except Exception as e:
            logger.error(f"Error verifying product fields: {e}", exc_info=True)
            return {
                'error': str(e),
                'product_id': product_id
            }
    
    @staticmethod
    def get_field_source_summary() -> Dict[str, Any]:
        """
        Get summary of field sources.
        """
        sources = {}
        
        for field_name, field_info in AnalyzerFieldVerifier.ANALYZER_FIELDS.items():
            source = field_info['source']
            if source not in sources:
                sources[source] = []
            sources[source].append(field_name)
        
        return {
            'total_fields': 45,
            'by_source': {
                source: {
                    'count': len(fields),
                    'fields': fields
                }
                for source, fields in sources.items()
            }
        }

