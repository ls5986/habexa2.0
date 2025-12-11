"""
UPC to ASIN conversion service using SP-API.
Converts UPC/EAN/GTIN to ASIN when ASIN is not available.
Supports batch conversion of up to 20 UPCs per request for efficiency.
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
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
        
        DEPRECATED: Use upc_to_asins() instead to get all matches.
        This method is kept for backward compatibility.
        
        Args:
            upc: UPC/EAN/GTIN code (12-14 digits)
            marketplace_id: Amazon marketplace ID
            
        Returns:
            First ASIN if found, None otherwise
        """
        asins, status = await self.upc_to_asins(upc, marketplace_id)
        
        if status == "found" and asins:
            return asins[0].get("asin")
        elif status == "multiple" and asins:
            # Return first ASIN even if multiple found (for backward compat)
            logger.warning(f"Multiple ASINs found for UPC {upc}, returning first: {asins[0].get('asin')}")
            return asins[0].get("asin")
        
        return None
    
    async def upc_to_asins(
        self,
        upc: str,
        marketplace_id: str = "ATVPDKIKX0DER"
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Convert UPC/EAN/GTIN to ASINs using SP-API.
        Returns all matching ASINs with full product info.
        
        Args:
            upc: UPC/EAN/GTIN code (12-14 digits)
            marketplace_id: Amazon marketplace ID
            
        Returns:
            Tuple of (list of ASIN dicts, status)
            
        Status values:
            - "found": Single ASIN found
            - "multiple": Multiple ASINs found
            - "not_found": No ASINs found
            - "error": API error or invalid UPC
            
        ASIN dict format:
            {
                "asin": "B07VRZ8TK3",
                "title": "Product Name",
                "brand": "Brand Name",
                "image": "https://...",
                "category": "Grocery"
            }
        """
        if not upc:
            return ([], "error")
        
        # Clean and validate UPC
        upc_clean = str(upc).strip().replace("-", "").replace(" ", "").replace(".0", "")
        
        # Validate UPC format
        if not upc_clean.isdigit():
            logger.warning(f"Invalid UPC format (non-numeric): {upc}")
            return ([], "error")
        
        original_length = len(upc_clean)
        
        # Handle short UPCs (9-11 digits) - Excel often strips leading zeros
        # Try padding with leading zeros to make it 12 digits
        if original_length < 12:
            logger.info(f"📏 Short UPC detected ({original_length} digits): {upc_clean} - attempting padding")
            # Pad with leading zeros to make 12 digits (UPC-A standard)
            upc_padded = upc_clean.zfill(12)
            logger.info(f"   Padded to 12 digits: {upc_padded}")
            upc_clean = upc_padded
        elif original_length > 14:
            logger.warning(f"UPC too long ({original_length} digits): {upc_clean}")
            return ([], "error")
        
        # Normalize to 12 digits (UPC-A) or 13 digits (EAN-13)
        # If 14 digits, it's GTIN-14, use last 13 digits
        if len(upc_clean) == 14:
            upc_clean = upc_clean[1:]  # Remove first digit (packaging indicator)
        
        # Try initial lookup
        try:
            result = await self._try_upc_lookup(upc_clean, marketplace_id)
            
            if result:
                items = result.get("items") or []
                if not items:
                    summaries = result.get("summaries") or []
                    if summaries:
                        items = summaries
                
                if items:
                    # Found results with original/padded UPC
                    logger.info(f"✅ Found products for UPC {upc_clean} (original: {upc})")
                else:
                    # No results - try retry with variations
                    logger.info(f"⚠️ No products found for UPC {upc_clean}, trying retry variations...")
                    result = await self._retry_upc_lookup(upc_clean, upc, marketplace_id)
                    if result:
                        items = result.get("items") or []
                        if not items:
                            summaries = result.get("summaries") or []
                            if summaries:
                                items = summaries
                    else:
                        items = []
            else:
                items = []
            
            if not items:
                logger.info(f"No products found for UPC {upc_clean} (original: {upc})")
                return ([], "not_found")
            
            # Extract ASIN info from all items
            asins = []
            for item in items:
                # Try multiple locations for ASIN
                asin = (
                    item.get("asin") or
                    item.get("productId") or
                    item.get("identifiers", {}).get("marketplaceASIN", {}).get("asin") or
                    (item.get("identifiers", {}) or {}).get("asin")
                )
                
                if not asin:
                    continue
                
                # Extract summary data
                summaries = item.get("summaries") or []
                summary = summaries[0] if summaries else {}
                
                # Extract images
                images = item.get("images") or []
                main_image = None
                if images:
                    for img_set in images:
                        if isinstance(img_set, dict):
                            img_list = img_set.get("images") or []
                            for img in img_list:
                                if isinstance(img, dict) and img.get("variant") == "MAIN":
                                    main_image = img.get("link")
                                    break
                                elif isinstance(img, dict) and not main_image:
                                    # Use first image if MAIN not found
                                    main_image = img.get("link")
                
                # Build ASIN info dict
                asin_info = {
                    "asin": asin,
                    "title": summary.get("itemName") or item.get("itemName") or "",
                    "brand": summary.get("brand") or item.get("brand") or "",
                    "image": main_image,
                    "category": summary.get("productType") or summary.get("websiteDisplayGroup") or item.get("productType") or ""
                }
                
                asins.append(asin_info)
            
            if len(asins) == 0:
                logger.info(f"No valid ASINs found for UPC {upc_clean}")
                return ([], "not_found")
            elif len(asins) == 1:
                logger.info(f"✅ Found single ASIN for UPC {upc_clean}: {asins[0]['asin']}")
                return (asins, "found")
            else:
                logger.warning(f"⚠️ Found {len(asins)} ASINs for UPC {upc_clean}")
                return (asins, "multiple")
                
        except Exception as e:
            logger.error(f"Error converting UPC {upc_clean} to ASINs: {e}", exc_info=True)
            return ([], "error")
    
    async def _try_upc_lookup(self, upc: str, marketplace_id: str = "ATVPDKIKX0DER") -> Optional[dict]:
        """
        Try to lookup a single UPC using SP-API and return the result dict.
        
        Args:
            upc: The UPC code to lookup
            marketplace_id: Amazon marketplace ID
            
        Returns:
            SP-API result dict if found, None otherwise
        """
        try:
            result = await sp_api_client.search_catalog_items(
                identifiers=[upc],
                identifiers_type="UPC",
                marketplace_id=marketplace_id
            )
            return result
        except Exception as e:
            logger.warning(f"SP-API lookup failed for UPC {upc}: {e}")
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
                logger.warning(f"Invalid UPC format (non-numeric): {upc}")
                continue
            
            original_length = len(upc_clean)
            
            # Handle short UPCs (9-11 digits) - Excel often strips leading zeros
            # Pad with leading zeros to make it 12 digits (UPC-A standard)
            if original_length < 12:
                logger.info(f"📏 Short UPC detected ({original_length} digits): {upc_clean} - padding to 12 digits")
                upc_clean = upc_clean.zfill(12)
                logger.info(f"   Padded UPC: {upc_clean}")
            elif original_length > 14:
                logger.warning(f"UPC too long ({original_length} digits): {upc_clean}")
                continue
            
            # Normalize to 12 digits (UPC-A) or 13 digits (EAN-13)
            # If 14 digits, it's GTIN-14, use last 13 digits
            if len(upc_clean) == 14:
                upc_clean = upc_clean[1:]  # Remove first digit (packaging indicator)
            
            normalized_upcs.append(upc_clean)
            upc_to_original[upc_clean] = upc
        
        if not normalized_upcs:
            return {}
        
        # Batch convert using SP-API catalog search
        try:
            logger.info(f"🔍 Calling SP-API catalog search for {len(normalized_upcs)} UPCs...")
            logger.info(f"   Normalized UPCs: {normalized_upcs}")
            
            result = await sp_api_client.search_catalog_items(
                identifiers=normalized_upcs,
                identifiers_type="UPC",
                marketplace_id=marketplace_id
            )
            
            logger.info(f"📦 SP-API response received:")
            logger.info(f"   Response type: {type(result)}")
            if isinstance(result, dict):
                logger.info(f"   Response keys: {list(result.keys())}")
                items = result.get("items") or []
                summaries = result.get("summaries") or []
                logger.info(f"   Items count: {len(items)}")
                logger.info(f"   Summaries count: {len(summaries)}")
                
                # Log first item structure for debugging
                if items:
                    import json
                    first_item = items[0]
                    logger.info(f"   First item keys: {list(first_item.keys())}")
                    logger.info(f"   First item ASIN: {first_item.get('asin')}")
                    logger.info(f"   First item identifiers: {first_item.get('identifiers')}")
            
            if not result:
                logger.warning(f"❌ No response from SP-API for batch UPC conversion")
                return {upc: None for upc in upcs_limited}
            
            # Parse results - build mapping of UPC -> ASIN
            upc_to_asin = {}
            
            # SP-API returns items - each item corresponds to one identifier
            # Items are typically returned in the same order as input identifiers
            items = result.get("items") or []
            summaries = result.get("summaries") or []
            
            logger.info(f"📊 Parsing SP-API response:")
            logger.info(f"   Items: {len(items)}, Summaries: {len(summaries)}")
            
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
                    logger.info(f"   ✅ Item {idx} (UPC {upc_key}): Found ASIN {asin}")
                    upc_to_asin[upc_key] = asin
                    # Also map original UPC format
                    original_upc = upc_to_original.get(upc_key)
                    if original_upc and original_upc != upc_key:
                        upc_to_asin[original_upc] = asin
                else:
                    logger.warning(f"   ❌ Item {idx} (UPC {upc_key}): No ASIN found in item")
                    logger.warning(f"      Item keys: {list(item.keys())}")
                    logger.warning(f"      Item identifiers: {item.get('identifiers')}")
            
            # Build result dictionary - map all input UPCs to ASINs (or None)
            results = {}
            for upc in upcs_limited:
                upc_clean = str(upc).strip().replace("-", "").replace(" ", "").replace(".0", "")
                if len(upc_clean) == 14:
                    upc_clean = upc_clean[1:]
                
                # Try normalized first, then original
                asin = upc_to_asin.get(upc_clean) or upc_to_asin.get(upc)
                results[upc] = asin
                
                if not asin:
                    logger.warning(f"   ⚠️ UPC {upc} (normalized: {upc_clean}) not found in results")
            
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
