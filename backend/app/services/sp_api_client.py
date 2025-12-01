"""
Amazon SP-API client using PER-USER credentials.
Each user connects their own Amazon Seller account.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from types import SimpleNamespace

from sp_api.api import Products, CatalogItems, ProductFees, ListingsRestrictions
from sp_api.base import Marketplaces, SellingApiException, Credentials

from app.services.supabase_client import supabase
from app.services.amazon_oauth import amazon_oauth
from app.core.config import settings

logger = logging.getLogger(__name__)


class SPAPIError(Exception):
    """Custom exception for SP-API errors."""
    pass


class SPAPIClient:
    """
    SP-API client using per-user credentials.
    Each user must connect their own Amazon Seller account.
    """
    
    def __init__(self):
        self.marketplace = Marketplaces.US
    
    async def _get_credentials_for_user(self, user_id: str) -> Optional[Dict]:
        """Get SP-API credentials for a specific user."""
        
        # Get user's refresh token
        refresh_token = await amazon_oauth.get_user_refresh_token(user_id)
        
        if not refresh_token:
            return None
        
        # Get seller_id from connection
        connection = await amazon_oauth.get_user_connection(user_id)
        seller_id = connection.get("seller_id") if connection else None
        
        # Create credentials object
        creds_obj = SimpleNamespace(
            lwa_app_id=settings.SPAPI_LWA_CLIENT_ID,
            lwa_client_secret=settings.SPAPI_LWA_CLIENT_SECRET,
            aws_access_key=settings.AWS_ACCESS_KEY_ID,
            aws_secret_key=settings.AWS_SECRET_ACCESS_KEY,
            role_arn=settings.SP_API_ROLE_ARN,
        )
        
        return {
            "refresh_token": refresh_token,
            "credentials": creds_obj,
            "seller_id": seller_id,
        }
    
    async def _get_credentials_dict(self, user_id: str) -> Optional[Dict]:
        """Get credentials as dict for API calls."""
        
        creds = await self._get_credentials_for_user(user_id)
        if not creds:
            return None
        
        return {
            "refresh_token": creds["refresh_token"],
            "lwa_app_id": settings.SPAPI_LWA_CLIENT_ID,
            "lwa_client_secret": settings.SPAPI_LWA_CLIENT_SECRET,
            "aws_access_key": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_key": settings.AWS_SECRET_ACCESS_KEY,
            "role_arn": settings.SP_API_ROLE_ARN,
        }
    
    # ==========================================
    # ELIGIBILITY / GATING CHECK
    # ==========================================
    
    async def check_eligibility(self, user_id: str, asin: str) -> Dict[str, Any]:
        """
        Check if THIS USER can list this product (real gating check).
        
        Returns:
            - ELIGIBLE: Can list
            - NOT_ELIGIBLE: Gated/restricted
            - APPROVAL_REQUIRED: Need to apply
            - NOT_CONNECTED: User hasn't connected Amazon
            - UNKNOWN: Error checking
        """
        
        # Check if user is connected
        connection = await amazon_oauth.get_user_connection(user_id)
        if not connection or not connection.get("is_connected"):
            return {
                "asin": asin,
                "status": "NOT_CONNECTED",
                "can_list": None,
                "error": "Connect your Amazon Seller account first",
            }
        
        # Check cache first
        cached = await self._get_cached_eligibility(user_id, asin)
        if cached:
            return cached
        
        # Get credentials
        creds = await self._get_credentials_for_user(user_id)
        if not creds:
            return {
                "asin": asin,
                "status": "NOT_CONNECTED",
                "can_list": None,
                "error": "Failed to get credentials",
            }
        
        seller_id = creds.get("seller_id")
        
        try:
            # Create credentials object for API
            creds_obj = creds["credentials"]
            credentials = Credentials(
                refresh_token=creds["refresh_token"],
                credentials=creds_obj
            )
            
            restrictions_api = ListingsRestrictions(
                credentials=credentials,
                marketplace=self.marketplace
            )
            
            response = restrictions_api.get_listings_restrictions(
                asin=asin,
                sellerId=seller_id,
                marketplaceIds=[settings.MARKETPLACE_ID or "ATVPDKIKX0DER"]
            )
            
            restrictions = response.payload.get("restrictions", [])
            
            if not restrictions:
                result = {
                    "asin": asin,
                    "status": "ELIGIBLE",
                    "can_list": True,
                    "restrictions": [],
                    "reasons": []
                }
            else:
                reasons = []
                approval_required = False
                
                for restriction in restrictions:
                    for reason in restriction.get("reasons", []):
                        reason_code = reason.get("reasonCode", "UNKNOWN")
                        message = reason.get("message", "Restriction applies")
                        reasons.append({"code": reason_code, "message": message})
                        
                        if reason_code == "APPROVAL_REQUIRED":
                            approval_required = True
                
                result = {
                    "asin": asin,
                    "status": "APPROVAL_REQUIRED" if approval_required else "NOT_ELIGIBLE",
                    "can_list": False,
                    "restrictions": restrictions,
                    "reasons": reasons
                }
            
            # Cache result
            await self._cache_eligibility(user_id, asin, result)
            
            # Update last_used
            await amazon_oauth.update_last_used(user_id)
            
            return result
            
        except SellingApiException as e:
            logger.error(f"SP-API eligibility error for {asin}: {e}")
            return {
                "asin": asin,
                "status": "UNKNOWN",
                "can_list": None,
                "error": str(e),
                "reasons": []
            }
    
    async def _get_cached_eligibility(self, user_id: str, asin: str) -> Optional[Dict]:
        """Get cached eligibility if still valid."""
        
        try:
            # Get seller_id for cache lookup
            connection = await amazon_oauth.get_user_connection(user_id)
            seller_id = connection.get("seller_id") if connection else None
            
            if not seller_id:
                return None
            
            result = supabase.table("eligibility_cache")\
                .select("*")\
                .eq("asin", asin)\
                .eq("seller_id", seller_id)\
                .gt("expires_at", datetime.utcnow().isoformat())\
                .maybe_single()\
                .execute()
            
            if result.data:
                return {
                    "asin": result.data["asin"],
                    "status": result.data["status"],
                    "can_list": result.data["status"] == "ELIGIBLE",
                    "reasons": result.data.get("reasons", []),
                    "cached": True
                }
        except Exception as e:
            logger.debug(f"Cache lookup failed: {e}")
        
        return None
    
    async def _cache_eligibility(self, user_id: str, asin: str, result: Dict):
        """Cache eligibility result."""
        
        try:
            connection = await amazon_oauth.get_user_connection(user_id)
            seller_id = connection.get("seller_id") if connection else None
            
            if not seller_id:
                return
            
            supabase.table("eligibility_cache").upsert({
                "asin": asin,
                "seller_id": seller_id,
                "status": result["status"],
                "reasons": result.get("reasons", []),
                "raw_response": result.get("restrictions"),
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
            }, on_conflict="asin,seller_id").execute()
        except Exception as e:
            logger.warning(f"Failed to cache eligibility: {e}")
    
    # ==========================================
    # FEE ESTIMATES
    # ==========================================
    
    async def get_fee_estimate(
        self,
        user_id: str,
        asin: str,
        price: float,
        is_fba: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get FBA fee estimate for a product using user's account.
        """
        
        # Check if user is connected
        connection = await amazon_oauth.get_user_connection(user_id)
        if not connection or not connection.get("is_connected"):
            return None
        
        # Check cache
        cached = self._get_cached_fees(asin, price)
        if cached:
            return cached
        
        # Get credentials
        creds = await self._get_credentials_for_user(user_id)
        if not creds:
            return None
        
        try:
            # Create credentials object
            creds_obj = creds["credentials"]
            credentials = Credentials(
                refresh_token=creds["refresh_token"],
                credentials=creds_obj
            )
            
            fees_api = ProductFees(
                credentials=credentials,
                marketplace=self.marketplace
            )
            
            response = fees_api.get_product_fees_estimate_for_asin(
                asin=asin,
                price=price,
                currency="USD",
                is_fba=is_fba,
                shipping=0 if is_fba else 4.99
            )
            
            if not response.payload:
                return None
            
            fees_result = response.payload.get("FeesEstimateResult", {})
            fees_estimate = fees_result.get("FeesEstimate", {})
            fee_details = fees_estimate.get("FeeDetailList", [])
            
            result = {
                "asin": asin,
                "price": price,
                "is_fba": is_fba,
                "total_fees": float(fees_estimate.get("TotalFeesEstimate", {}).get("Amount", 0)),
                "referral_fee": self._extract_fee(fee_details, "ReferralFee"),
                "fba_fulfillment_fee": self._extract_fee(fee_details, "FBAFees"),
                "variable_closing_fee": self._extract_fee(fee_details, "VariableClosingFee"),
                "currency": "USD"
            }
            
            # Cache result
            self._cache_fees(result)
            
            # Update last_used
            await amazon_oauth.update_last_used(user_id)
            
            return result
            
        except SellingApiException as e:
            logger.error(f"SP-API fees error for {asin}: {e}")
            return None
    
    def _extract_fee(self, fee_list: List[Dict], fee_type: str) -> float:
        """Extract specific fee from fee list."""
        for fee in fee_list:
            if fee.get("FeeType") == fee_type:
                return float(fee.get("FeeAmount", {}).get("Amount", 0))
        return 0.0
    
    def _get_cached_fees(self, asin: str, price: float) -> Optional[Dict]:
        """Get cached fees if still valid."""
        
        try:
            result = supabase.table("fee_cache")\
                .select("*")\
                .eq("asin", asin)\
                .eq("price", price)\
                .gt("expires_at", datetime.utcnow().isoformat())\
                .maybe_single()\
                .execute()
            
            if result.data:
                return {
                    "asin": result.data["asin"],
                    "price": float(result.data["price"]),
                    "total_fees": float(result.data["total_fees"] or 0),
                    "referral_fee": float(result.data["referral_fee"] or 0),
                    "fba_fulfillment_fee": float(result.data["fba_fulfillment_fee"] or 0),
                    "cached": True
                }
        except Exception as e:
            logger.debug(f"Fee cache lookup failed: {e}")
        
        return None
    
    def _cache_fees(self, fees: Dict):
        """Cache fee estimate."""
        
        try:
            supabase.table("fee_cache").upsert({
                "asin": fees["asin"],
                "price": fees["price"],
                "referral_fee": fees.get("referral_fee"),
                "fba_fulfillment_fee": fees.get("fba_fulfillment_fee"),
                "variable_closing_fee": fees.get("variable_closing_fee"),
                "total_fees": fees.get("total_fees"),
                "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
            }, on_conflict="asin,price").execute()
        except Exception as e:
            logger.warning(f"Failed to cache fees: {e}")
    
    # ==========================================
    # PRODUCT DATA
    # ==========================================
    
    async def get_competitive_pricing(self, user_id: str, asin: str) -> Optional[Dict[str, Any]]:
        """Get competitive pricing data using user's account."""
        
        # Get credentials
        creds = await self._get_credentials_for_user(user_id)
        if not creds:
            return None
        
        try:
            # Create credentials object
            creds_obj = creds["credentials"]
            credentials = Credentials(
                refresh_token=creds["refresh_token"],
                credentials=creds_obj
            )
            
            products_api = Products(
                credentials=credentials,
                marketplace=self.marketplace
            )
            
            response = products_api.get_competitive_pricing_for_asins(
                asin_list=[asin]
            )
            
            if not response.payload:
                return None
            
            data = response.payload[0]
            product_data = data.get("Product", {})
            
            # Extract pricing
            competitive_prices = product_data.get("CompetitivePricing", {}).get("CompetitivePrices", [])
            buy_box_price = None
            
            for price in competitive_prices:
                if price.get("CompetitivePriceId") == "1":
                    buy_box_price = price.get("Price", {}).get("LandedPrice", {}).get("Amount")
                    break
            
            # Extract sales rank
            sales_rankings = product_data.get("SalesRankings", [])
            primary_rank = None
            primary_category = None
            
            for rank in sales_rankings:
                cat_id = rank.get("ProductCategoryId", "")
                if "_display_on_website" in cat_id:
                    primary_rank = rank.get("Rank")
                    primary_category = cat_id.replace("_display_on_website", "")
                    break
            
            # Update last_used
            await amazon_oauth.update_last_used(user_id)
            
            return {
                "asin": asin,
                "buy_box_price": float(buy_box_price) if buy_box_price else None,
                "sales_rank": primary_rank,
                "sales_rank_category": primary_category,
            }
            
        except SellingApiException as e:
            logger.error(f"SP-API pricing error for {asin}: {e}")
            return None


# Singleton instance
sp_api_client = SPAPIClient()
