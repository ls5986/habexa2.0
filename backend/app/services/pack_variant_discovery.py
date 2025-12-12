"""
Pack Variant Discovery Service

Discovers all pack size variants (1-pack, 2-pack, 3-pack, etc.) for a product
by searching SP-API variations, Keepa product families, and UPC patterns.
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal

from app.services.sp_api_client import sp_api_client
from app.services.keepa_client import keepa_client
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)


class PackVariantDiscovery:
    """Discover pack size variants for a product."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    async def discover_variants(
        self,
        product_id: str,
        base_asin: str,
        upc: Optional[str] = None,
        title: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Discover all pack size variants for a product.
        
        Returns list of variants with:
        - asin
        - pack_size
        - price
        - fees
        - calculated PPU
        """
        variants = []
        
        # Method 1: SP-API Variations
        sp_variants = await self._discover_sp_api_variations(base_asin)
        variants.extend(sp_variants)
        
        # Method 2: Keepa Product Family
        keepa_variants = await self._discover_keepa_family(base_asin, upc, title)
        variants.extend(keepa_variants)
        
        # Method 3: UPC Pattern Matching (if UPC provided)
        if upc:
            upc_variants = await self._discover_upc_patterns(upc, title)
            variants.extend(upc_variants)
        
        # Deduplicate by ASIN
        seen_asins = set()
        unique_variants = []
        for variant in variants:
            if variant['asin'] not in seen_asins:
                seen_asins.add(variant['asin'])
                unique_variants.append(variant)
        
        # Calculate PPU for each variant
        for variant in unique_variants:
            variant['ppu'] = await self._calculate_variant_ppu(
                product_id,
                variant['asin'],
                variant['pack_size'],
                variant.get('price')
            )
        
        # Sort by PPU (highest first)
        unique_variants.sort(key=lambda x: x.get('ppu', 0), reverse=True)
        
        # Mark recommended variant (highest PPU)
        if unique_variants:
            unique_variants[0]['is_recommended'] = True
            unique_variants[0]['recommendation_reason'] = 'Highest PPU'
        
        return unique_variants
    
    async def _discover_sp_api_variations(self, asin: str) -> List[Dict[str, Any]]:
        """Discover variants via SP-API GetCatalogItem variations."""
        variants = []
        
        try:
            # Get catalog item with variations
            catalog_item = await sp_api_client.get_catalog_item(asin, marketplace_id="ATVPDKIKX0DER")
            
            if not catalog_item:
                return variants
            
            # Check for parent ASIN and variations
            parent_asin = catalog_item.get('parent_asin')
            variation_count = catalog_item.get('variation_count', 0)
            
            if variation_count > 0:
                # Get all variations
                # Note: SP-API doesn't directly return all variations in one call
                # We'd need to use GetItemOffers or search by parent ASIN
                logger.info(f"Found {variation_count} variations for {asin}")
                
                # For now, return the base ASIN as 1-pack
                variants.append({
                    'asin': asin,
                    'pack_size': 1,
                    'source': 'sp_api_base',
                    'price': catalog_item.get('buy_box_price')
                })
        
        except Exception as e:
            logger.debug(f"SP-API variation discovery failed: {e}")
        
        return variants
    
    async def _discover_keepa_family(
        self,
        asin: str,
        upc: Optional[str] = None,
        title: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Discover variants via Keepa product family search."""
        variants = []
        
        try:
            # Keepa can find related products by UPC or title
            # This is a simplified version - real implementation would use Keepa's product search
            
            # For now, return base ASIN
            variants.append({
                'asin': asin,
                'pack_size': 1,
                'source': 'keepa_base',
                'price': None
            })
        
        except Exception as e:
            logger.debug(f"Keepa family discovery failed: {e}")
        
        return variants
    
    async def _discover_upc_patterns(
        self,
        upc: str,
        title: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Discover variants by searching for common pack size patterns in title/UPC."""
        variants = []
        
        if not title:
            return variants
        
        # Common pack size patterns in titles
        pack_patterns = [
            (r'(\d+)\s*pack', 'pack'),
            (r'(\d+)\s*ct', 'count'),
            (r'(\d+)\s*count', 'count'),
            (r'(\d+)\s*pc', 'piece'),
            (r'(\d+)\s*piece', 'piece'),
            (r'case\s*of\s*(\d+)', 'case'),
            (r'(\d+)\s*unit', 'unit')
        ]
        
        import re
        title_lower = title.lower()
        
        for pattern, _ in pack_patterns:
            match = re.search(pattern, title_lower)
            if match:
                pack_size = int(match.group(1))
                if 1 <= pack_size <= 100:  # Reasonable range
                    variants.append({
                        'asin': None,  # Will need to be discovered
                        'pack_size': pack_size,
                        'source': 'title_pattern',
                        'price': None
                    })
        
        return variants
    
    async def _calculate_variant_ppu(
        self,
        product_id: str,
        variant_asin: str,
        pack_size: int,
        variant_price: Optional[float] = None
    ) -> float:
        """Calculate Profit Per Unit for a variant."""
        
        # Get product source data
        try:
            product_result = supabase.table('products').select(
                '''
                id,
                buy_box_price,
                buy_box_price_365d_avg,
                fba_fees,
                referral_fee_percentage,
                product_sources(wholesale_cost, pack_size, supplier_id)
                '''
            ).eq('id', product_id).eq('user_id', self.user_id).limit(1).execute()
            
            if not product_result.data:
                return 0.0
            
            product = product_result.data[0]
            product_source = product.get('product_sources', [{}])[0] if product.get('product_sources') else {}
            
            # Get price (use variant price if available, otherwise use product price)
            sell_price = variant_price
            if not sell_price:
                sell_price = float(product.get('buy_box_price_365d_avg') or product.get('buy_box_price') or 0)
            
            # Get costs
            wholesale_cost = float(product_source.get('wholesale_cost', 0))
            supplier_pack_size = product_source.get('pack_size', 1)
            
            # Calculate unit cost
            unit_cost = wholesale_cost / supplier_pack_size if supplier_pack_size > 0 else wholesale_cost
            
            # Calculate Amazon pack cost (unit cost × Amazon pack size)
            amazon_pack_cost = unit_cost * pack_size
            
            # Get fees
            fba_fee = float(product.get('fba_fees', 0))
            referral_pct = float(product.get('referral_fee_percentage', 15.0))
            referral_fee = sell_price * (referral_pct / 100)
            
            # Calculate profit
            total_cost = amazon_pack_cost + fba_fee + referral_fee + 0.50 + 0.50  # prep + shipping
            profit = sell_price - total_cost
            
            # PPU = profit per unit
            ppu = profit / pack_size if pack_size > 0 else profit
            
            return round(float(ppu), 2)
        
        except Exception as e:
            logger.error(f"Failed to calculate PPU for variant {variant_asin}: {e}")
            return 0.0

