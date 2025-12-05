"""
UPC to ASIN conversion service using SP-API.
Converts UPC/EAN/GTIN to ASIN when ASIN is not available.
Supports batch conversion of up to 20 UPCs per request for efficiency.
"""
import logging
from typing import Optional, Dict, Any, List
from app.services.sp_api_client import sp_api_client

logger = logging.getLogger(__name__)


class UPCConverter:
    """
    Converts UPC/EAN/GTIN to ASIN using SP-API catalog search.
    Supports single and batch conversion (up to 20 UPCs per request).
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
        upc_clean = str(upc).strip().replace("-", "").replace(" ", "").replace(".0", "")
        
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
    
    async def upcs_to_asins_batch(
        self,
        upcs: List[str],
        marketplace_id: str = "ATVPDKIKX0DER"
    ) -> Dict[str, Optional[str]]:
        """
        Convert multiple UPCs/EANs/GTINs to ASINs in batch.
        SP-API supports up to 20 identifiers per request.
        
        Args:
            upcs: List of UPC/EAN/GTIN codes (up to 20)
            marketplace_id: Amazon marketplace ID
            
        Returns:
            Dictionary mapping UPC -> ASIN (or None if not found)
        """
        if not upcs:
            return {}
        
        # Limit to 20 UPCs per batch (SP-API limit)
        upcs_limited = upcs[:20]
        
        # Normalize and validate UPCs
        normalized_upcs = []
        upc_to_original = {}  # Map normalized -> original for result mapping
        
        for upc in upcs_limited:
            if not upc:
                continue
            
            # Clean and validate
            upc_clean = str(upc).strip().replace("-", "").replace(" ", "").replace(".0", "")
            
            # Validate format
            if not upc_clean.isdigit():
                logger.warning(f"Invalid UPC format: {upc}")
                continue
            
            if len(upc_clean) < 12 or len(upc_clean) > 14:
                logger.warning(f"UPC length invalid (must be 12-14 digits): {upc_clean}")
                continue
            
            # Normalize to 12 digits (UPC-A) or 13 digits (EAN-13)
            if len(upc_clean) == 14:
                upc_clean = upc_clean[1:]  # Remove first digit (packaging indicator)
            
            normalized_upcs.append(upc_clean)
            upc_to_original[upc_clean] = upc
        
        if not normalized_upcs:
            return {}
        
        # Batch convert using SP-API catalog search
        try:
            result = await sp_api_client.search_catalog_items(
                identifiers=normalized_upcs,
                identifiers_type="UPC",
                marketplace_id=marketplace_id
            )
            
            if not result:
                logger.warning(f"No response from SP-API for batch UPC conversion")
                return {upc: None for upc in upcs_limited}
            
            # Parse results - build mapping of UPC -> ASIN
            upc_to_asin = {}
            
            # SP-API returns items - each item corresponds to one identifier
            # Items are typically returned in the same order as input identifiers
            items = result.get("items") or []
            summaries = result.get("summaries") or []
            
            # Use items if available, otherwise summaries
            catalog_items = items if items else summaries
            
            # Match items to UPCs by position (SP-API returns in order)
            for idx, item in enumerate(catalog_items):
                if idx >= len(normalized_upcs):
                    break
                
                upc_key = normalized_upcs[idx]
                
                # Extract ASIN from item
                asin = (
                    item.get("asin") or
                    item.get("productId") or
                    item.get("identifiers", {}).get("marketplaceASIN", {}).get("asin") or
                    (item.get("identifiers", {}) or {}).get("asin")
                )
                
                if asin:
                    upc_to_asin[upc_key] = asin
                    # Also map original UPC format
                    original_upc = upc_to_original.get(upc_key)
                    if original_upc and original_upc != upc_key:
                        upc_to_asin[original_upc] = asin
            
            # Build result dictionary - map all input UPCs to ASINs (or None)
            results = {}
            for upc in upcs_limited:
                upc_clean = str(upc).strip().replace("-", "").replace(" ", "").replace(".0", "")
                if len(upc_clean) == 14:
                    upc_clean = upc_clean[1:]
                
                # Try normalized first, then original
                asin = upc_to_asin.get(upc_clean) or upc_to_asin.get(upc)
                results[upc] = asin
            
            success_count = sum(1 for asin in results.values() if asin)
            logger.info(f"✅ Batch UPC conversion: {success_count}/{len(upcs_limited)} successful")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch UPC conversion: {e}", exc_info=True)
            return {upc: None for upc in upcs_limited}
    
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
        clean = str(value).strip().replace("-", "").replace(" ", "").replace(".0", "")
        
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
        
        clean = str(value).strip().replace("-", "").replace(" ", "").replace(".0", "")
        
        if self.is_valid_upc(clean):
            return clean
        
        return None


# Singleton instance
upc_converter = UPCConverter()
