"""
UPC to ASIN conversion service using SP-API.
Converts UPC/EAN/GTIN to ASIN when ASIN is not available.
"""
import logging
from typing import Optional, Dict, Any
from app.services.sp_api_client import sp_api_client

logger = logging.getLogger(__name__)


class UPCConverter:
    """
    Converts UPC/EAN/GTIN to ASIN using SP-API catalog search.
    """
    
    async def upc_to_asin(
        self,
        upc: str,
        marketplace_id: str = "ATVPDKIKX0DER"
    ) -> Optional[str]:
        """
        Convert UPC/EAN/GTIN to ASIN using SP-API.
        
        Args:
            upc: UPC/EAN/GTIN code (12-14 digits)
            marketplace_id: Amazon marketplace ID
            
        Returns:
            ASIN if found, None otherwise
        """
        if not upc:
            return None
        
        # Clean and validate UPC
        upc_clean = str(upc).strip().replace("-", "").replace(" ", "")
        
        # Validate UPC format (12-14 digits)
        if not upc_clean.isdigit():
            logger.warning(f"Invalid UPC format: {upc}")
            return None
        
        if len(upc_clean) < 12 or len(upc_clean) > 14:
            logger.warning(f"UPC length invalid (must be 12-14 digits): {upc_clean}")
            return None
        
        # Normalize to 12 digits (UPC-A) or 13 digits (EAN-13)
        # If 14 digits, it's GTIN-14, use last 13 digits
        if len(upc_clean) == 14:
            upc_clean = upc_clean[1:]  # Remove first digit (packaging indicator)
        
        try:
            # Use SP-API catalog search to find product by UPC
            # SP-API catalog search accepts identifiers like UPC/EAN
            result = await sp_api_client.search_catalog_items(
                identifiers=[upc_clean],
                identifiers_type="UPC",
                marketplace_id=marketplace_id
            )
            
            if result:
                # SP-API catalog search returns items in this structure:
                # {
                #   "items": [
                #     {
                #       "asin": "B08...",
                #       "identifiers": {
                #         "marketplaceASIN": {
                #           "marketplaceId": "...",
                #           "asin": "B08..."
                #         }
                #       },
                #       "summaries": [...]
                #     }
                #   ]
                # }
                items = result.get("items") or []
                
                if items:
                    # Get first item's ASIN
                    first_item = items[0]
                    
                    # Try multiple locations for ASIN
                    asin = (
                        first_item.get("asin") or
                        first_item.get("productId") or
                        first_item.get("identifiers", {}).get("marketplaceASIN", {}).get("asin") or
                        (first_item.get("identifiers", {}) or {}).get("asin")
                    )
                    
                    if asin:
                        logger.info(f"✅ Converted UPC {upc_clean} to ASIN {asin}")
                        return asin
                    else:
                        # Log the full item structure for debugging
                        import json
                        logger.warning(f"UPC {upc_clean} found but no ASIN in response. Item keys: {list(first_item.keys())}")
                        logger.debug(f"Full item structure: {json.dumps(first_item, indent=2, default=str)[:1000]}")
                else:
                    # Check if summaries exist at top level (different response format)
                    summaries = result.get("summaries") or []
                    if summaries:
                        first_summary = summaries[0]
                        asin = (
                            first_summary.get("asin") or
                            first_summary.get("productId") or
                            first_summary.get("identifiers", {}).get("marketplaceASIN", {}).get("asin")
                        )
                        if asin:
                            logger.info(f"✅ Converted UPC {upc_clean} to ASIN {asin} (from summaries)")
                            return asin
                    
                    logger.warning(f"No products found for UPC {upc_clean}. Response keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
            else:
                logger.warning(f"No response from SP-API for UPC {upc_clean}")
                
        except Exception as e:
            logger.error(f"Error converting UPC {upc_clean} to ASIN: {e}", exc_info=True)
        
        return None
    
    def is_valid_upc(self, value: str) -> bool:
        """
        Check if a string is a valid UPC/EAN/GTIN format.
        
        Args:
            value: String to validate
            
        Returns:
            True if valid UPC format
        """
        if not value:
            return False
        
        # Clean the value
        clean = str(value).strip().replace("-", "").replace(" ", "")
        
        # Must be all digits
        if not clean.isdigit():
            return False
        
        # Must be 12-14 digits (UPC-A, EAN-13, or GTIN-14)
        if len(clean) < 12 or len(clean) > 14:
            return False
        
        return True
    
    def normalize_upc(self, value: str) -> Optional[str]:
        """
        Normalize UPC to standard format (remove dashes, spaces).
        
        Args:
            value: UPC string
            
        Returns:
            Normalized UPC or None if invalid
        """
        if not value:
            return None
        
        clean = str(value).strip().replace("-", "").replace(" ", "")
        
        if self.is_valid_upc(clean):
            return clean
        
        return None


# Singleton instance
upc_converter = UPCConverter()

