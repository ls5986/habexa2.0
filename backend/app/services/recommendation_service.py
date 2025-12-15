"""
Recommendation Service

Main orchestrator for generating intelligent order recommendations.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.services.supabase_client import supabase
from app.services.recommendation_scorer import RecommendationScorer
from app.services.genius_scorer import GeniusScorer
from app.services.recommendation_filter import RecommendationFilter
from app.services.recommendation_optimizer import RecommendationOptimizer

logger = logging.getLogger(__name__)


class RecommendationService:
    """Generate intelligent order recommendations."""
    
    def __init__(self, user_id: str, use_genius_scorer: bool = True):
        self.user_id = user_id
        self.use_genius_scorer = use_genius_scorer
        self.scorer = RecommendationScorer()  # Legacy scorer (fallback)
        self.genius_scorer = GeniusScorer()  # New genius scorer
        self.filter = RecommendationFilter()
        self.optimizer = RecommendationOptimizer()
    
    async def generate_recommendations(
        self,
        supplier_id: str,
        goal_type: str,
        goal_params: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate recommendations for a supplier.
        
        Args:
            supplier_id: Supplier ID
            goal_type: 'meet_minimum', 'target_profit', 'restock_inventory'
            goal_params: Goal-specific parameters
            constraints: Filters and constraints
        
        Returns:
            Recommendation run results
        """
        try:
            # Update filter and scorer with constraints
            self.filter = RecommendationFilter(
                min_roi=constraints.get('min_roi', 25.0),
                max_fba_sellers=constraints.get('max_fba_sellers', 30),
                max_days_to_sell=constraints.get('max_days_to_sell', 60),
                avoid_hazmat=constraints.get('avoid_hazmat', True),
                pricing_mode=constraints.get('pricing_mode', '365d_avg')
            )
            
            self.scorer = RecommendationScorer(
                pricing_mode=constraints.get('pricing_mode', '365d_avg')
            )
            
            # Get all products for supplier
            products_result = supabase.table('products').select(
                '''
                *,
                product_sources!inner(
                    *,
                    supplier:suppliers(*)
                )
                '''
            ).eq('product_sources.supplier_id', supplier_id).eq('user_id', self.user_id).execute()
            
            if not products_result.data:
                return {
                    'success': False,
                    'error': 'No products found for supplier'
                }
            
            # Create recommendation run
            run_id = await self._create_recommendation_run(
                supplier_id, goal_type, goal_params, constraints
            )
            
            # Process products
            scored_products = []
            filter_failures = []
            products_analyzed = 0
            products_passed = 0
            products_failed = 0
            
            for item in products_result.data:
                products_analyzed += 1
                product = item
                product_source = item.get('product_sources', [{}])[0] if item.get('product_sources') else {}
                
                # Check brand restrictions (from product_brand_flags if exists)
                brand_status = None
                product_id = product.get('id')
                if product_id:
                    try:
                        brand_flag_result = supabase.table('product_brand_flags').select('brand_status').eq(
                            'product_id', product_id
                        ).eq('user_id', self.user_id).limit(1).execute()
                        
                        if brand_flag_result.data:
                            brand_status = brand_flag_result.data[0].get('brand_status')
                    except:
                        pass  # If no brand flag, assume unknown/unrestricted
                
                # Apply filters
                should_include, failure_reason = self.filter.should_include(
                    product, product_source, brand_status
                )
                
                if not should_include:
                    products_failed += 1
                    filter_failures.append({
                        'product_id': product.get('id'),
                        'filter_name': failure_reason or 'unknown',
                        'run_id': run_id
                    })
                    continue
                
                products_passed += 1
                
                # Calculate score using Genius Scorer or legacy scorer
                if self.use_genius_scorer:
                    # Use Genius Scorer
                    try:
                        # Get Keepa data
                        keepa_data = product.get('keepa_raw_response', {}) or {}
                        if isinstance(keepa_data, str):
                            import json
                            try:
                                keepa_data = json.loads(keepa_data)
                            except:
                                keepa_data = {}
                        
                        # Prepare product data for genius scorer
                        product_data = {
                            'roi': float(product.get('roi', 0) or product_source.get('roi', 0)),
                            'profit_per_unit': float(product.get('profit_per_unit', 0) or product_source.get('profit_per_unit', 0)),
                            'margin': float(product.get('margin', 0) or product_source.get('margin', 0)),
                            'is_brand_restricted': brand_status in ['globally_restricted', 'supplier_restricted'],
                            'order_quantity': 100
                        }
                        
                        # Prepare SP-API data
                        sp_api_data = {
                            'sales_rank': product.get('current_sales_rank', 999999) or product.get('sales_rank', 999999),
                            'category': product.get('category', 'default'),
                            'fba_seller_count': product.get('fba_seller_count', 0),
                            'is_hazmat': product.get('is_hazmat', False)
                        }
                        
                        # User config
                        user_config = {
                            'min_roi': constraints.get('min_roi', 25.0),
                            'max_fba_sellers': constraints.get('max_fba_sellers', 30),
                            'handles_hazmat': not constraints.get('avoid_hazmat', True)
                        }
                        
                        # Calculate genius score
                        genius_result = self.genius_scorer.calculate_genius_score(
                            product_data=product_data,
                            keepa_data=keepa_data,
                            sp_api_data=sp_api_data,
                            user_config=user_config
                        )
                        
                        # Convert genius result to legacy format for compatibility
                        score_result = {
                            'total_score': genius_result['total_score'],
                            'profitability_score': genius_result['breakdown']['profitability'],
                            'velocity_score': genius_result['breakdown']['velocity'],
                            'competition_score': genius_result['breakdown']['competition'],
                            'risk_score': genius_result['breakdown']['risk'],
                            'breakdown': genius_result['component_scores'],
                            'genius_grade': genius_result['grade'],
                            'genius_badge': genius_result['badge'],
                            'genius_insights': genius_result['insights']
                        }
                    except Exception as e:
                        logger.warning(f"Genius scoring failed for product {product.get('id')}, using legacy scorer: {e}")
                        # Fallback to legacy scorer
                        score_result = self.scorer.calculate_score(product, product_source)
                else:
                    # Use legacy scorer
                    score_result = self.scorer.calculate_score(product, product_source)
                
                # Calculate unit cost and profit
                wholesale_cost = float(product_source.get('wholesale_cost', 0))
                pack_size = product_source.get('pack_size', 1) or 1
                unit_cost = wholesale_cost / pack_size if pack_size > 0 else wholesale_cost
                
                sell_price = self.scorer._get_price_for_mode(product)
                fba_fee = float(product.get('fba_fees', 0))
                referral_pct = float(product.get('referral_fee_percentage', 15.0))
                referral_fee = sell_price * (referral_pct / 100)
                total_fees = fba_fee + referral_fee
                total_cost = unit_cost + 0.10 + 0.50 + total_fees
                profit_per_unit = sell_price - total_cost
                
                # Build product data for optimizer
                scored_product = {
                    'product_id': product.get('id'),
                    'product_source_id': product_source.get('id'),
                    'asin': product.get('asin'),
                    'title': product.get('title'),
                    'brand': product.get('brand'),
                    'score': score_result['total_score'],
                    'profitability_score': score_result['profitability_score'],
                    'velocity_score': score_result['velocity_score'],
                    'competition_score': score_result['competition_score'],
                    'risk_score': score_result['risk_score'],
                    'unit_cost': unit_cost,
                    'profit_per_unit': profit_per_unit,
                    'pack_size': pack_size,
                    'monthly_sales': product.get('est_monthly_sales', 0),
                    'fba_sellers': product.get('fba_seller_count', 0),
                    'sell_price': sell_price,
                    'roi': (profit_per_unit / total_cost * 100) if total_cost > 0 else 0,
                    'breakdown': score_result.get('breakdown', {}),
                    # Add genius score data if available
                    'genius_grade': score_result.get('genius_grade'),
                    'genius_badge': score_result.get('genius_badge'),
                    'genius_insights': score_result.get('genius_insights', {})
                }
                
                scored_products.append(scored_product)
            
            # Store filter failures
            if filter_failures:
                supabase.table('recommendation_filter_failures').insert(filter_failures).execute()
            
            # Optimize based on goal
            if goal_type == 'meet_minimum':
                budget = goal_params.get('budget', 0)
                result = self.optimizer.optimize_for_budget(
                    scored_products,
                    budget=budget,
                    max_days_to_sell=constraints.get('max_days_to_sell')
                )
            
            elif goal_type == 'target_profit':
                profit_target = goal_params.get('profit_target', 0)
                max_budget = goal_params.get('max_budget')
                result = self.optimizer.optimize_for_profit(
                    scored_products,
                    profit_target=profit_target,
                    max_budget=max_budget,
                    fast_pct=goal_params.get('fast_pct', 0.60),
                    medium_pct=goal_params.get('medium_pct', 0.30),
                    slow_pct=goal_params.get('slow_pct', 0.10)
                )
            
            elif goal_type == 'restock_inventory':
                # TODO: Get current inventory and reorder points
                current_inventory = {}  # Placeholder
                reorder_points = {}  # Placeholder
                max_budget = goal_params.get('max_budget')
                
                result = self.optimizer.optimize_for_restock(
                    scored_products,
                    current_inventory=current_inventory,
                    reorder_points=reorder_points,
                    max_budget=max_budget
                )
            
            else:
                return {
                    'success': False,
                    'error': f'Unknown goal_type: {goal_type}'
                }
            
            # Generate reasoning and warnings
            for product in result['products']:
                why_recommended = []
                warnings = []
                
                # Why recommended
                if product.get('score', 0) >= 80:
                    why_recommended.append('Top score (80+)')
                if product.get('roi', 0) >= 100:
                    why_recommended.append(f'High ROI ({product["roi"]:.0f}%)')
                if product.get('monthly_sales', 0) > 500:
                    why_recommended.append('Fast mover (500+ sales/month)')
                if product.get('fba_sellers', 999) < 10:
                    why_recommended.append('Low competition')
                
                # Warnings
                breakdown = product.get('breakdown', {})
                volatility = breakdown.get('price_volatility', 0)
                if volatility > 30:
                    warnings.append(f'Price volatility ({volatility:.0f}%)')
                
                if not why_recommended:
                    why_recommended.append('Meets criteria')
                
                product['why_recommended'] = why_recommended
                product['warnings'] = warnings
            
            # Store results
            await self._store_recommendation_results(run_id, result, products_analyzed, products_passed, products_failed)
            
            return {
                'success': True,
                'run_id': run_id,
                'results': result,
                'stats': {
                    'products_analyzed': products_analyzed,
                    'products_passed': products_passed,
                    'products_failed': products_failed
                }
            }
        
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _create_recommendation_run(
        self,
        supplier_id: str,
        goal_type: str,
        goal_params: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> str:
        """Create recommendation run record."""
        run_data = {
            'user_id': self.user_id,
            'supplier_id': supplier_id,
            'goal_type': goal_type,
            'goal_params': goal_params,
            'status': 'pending'
        }
        
        result = supabase.table('recommendation_runs').insert(run_data).execute()
        return result.data[0]['id'] if result.data else None
    
    async def _store_recommendation_results(
        self,
        run_id: str,
        optimization_result: Dict[str, Any],
        products_analyzed: int,
        products_passed: int,
        products_failed: int
    ):
        """Store recommendation results in database."""
        # Store individual product recommendations
        result_records = []
        for product in optimization_result.get('products', []):
            result_records.append({
                'user_id': self.user_id,
                'run_id': run_id,
                'product_id': product.get('product_id'),
                'product_source_id': product.get('product_source_id'),
                'total_score': product.get('score', 0),
                'profitability_score': product.get('profitability_score', 0),
                'velocity_score': product.get('velocity_score', 0),
                'competition_score': product.get('competition_score', 0),
                'risk_score': product.get('risk_score', 0),
                'recommended_quantity': product.get('recommended_quantity', 0),
                'recommended_cost': product.get('recommended_cost', 0),
                'expected_profit': product.get('expected_profit', 0),
                'expected_roi': product.get('roi', 0),
                'days_to_sell': product.get('days_to_sell', 0),
                'mover_category': product.get('mover_category'),
                'why_recommended': product.get('why_recommended', []),
                'warnings': product.get('warnings', [])
            })
        
        if result_records:
            supabase.table('recommendation_results').insert(result_records).execute()
        
        # Update run with summary
        supabase.table('recommendation_runs').update({
            'status': 'completed',
            'completed_at': datetime.utcnow().isoformat(),
            'total_products_analyzed': products_analyzed,
            'products_passed_filters': products_passed,
            'products_failed_filters': products_failed,
            'recommended_product_count': len(optimization_result.get('products', [])),
            'total_investment': optimization_result.get('total_cost', 0),
            'expected_profit': optimization_result.get('total_profit', 0),
            'expected_roi': optimization_result.get('roi', 0),
            'avg_days_to_sell': optimization_result.get('avg_days_to_sell', 0)
        }).eq('id', run_id).execute()

