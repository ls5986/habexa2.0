"""
Brand Restriction Detection Service

Automatically detects and flags restricted brands during product import.
"""
import logging
from typing import Dict, Optional, List
import re

from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)


class BrandRestrictionDetector:
    """Detect brand restrictions for products."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    def normalize_brand_name(self, brand: str) -> str:
        """Normalize brand name for matching."""
        if not brand:
            return ""
        return re.sub(r'[^\w\s]', '', brand.lower().strip())
    
    async def detect_and_flag(
        self,
        product_id: str,
        brand_name: str,
        supplier_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Detect brand restriction status and create/update product_brand_flags.
        
        Returns:
        {
            'brand_status': 'unrestricted' | 'supplier_restricted' | 'globally_restricted' | 'requires_approval' | 'unknown',
            'restriction_id': UUID or None,
            'override_id': UUID or None,
            'message': str
        }
        """
        if not brand_name:
            return {
                'brand_status': 'unknown',
                'message': 'No brand name provided'
            }
        
        normalized_brand = self.normalize_brand_name(brand_name)
        
        # Check global restrictions
        global_restriction = await self._check_global_restriction(normalized_brand)
        
        # Check supplier override
        supplier_override = None
        if supplier_id:
            supplier_override = await self._check_supplier_override(supplier_id, normalized_brand)
        
        # Determine status
        brand_status = self._determine_status(global_restriction, supplier_override)
        
        # Create/update product_brand_flags
        await self._update_product_flag(
            product_id,
            brand_name,
            brand_status,
            global_restriction.get('id') if global_restriction else None,
            supplier_override.get('id') if supplier_override else None
        )
        
        return {
            'brand_status': brand_status,
            'restriction_id': global_restriction.get('id') if global_restriction else None,
            'override_id': supplier_override.get('id') if supplier_override else None,
            'message': self._get_status_message(brand_status, global_restriction, supplier_override)
        }
    
    async def _check_global_restriction(self, normalized_brand: str) -> Optional[Dict]:
        """Check if brand is globally restricted."""
        try:
            result = supabase.table('brand_restrictions').select('*').eq(
                'brand_name_normalized', normalized_brand
            ).limit(1).execute()
            
            if result.data:
                return result.data[0]
            return None
        
        except Exception as e:
            logger.error(f"Failed to check global restriction: {e}")
            return None
    
    async def _check_supplier_override(
        self,
        supplier_id: str,
        normalized_brand: str
    ) -> Optional[Dict]:
        """Check if supplier has override for this brand."""
        try:
            result = supabase.table('supplier_brand_overrides').select('*').eq(
                'supplier_id', supplier_id
            ).eq('brand_name_normalized', normalized_brand).limit(1).execute()
            
            if result.data:
                return result.data[0]
            return None
        
        except Exception as e:
            logger.error(f"Failed to check supplier override: {e}")
            return None
    
    def _determine_status(
        self,
        global_restriction: Optional[Dict],
        supplier_override: Optional[Dict]
    ) -> str:
        """Determine brand status based on restrictions and overrides."""
        
        # Supplier override takes precedence
        if supplier_override:
            override_type = supplier_override.get('override_type')
            if override_type == 'can_sell':
                return 'unrestricted'
            elif override_type == 'cannot_sell':
                return 'supplier_restricted'
            elif override_type == 'requires_approval':
                return 'requires_approval'
        
        # Check global restriction
        if global_restriction:
            restriction_type = global_restriction.get('restriction_type')
            if restriction_type == 'globally_gated':
                return 'globally_restricted'
            elif restriction_type == 'seller_specific':
                return 'requires_approval'
            elif restriction_type == 'category_gated':
                return 'requires_approval'
            elif restriction_type == 'ungated':
                return 'unrestricted'
        
        # Unknown if no data
        return 'unknown'
    
    async def _update_product_flag(
        self,
        product_id: str,
        brand_name: str,
        brand_status: str,
        restriction_id: Optional[str],
        override_id: Optional[str]
    ):
        """Create or update product_brand_flags record."""
        try:
            # Check if flag exists
            existing = supabase.table('product_brand_flags').select('id').eq(
                'product_id', product_id
            ).eq('brand_name', brand_name).limit(1).execute()
            
            flag_data = {
                'product_id': product_id,
                'user_id': self.user_id,
                'brand_name': brand_name,
                'brand_status': brand_status,
                'restriction_id': restriction_id,
                'override_id': override_id,
                'detection_method': 'auto',
                'detected_at': 'now()'
            }
            
            if existing.data:
                # Update existing
                supabase.table('product_brand_flags').update(flag_data).eq(
                    'id', existing.data[0]['id']
                ).execute()
            else:
                # Create new
                supabase.table('product_brand_flags').insert(flag_data).execute()
        
        except Exception as e:
            logger.error(f"Failed to update product flag: {e}")
    
    def _get_status_message(
        self,
        brand_status: str,
        global_restriction: Optional[Dict],
        supplier_override: Optional[Dict]
    ) -> str:
        """Get human-readable status message."""
        messages = {
            'unrestricted': '✅ Brand is unrestricted - can sell',
            'supplier_restricted': '⚠️ Supplier restriction - cannot sell this brand',
            'globally_restricted': '🚫 Globally gated brand - cannot sell',
            'requires_approval': '⚠️ Requires approval to sell this brand',
            'unknown': '❓ Brand restriction status unknown'
        }
        
        return messages.get(brand_status, 'Unknown status')
    
    async def add_global_restriction(
        self,
        brand_name: str,
        restriction_type: str,
        category: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """Add a brand to the global restrictions database."""
        normalized = self.normalize_brand_name(brand_name)
        
        try:
            # Check if exists
            existing = supabase.table('brand_restrictions').select('id').eq(
                'brand_name_normalized', normalized
            ).limit(1).execute()
            
            restriction_data = {
                'brand_name': brand_name,
                'brand_name_normalized': normalized,
                'restriction_type': restriction_type,
                'category': category,
                'notes': notes,
                'verified_by': self.user_id,
                'verification_source': 'manual'
            }
            
            if existing.data:
                # Update
                result = supabase.table('brand_restrictions').update(restriction_data).eq(
                    'id', existing.data[0]['id']
                ).execute()
                return result.data[0] if result.data else None
            else:
                # Insert
                result = supabase.table('brand_restrictions').insert(restriction_data).execute()
                return result.data[0] if result.data else None
        
        except Exception as e:
            logger.error(f"Failed to add global restriction: {e}")
            raise

