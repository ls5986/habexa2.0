"""
Genius Scoring Algorithm - Advanced Product Selection & Profitability Scoring System
Version 1.0 GENIUS MODE

The most sophisticated product recommendation engine for Amazon FBA wholesale.
Scores every product 0-100 using Keepa + SP-API + user data.
"""
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)


class GeniusScorer:
    """
    Composite Score (0-100) that evaluates:
    - Profitability (30 points)
    - Velocity (25 points)
    - Competition (15 points)
    - Risk (15 points)
    - Opportunity (15 points)
    """
    
    def __init__(self):
        # Category-specific rank thresholds
        self.RANK_THRESHOLDS = {
            'Grocery & Gourmet Food': {
                'excellent': 10000,
                'great': 25000,
                'good': 50000,
                'okay': 100000,
                'marginal': 200000
            },
            'Health & Household': {
                'excellent': 15000,
                'great': 35000,
                'good': 75000,
                'okay': 150000,
                'marginal': 300000
            },
            'Beauty & Personal Care': {
                'excellent': 12000,
                'great': 30000,
                'good': 60000,
                'okay': 120000,
                'marginal': 250000
            },
            'Home & Kitchen': {
                'excellent': 10000,
                'great': 25000,
                'good': 50000,
                'okay': 100000,
                'marginal': 200000
            },
            'default': {
                'excellent': 10000,
                'great': 25000,
                'good': 50000,
                'okay': 100000,
                'marginal': 200000
            }
        }
        
        # Category risk scores
        self.CATEGORY_RISK = {
            'Grocery & Gourmet Food': {'score': 1, 'risk': 'medium'},
            'Health & Household': {'score': 2, 'risk': 'low'},
            'Beauty & Personal Care': {'score': 1, 'risk': 'medium'},
            'Clothing & Accessories': {'score': 0, 'risk': 'high'},
            'Electronics': {'score': 0, 'risk': 'high'},
            'Toys & Games': {'score': 1, 'risk': 'medium'},
        }
    
    def calculate_genius_score(
        self,
        product_data: Dict[str, Any],
        keepa_data: Dict[str, Any],
        sp_api_data: Dict[str, Any],
        user_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        The complete genius scoring algorithm.
        
        Returns: {
            'total_score': 0-100,
            'grade': 'EXCELLENT'|'GOOD'|'FAIR'|'POOR',
            'badge': '🟢'|'🟡'|'🟠'|'🔴',
            'breakdown': {...},
            'component_scores': {...},
            'insights': {...}
        }
        """
        # STEP 1: PASS/FAIL FILTERS
        fail_reason = self._check_pass_fail_filters(product_data, sp_api_data, user_config, keepa_data)
        if fail_reason:
            return {
                'score': 0,
                'total_score': 0,
                'grade': 'POOR',
                'badge': '🔴',
                'reason': fail_reason,
                'breakdown': {},
                'component_scores': {},
                'insights': {'warnings': [fail_reason]}
            }
        
        # STEP 2: CALCULATE COMPONENT SCORES
        scores = {}
        
        # PROFITABILITY (30 points)
        profitability_score, profit_scores = self._calculate_profitability(product_data, keepa_data)
        scores.update(profit_scores)
        
        # VELOCITY (25 points)
        velocity_score, velocity_scores = self._calculate_velocity(product_data, keepa_data, sp_api_data)
        scores.update(velocity_scores)
        
        # COMPETITION (15 points)
        competition_score, comp_scores = self._calculate_competition(keepa_data, sp_api_data)
        scores.update(comp_scores)
        
        # RISK (15 points)
        risk_score, risk_scores = self._calculate_risk(keepa_data, sp_api_data, product_data, user_config)
        scores.update(risk_scores)
        
        # OPPORTUNITY (15 points)
        opportunity_score, opp_scores = self._calculate_opportunity(keepa_data, sp_api_data, product_data)
        scores.update(opp_scores)
        
        # STEP 3: CALCULATE TOTAL SCORE
        total_score = profitability_score + velocity_score + competition_score + risk_score + opportunity_score
        
        # STEP 4: APPLY MULTIPLIERS
        if profitability_score >= 25 and velocity_score >= 20:
            total_score *= 1.05  # 5% bonus for high profit + fast mover
        
        if competition_score < 5:
            total_score *= 0.9  # 10% penalty for high competition
        
        if risk_score < 8:
            total_score *= 0.95  # 5% penalty for high risk
        
        total_score = min(total_score, 100)  # Cap at 100
        
        # STEP 5: CATEGORIZE
        if total_score >= 85:
            grade = 'EXCELLENT'
            badge = '🟢'
        elif total_score >= 70:
            grade = 'GOOD'
            badge = '🟡'
        elif total_score >= 50:
            grade = 'FAIR'
            badge = '🟠'
        else:
            grade = 'POOR'
            badge = '🔴'
        
        # STEP 6: GENERATE INSIGHTS
        insights = self._generate_insights(scores, product_data, keepa_data, sp_api_data)
        
        return {
            'total_score': round(total_score, 1),
            'score': round(total_score, 1),  # Alias for compatibility
            'grade': grade,
            'badge': badge,
            'breakdown': {
                'profitability': round(profitability_score, 1),
                'velocity': round(velocity_score, 1),
                'competition': round(competition_score, 1),
                'risk': round(risk_score, 1),
                'opportunity': round(opportunity_score, 1)
            },
            'component_scores': {k: round(v, 1) if isinstance(v, (int, float)) else v for k, v in scores.items()},
            'insights': insights
        }
    
    def _check_pass_fail_filters(
        self,
        product_data: Dict[str, Any],
        sp_api_data: Dict[str, Any],
        user_config: Dict[str, Any],
        keepa_data: Dict[str, Any]
    ) -> Optional[str]:
        """Check hard pass/fail filters. Returns reason if failed, None if passed."""
        
        # Brand restriction check
        if product_data.get('is_brand_restricted'):
            return 'Brand restricted'
        
        # Hazmat check
        if sp_api_data.get('is_hazmat') and not user_config.get('handles_hazmat', False):
            return 'Hazmat (user cannot handle)'
        
        # ROI threshold
        min_roi = user_config.get('min_roi', 25)
        roi = product_data.get('roi', 0)
        if roi < min_roi:
            return f'ROI below {min_roi}% (current: {roi}%)'
        
        # FBA seller count
        max_fba_sellers = user_config.get('max_fba_sellers', 30)
        fba_sellers = sp_api_data.get('fba_seller_count', 0)
        if fba_sellers > max_fba_sellers:
            return f'Too many FBA sellers ({fba_sellers} > {max_fba_sellers})'
        
        # Price volatility
        price_volatility = self._calculate_price_volatility_raw(keepa_data)
        if price_volatility and price_volatility > 40:
            return f'Price too volatile ({price_volatility:.1f}%)'
        
        return None
    
    def _calculate_profitability(
        self,
        product_data: Dict[str, Any],
        keepa_data: Dict[str, Any]
    ) -> tuple[float, Dict[str, float]]:
        """Calculate profitability score (30 points total)."""
        scores = {}
        
        # 1.1 ROI Score (12 points)
        roi = product_data.get('roi', 0)
        scores['roi'] = self._score_roi(roi)
        
        # 1.2 Absolute Profit Score (10 points)
        profit_per_unit = product_data.get('profit_per_unit', 0) or product_data.get('profit', 0)
        scores['absolute_profit'] = self._score_absolute_profit(profit_per_unit)
        
        # 1.3 Margin Score (8 points)
        margin = product_data.get('margin', 0)
        scores['margin'] = self._score_margin(margin)
        
        total = sum(scores.values())
        return total, scores
    
    def _score_roi(self, roi: float) -> float:
        """Score ROI (12 points max)."""
        if roi >= 200:
            return 12
        elif roi >= 150:
            return 10
        elif roi >= 100:
            return 8
        elif roi >= 75:
            return 6
        elif roi >= 50:
            return 4
        elif roi >= 30:
            return 2
        else:
            return 0
    
    def _score_absolute_profit(self, profit: float) -> float:
        """Score absolute profit per unit (10 points max)."""
        if profit >= 10:
            return 10
        elif profit >= 5:
            return 8
        elif profit >= 3:
            return 6
        elif profit >= 2:
            return 4
        elif profit >= 1:
            return 2
        else:
            return 0
    
    def _score_margin(self, margin: float) -> float:
        """Score margin percentage (8 points max)."""
        if margin >= 40:
            return 8
        elif margin >= 30:
            return 6
        elif margin >= 20:
            return 4
        elif margin >= 15:
            return 2
        else:
            return 0
    
    def _calculate_velocity(
        self,
        product_data: Dict[str, Any],
        keepa_data: Dict[str, Any],
        sp_api_data: Dict[str, Any]
    ) -> tuple[float, Dict[str, float]]:
        """Calculate velocity score (25 points total)."""
        scores = {}
        
        # 2.1 Sales Velocity (10 points)
        monthly_sales = self._estimate_monthly_sales(keepa_data, sp_api_data)
        scores['sales_velocity'] = self._score_sales_velocity(monthly_sales)
        
        # 2.2 Sales Rank (7 points)
        sales_rank = sp_api_data.get('sales_rank', 999999) or keepa_data.get('salesRank', 999999)
        category = sp_api_data.get('category', 'default')
        scores['sales_rank'] = self._score_sales_rank(sales_rank, category)
        
        # 2.3 Days to Sell (5 points)
        order_qty = product_data.get('order_quantity', 100)  # Default
        days_to_sell = (order_qty / monthly_sales * 30) if monthly_sales > 0 else 999
        scores['days_to_sell'] = self._score_days_to_sell(days_to_sell)
        
        # 2.4 Sell-Through Rate (3 points)
        scores['sell_through'] = self._score_sell_through(keepa_data)
        
        total = sum(scores.values())
        return total, scores
    
    def _estimate_monthly_sales(
        self,
        keepa_data: Dict[str, Any],
        sp_api_data: Dict[str, Any]
    ) -> float:
        """Estimate monthly sales using multiple methods."""
        # Method 1: Keepa estimated sales
        if keepa_data.get('estimatedSales'):
            return float(keepa_data['estimatedSales'])
        
        # Method 2: Sales rank drops (if available)
        rank_drops = self._calculate_sales_from_rank_drops(keepa_data)
        if rank_drops:
            return rank_drops
        
        # Method 3: Sales rank formula
        sales_rank = sp_api_data.get('sales_rank', 999999) or keepa_data.get('salesRank', 999999)
        category = sp_api_data.get('category', 'Grocery & Gourmet Food')
        return self._estimate_sales_from_rank(sales_rank, category)
    
    def _calculate_sales_from_rank_drops(self, keepa_data: Dict[str, Any]) -> Optional[float]:
        """Calculate sales from sales rank drops (GENIUS METHOD)."""
        csv_data = keepa_data.get('csv', {})
        sales_ranks = csv_data.get('salesRanks', [])
        
        if not sales_ranks or len(sales_ranks) < 10:
            return None
        
        # Get last 30 days
        cutoff_ms = (datetime.now() - timedelta(days=30)).timestamp() * 1000
        
        recent_history = [p for p in sales_ranks if p[0] >= cutoff_ms and p[1] > 0]
        
        if len(recent_history) < 10:
            return None
        
        # Count rank improvements (drops)
        drops = 0
        significant_drops = 0
        
        for i in range(1, len(recent_history)):
            prev_rank = recent_history[i-1][1]
            curr_rank = recent_history[i][1]
            
            if curr_rank < prev_rank:  # Rank improved
                drops += 1
                improvement = (prev_rank - curr_rank) / prev_rank if prev_rank > 0 else 0
                if improvement > 0.10:
                    significant_drops += 1
        
        # Estimate sales
        estimated_sales = significant_drops + (drops * 0.5)
        
        # Extrapolate to monthly
        if len(recent_history) > 1:
            days_covered = (recent_history[-1][0] - recent_history[0][0]) / (1000 * 60 * 60 * 24)
            if days_covered > 0:
                monthly_sales = (estimated_sales / days_covered) * 30
                return monthly_sales
        
        return None
    
    def _estimate_sales_from_rank(self, sales_rank: int, category: str) -> float:
        """Estimate sales from sales rank using category-specific formulas."""
        formulas = {
            'Grocery & Gourmet Food': lambda r: 50000 / (r ** 0.65) if r > 0 else 0,
            'Health & Household': lambda r: 45000 / (r ** 0.63) if r > 0 else 0,
            'Beauty & Personal Care': lambda r: 40000 / (r ** 0.62) if r > 0 else 0,
            'Home & Kitchen': lambda r: 55000 / (r ** 0.67) if r > 0 else 0,
        }
        
        formula = formulas.get(category, formulas['Grocery & Gourmet Food'])
        return max(0, formula(sales_rank))
    
    def _score_sales_velocity(self, monthly_sales: float) -> float:
        """Score sales velocity (10 points max)."""
        if monthly_sales >= 1000:
            return 10
        elif monthly_sales >= 500:
            return 8
        elif monthly_sales >= 250:
            return 6
        elif monthly_sales >= 100:
            return 4
        elif monthly_sales >= 50:
            return 2
        else:
            return 0
    
    def _score_sales_rank(self, rank: int, category: str) -> float:
        """Score sales rank (7 points max)."""
        thresholds = self.RANK_THRESHOLDS.get(category, self.RANK_THRESHOLDS['default'])
        
        if rank <= thresholds['excellent']:
            return 7
        elif rank <= thresholds['great']:
            return 6
        elif rank <= thresholds['good']:
            return 4
        elif rank <= thresholds['okay']:
            return 2
        elif rank <= thresholds['marginal']:
            return 1
        else:
            return 0
    
    def _score_days_to_sell(self, days: float) -> float:
        """Score days to sell (5 points max)."""
        if days <= 15:
            return 5
        elif days <= 30:
            return 4
        elif days <= 45:
            return 3
        elif days <= 60:
            return 2
        elif days <= 90:
            return 1
        else:
            return 0
    
    def _score_sell_through(self, keepa_data: Dict[str, Any]) -> float:
        """Score sell-through rate (3 points max)."""
        # Simplified - would need buy box history
        # For now, return neutral score
        return 1.5
    
    def _calculate_competition(
        self,
        keepa_data: Dict[str, Any],
        sp_api_data: Dict[str, Any]
    ) -> tuple[float, Dict[str, float]]:
        """Calculate competition score (15 points total)."""
        scores = {}
        
        # 3.1 FBA Seller Count (5 points)
        fba_sellers = sp_api_data.get('fba_seller_count', 0) or keepa_data.get('fbaOffers', {}).get('offerCountNew', 0)
        scores['fba_count'] = self._score_fba_sellers(fba_sellers)
        
        # 3.2 Buy Box Percentage (4 points)
        scores['buy_box_pct'] = self._score_buy_box_percentage(keepa_data)
        
        # 3.3 New FBA Offers Trend (3 points)
        scores['seller_trend'] = self._analyze_seller_trend(keepa_data)
        
        # 3.4 Price Compression (2 points)
        scores['price_compression'] = self._detect_price_compression(keepa_data)
        
        # 3.5 Seller Churn (1 point)
        scores['seller_churn'] = self._calculate_seller_churn(keepa_data)
        
        total = sum(scores.values())
        return total, scores
    
    def _score_fba_sellers(self, count: int) -> float:
        """Score FBA seller count (5 points max)."""
        if count <= 5:
            return 5
        elif count <= 10:
            return 4
        elif count <= 20:
            return 3
        elif count <= 30:
            return 2
        elif count <= 50:
            return 1
        else:
            return 0
    
    def _score_buy_box_percentage(self, keepa_data: Dict[str, Any]) -> float:
        """Score buy box percentage (4 points max)."""
        # Simplified - would need buy box history
        # For now, return neutral score
        return 2.0
    
    def _analyze_seller_trend(self, keepa_data: Dict[str, Any]) -> float:
        """Analyze seller trend (3 points max)."""
        # Simplified - would need offer count history
        return 1.5
    
    def _detect_price_compression(self, keepa_data: Dict[str, Any]) -> float:
        """Detect price compression (2 points max)."""
        # Simplified - would need price history analysis
        return 1.0
    
    def _calculate_seller_churn(self, keepa_data: Dict[str, Any]) -> float:
        """Calculate seller churn (1 point max)."""
        # Simplified
        return 0.5
    
    def _calculate_risk(
        self,
        keepa_data: Dict[str, Any],
        sp_api_data: Dict[str, Any],
        product_data: Dict[str, Any],
        user_config: Dict[str, Any]
    ) -> tuple[float, Dict[str, float]]:
        """Calculate risk score (15 points total)."""
        scores = {}
        
        # 4.1 Price Volatility (4 points)
        scores['price_volatility'] = self._score_price_volatility(keepa_data)
        
        # 4.2 Stock-Out Risk (3 points)
        scores['stockout_risk'] = self._score_stockout_risk(keepa_data)
        
        # 4.3 Hazmat Status (2 points)
        scores['hazmat'] = self._score_hazmat(sp_api_data, user_config)
        
        # 4.4 IP/Brand Risk (2 points)
        scores['ip_risk'] = self._score_ip_risk(product_data)
        
        # 4.5 Review Volatility (2 points)
        scores['review_volatility'] = self._score_review_stability(keepa_data)
        
        # 4.6 Category Risk (2 points)
        category = sp_api_data.get('category', 'default')
        scores['category_risk'] = self._score_category_risk(category)
        
        total = sum(scores.values())
        return total, scores
    
    def _calculate_price_volatility_raw(self, keepa_data: Dict[str, Any]) -> Optional[float]:
        """Calculate raw price volatility coefficient."""
        csv_data = keepa_data.get('csv', {})
        price_history = csv_data.get('AMAZON', []) or csv_data.get('NEW', [])
        
        if not price_history or len(price_history) < 30:
            return None
        
        # Get last 90 days
        cutoff_ms = (datetime.now() - timedelta(days=90)).timestamp() * 1000
        recent_prices = [p[1]/100 for p in price_history if p[0] >= cutoff_ms and p[1] > 0]
        
        if len(recent_prices) < 10:
            return None
        
        mean_price = statistics.mean(recent_prices)
        if mean_price == 0:
            return None
        
        std_dev = statistics.stdev(recent_prices) if len(recent_prices) > 1 else 0
        cv = (std_dev / mean_price) * 100
        
        return cv
    
    def _score_price_volatility(self, keepa_data: Dict[str, Any]) -> float:
        """Score price volatility (4 points max)."""
        cv = self._calculate_price_volatility_raw(keepa_data)
        
        if cv is None:
            return 2  # Neutral if no data
        
        if cv < 5:
            return 4
        elif cv < 10:
            return 3
        elif cv < 20:
            return 2
        elif cv < 30:
            return 1
        else:
            return 0
    
    def _score_stockout_risk(self, keepa_data: Dict[str, Any]) -> float:
        """Score stock-out risk (3 points max)."""
        oos_pct = keepa_data.get('outOfStockPercentage90', 0)
        
        if 5 <= oos_pct <= 20:
            return 3  # Opportunity
        elif oos_pct < 5:
            return 1
        elif oos_pct > 50:
            return 0
        else:
            return 2
    
    def _score_hazmat(self, sp_api_data: Dict[str, Any], user_config: Dict[str, Any]) -> float:
        """Score hazmat status (2 points max)."""
        is_hazmat = sp_api_data.get('is_hazmat', False)
        
        if not is_hazmat:
            return 2
        
        if user_config.get('handles_hazmat', False):
            return 3  # Bonus for handling hazmat
        else:
            return 0
    
    def _score_ip_risk(self, product_data: Dict[str, Any]) -> float:
        """Score IP/brand risk (2 points max)."""
        if product_data.get('is_brand_restricted'):
            return 0
        else:
            return 2
    
    def _score_review_stability(self, keepa_data: Dict[str, Any]) -> float:
        """Score review stability (2 points max)."""
        # Simplified - would need review history
        return 1.5
    
    def _score_category_risk(self, category: str) -> float:
        """Score category risk (2 points max)."""
        risk_data = self.CATEGORY_RISK.get(category, {'score': 1})
        return risk_data['score']
    
    def _calculate_opportunity(
        self,
        keepa_data: Dict[str, Any],
        sp_api_data: Dict[str, Any],
        product_data: Dict[str, Any]
    ) -> tuple[float, Dict[str, float]]:
        """Calculate opportunity score (15 points total)."""
        scores = {}
        
        # 5.1 Underpriced Detection (4 points)
        scores['underpriced'] = self._detect_underpricing(keepa_data)
        
        # 5.2 Low Competition Window (4 points)
        scores['low_competition'] = self._detect_competition_window(keepa_data)
        
        # 5.3 Trending Up (3 points)
        scores['trending_up'] = self._detect_upward_trend(keepa_data)
        
        # 5.4 Amazon OOS Opportunity (2 points)
        scores['amazon_oos'] = self._check_amazon_oos_opportunity(keepa_data)
        
        # 5.5 New Product Potential (2 points)
        scores['new_product'] = self._score_new_product_potential(keepa_data, sp_api_data)
        
        total = sum(scores.values())
        return total, scores
    
    def _detect_underpricing(self, keepa_data: Dict[str, Any]) -> float:
        """Detect underpricing (4 points max)."""
        current = keepa_data.get('current', 0) / 100 if keepa_data.get('current') else 0
        avg_30d = keepa_data.get('avg30', 0) / 100 if keepa_data.get('avg30') else 0
        avg_90d = keepa_data.get('avg90', 0) / 100 if keepa_data.get('avg90') else 0
        
        if not current or not avg_90d:
            return 1.0
        
        discount_from_avg = ((avg_90d - current) / avg_90d) * 100 if avg_90d > 0 else 0
        recent_discount = ((avg_30d - current) / avg_30d) * 100 if avg_30d > 0 else 0
        
        # Temporary dip (opportunity)
        if discount_from_avg > 10 and recent_discount < 5:
            return 4
        
        # Sustained dip (concerning)
        elif discount_from_avg > 10 and recent_discount > 8:
            return 0
        
        # Fair price
        elif -5 <= discount_from_avg <= 5:
            return 2
        
        # Overpriced
        else:
            return 0
    
    def _detect_competition_window(self, keepa_data: Dict[str, Any]) -> float:
        """Detect low competition window (4 points max)."""
        # Simplified - would need offer count history
        return 2.0
    
    def _detect_upward_trend(self, keepa_data: Dict[str, Any]) -> float:
        """Detect upward trend (3 points max)."""
        # Simplified - would need rank/review history analysis
        return 1.5
    
    def _check_amazon_oos_opportunity(self, keepa_data: Dict[str, Any]) -> float:
        """Check Amazon OOS opportunity (2 points max)."""
        oos_pct = keepa_data.get('outOfStockPercentage90', 0)
        
        if oos_pct < 20:
            return 2
        elif oos_pct < 50:
            return 1
        else:
            return 0
    
    def _score_new_product_potential(
        self,
        keepa_data: Dict[str, Any],
        sp_api_data: Dict[str, Any]
    ) -> float:
        """Score new product potential (2 points max)."""
        # Simplified
        return 1.0
    
    def _generate_insights(
        self,
        scores: Dict[str, float],
        product_data: Dict[str, Any],
        keepa_data: Dict[str, Any],
        sp_api_data: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Generate insights explaining the score."""
        insights = {
            'strengths': [],
            'weaknesses': [],
            'opportunities': [],
            'warnings': []
        }
        
        # Strengths
        if scores.get('roi', 0) >= 10:
            insights['strengths'].append(f"Excellent ROI ({product_data.get('roi', 0):.1f}%)")
        
        if scores.get('sales_velocity', 0) >= 8:
            monthly_sales = self._estimate_monthly_sales(keepa_data, sp_api_data)
            insights['strengths'].append(f"Fast mover (~{monthly_sales:.0f} sales/month)")
        
        if scores.get('fba_count', 0) >= 4:
            fba_sellers = sp_api_data.get('fba_seller_count', 0)
            insights['strengths'].append(f"Low competition ({fba_sellers} FBA sellers)")
        
        # Weaknesses
        if scores.get('roi', 0) < 4:
            insights['weaknesses'].append(f"Low ROI ({product_data.get('roi', 0):.1f}%)")
        
        if scores.get('sales_velocity', 0) < 4:
            monthly_sales = self._estimate_monthly_sales(keepa_data, sp_api_data)
            insights['weaknesses'].append(f"Slow mover (est. {monthly_sales:.0f}/month)")
        
        # Opportunities
        if scores.get('underpriced', 0) >= 3:
            insights['opportunities'].append("Price temporarily LOW - buy opportunity!")
        
        if scores.get('amazon_oos', 0) >= 1:
            insights['opportunities'].append("Amazon out of stock - 3P opportunity")
        
        # Warnings
        if scores.get('price_volatility', 0) < 2:
            cv = self._calculate_price_volatility_raw(keepa_data)
            if cv:
                insights['warnings'].append(f"Price volatility: {cv:.1f}%")
        
        return insights


