"""
Rank ASINs by quality for automatic recommendation.
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class AsinRankingService:
    """
    Rank ASINs by quality indicators.
    """
    
    def rank_asins(self, asins: List[Dict]) -> List[Dict]:
        """
        Rank ASINs by recommendation score.
        
        Scoring criteria:
        - Parent ASIN: +10 points
        - Lower BSR (better sales): up to +10 points
        - Prime eligible: +5 points
        - Buybox winner: +5 points
        - More reviews: up to +5 points
        - Higher rating: up to +5 points
        
        Returns: ASINs sorted by score (highest first)
        """
        
        for asin in asins:
            score = 0
            quality = asin.get('quality_indicators', {})
            
            # Prefer parent ASINs
            if asin.get('is_parent'):
                score += 10
                logger.debug(f"{asin['asin']}: +10 (parent)")
            
            # Prefer better BSR (lower is better)
            bsr = quality.get('bsr')
            if bsr:
                if bsr < 1000:
                    score += 10
                elif bsr < 10000:
                    score += 8
                elif bsr < 100000:
                    score += 5
                elif bsr < 500000:
                    score += 2
                logger.debug(f"{asin['asin']}: +score (BSR: {bsr})")
            
            # Prime eligible
            if quality.get('has_prime'):
                score += 5
                logger.debug(f"{asin['asin']}: +5 (Prime)")
            
            # Buybox winner
            if quality.get('is_buybox_winner'):
                score += 5
                logger.debug(f"{asin['asin']}: +5 (Buybox)")
            
            # Review count
            review_count = quality.get('review_count', 0)
            if review_count > 1000:
                score += 5
            elif review_count > 100:
                score += 3
            elif review_count > 10:
                score += 1
            
            # Rating
            rating = quality.get('rating', 0)
            if rating >= 4.5:
                score += 5
            elif rating >= 4.0:
                score += 3
            elif rating >= 3.5:
                score += 1
            
            asin['recommendation_score'] = score
            logger.info(f"{asin['asin']}: Total score = {score}")
        
        # Sort by score (highest first)
        ranked = sorted(asins, key=lambda x: x.get('recommendation_score', 0), reverse=True)
        
        # Mark top recommendation
        if ranked:
            ranked[0]['is_recommended'] = True
        
        return ranked


# Singleton
asin_ranking_service = AsinRankingService()

