"""
Prep Instructions Service
Auto-generates prep instructions for 3PL when orders are created.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.database import supabase

logger = logging.getLogger(__name__)


class PrepInstructionsService:
    """Generate prep instructions for supplier orders."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    async def generate_prep_instructions_for_order(self, supplier_order_id: str) -> List[Dict[str, Any]]:
        """
        Generate prep instructions for all items in a supplier order.
        
        Returns list of prep instruction records.
        """
        try:
            # Get order items
            order_result = supabase.table('supplier_orders').select(
                '''
                *,
                order_items:supplier_order_items(
                    *,
                    product:products(*),
                    product_source:product_sources(*)
                )
                '''
            ).eq('id', supplier_order_id).eq('user_id', self.user_id).limit(1).execute()
            
            if not order_result.data:
                logger.warning(f"Order {supplier_order_id} not found")
                return []
            
            order = order_result.data[0]
            order_items = order.get('order_items', [])
            
            if not order_items:
                logger.info(f"No items in order {supplier_order_id}")
                return []
            
            prep_instructions = []
            
            for item in order_items:
                try:
                    instruction = await self._generate_prep_instruction_for_item(
                        supplier_order_id, item
                    )
                    if instruction:
                        prep_instructions.append(instruction)
                except Exception as e:
                    logger.error(f"Error generating prep instruction for item {item.get('id')}: {e}", exc_info=True)
                    continue
            
            logger.info(f"Generated {len(prep_instructions)} prep instructions for order {supplier_order_id}")
            
            return prep_instructions
        
        except Exception as e:
            logger.error(f"Error generating prep instructions for order {supplier_order_id}: {e}", exc_info=True)
            return []
    
    async def _generate_prep_instruction_for_item(
        self,
        supplier_order_id: str,
        order_item: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate prep instruction for a single order item."""
        try:
            product = order_item.get('product', {})
            product_source = order_item.get('product_source', {})
            
            product_id = product.get('id')
            order_item_id = order_item.get('id')
            quantity_ordered = order_item.get('quantity', 0)
            
            if not product_id:
                return None
            
            # Get supplier pack size
            supplier_pack_size = product_source.get('pack_size', 1) or 1
            
            # Calculate total units
            total_units = quantity_ordered * supplier_pack_size
            
            # Get target pack size (Amazon pack size)
            target_pack_size = product_source.get('recommended_pack_size') or product.get('package_quantity') or 1
            
            # Calculate packs to create and leftover
            packs_to_create = total_units // target_pack_size
            leftover_units = total_units % target_pack_size
            
            # Generate prep steps
            prep_steps = self._generate_prep_steps(
                product, product_source, total_units, target_pack_size, packs_to_create, leftover_units
            )
            
            # Calculate profitability for this pack size
            # Get variant data if exists
            variant_result = supabase.table('product_pack_variants').select('*').eq(
                'product_id', product_id
            ).eq('pack_size', target_pack_size).limit(1).execute()
            
            profit_per_unit = 0
            roi = 0
            total_profit = 0
            
            if variant_result.data:
                variant = variant_result.data[0]
                profit_per_unit = float(variant.get('profit_per_unit', 0))
                roi = float(variant.get('roi', 0))
                total_profit = profit_per_unit * total_units
            
            # Create prep instruction record
            prep_instruction = {
                'user_id': self.user_id,
                'supplier_order_id': supplier_order_id,
                'order_item_id': order_item_id,
                'product_id': product_id,
                'product_source_id': product_source.get('id'),
                'status': 'pending',
                'total_units_ordered': total_units,
                'target_pack_size': target_pack_size,
                'packs_to_create': packs_to_create,
                'leftover_units': leftover_units,
                'prep_steps': prep_steps,
                'profit_per_unit': profit_per_unit,
                'total_profit': total_profit,
                'roi': roi
            }
            
            # Insert into database
            result = supabase.table('prep_instructions').insert(prep_instruction).execute()
            
            if result.data:
                return result.data[0]
            return None
        
        except Exception as e:
            logger.error(f"Error generating prep instruction: {e}", exc_info=True)
            return None
    
    def _generate_prep_steps(
        self,
        product: Dict[str, Any],
        product_source: Dict[str, Any],
        total_units: int,
        target_pack_size: int,
        packs_to_create: int,
        leftover_units: int
    ) -> List[Dict[str, Any]]:
        """Generate step-by-step prep instructions."""
        steps = []
        
        # Step 1: Receive units
        steps.append({
            'step_number': 1,
            'title': f'Receive {total_units} units from supplier',
            'description': f'Receive and verify {total_units} individual units for {product.get("title", "product")}.',
            'estimated_time': '30 minutes',
            'required': True
        })
        
        # Step 2: Label with FNSKU
        asin = product.get('asin')
        fnsku = product.get('fnsku') or f'FNSKU-{asin}'  # Placeholder
        steps.append({
            'step_number': 2,
            'title': f'Label all {total_units} units with FNSKU',
            'description': f'Apply FNSKU label {fnsku} to each individual unit. Use barcode scanner to verify.',
            'estimated_time': f'{total_units * 0.5} minutes',
            'required': True,
            'fnsku': fnsku
        })
        
        # Step 3: Bundle into packs (if pack size > 1)
        if target_pack_size > 1:
            steps.append({
                'step_number': 3,
                'title': f'Bundle into {packs_to_create} {target_pack_size}-packs',
                'description': f'Group {target_pack_size} labeled units together to create {packs_to_create} sellable packs.',
                'instructions': [
                    f'Take {target_pack_size} labeled units',
                    'Place in poly bag or shrink wrap',
                    'Seal securely',
                    'Verify pack contains exactly {target_pack_size} units',
                    f'Repeat for all {packs_to_create} packs'
                ],
                'estimated_time': f'{packs_to_create * 2} minutes',
                'required': True
            })
        
        # Step 4: Handle leftover units (if any)
        if leftover_units > 0:
            steps.append({
                'step_number': 4,
                'title': f'Handle {leftover_units} leftover units',
                'description': f'{leftover_units} units remain that cannot make a full pack. Options:',
                'instructions': [
                    'Option 1: Hold for next shipment',
                    'Option 2: Return to supplier',
                    'Option 3: Sell as individual units (if allowed)'
                ],
                'estimated_time': '15 minutes',
                'required': False,
                'note': f'Recommendation: Hold for next shipment to avoid waste.'
            })
        
        # Step 5: Prep for FBA shipment
        steps.append({
            'step_number': 5,
            'title': 'Prep for FBA shipment',
            'description': 'Package all packs according to FBA requirements.',
            'instructions': [
                'Place packs in boxes per FBA guidelines',
                'Generate shipping labels',
                'Schedule pickup or drop-off',
                'Update shipment tracking'
            ],
            'estimated_time': '1 hour',
            'required': True
        })
        
        return steps
    
    async def generate_prep_instruction_pdf(self, prep_instruction_id: str) -> Optional[str]:
        """
        Generate PDF for prep instructions.
        Returns URL to PDF (stored in Supabase Storage or similar).
        
        TODO: Implement actual PDF generation using reportlab or similar.
        """
        # Placeholder - would use reportlab or similar library
        logger.warning(f"PDF generation not yet implemented for prep instruction {prep_instruction_id}")
        return None
    
    async def email_prep_instructions_to_3pl(
        self,
        prep_instruction_id: str,
        prep_center_email: str
    ) -> bool:
        """
        Email prep instructions to 3PL prep center.
        
        TODO: Integrate with email service (SendGrid).
        """
        # Placeholder
        logger.warning(f"Email to 3PL not yet implemented for prep instruction {prep_instruction_id}")
        return False

