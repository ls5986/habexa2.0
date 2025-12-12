"""
Cost Intelligence Service

Calculates true unit costs based on supplier cost type (Unit/Pack/Case)
and Amazon pack sizes for accurate profitability.
"""
import logging
from typing import Dict, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


class CostIntelligence:
    """Calculate true unit costs based on cost types."""
    
    COST_TYPES = ['unit', 'pack', 'case']
    
    @staticmethod
    def calculate_unit_cost(
        wholesale_cost: Decimal,
        cost_type: str = 'unit',
        pack_size_for_cost: Optional[int] = None,
        case_size: Optional[int] = None
    ) -> Decimal:
        """
        Calculate true per-unit cost based on supplier cost type.
        
        Args:
            wholesale_cost: Total cost from supplier
            cost_type: 'unit', 'pack', or 'case'
            pack_size_for_cost: Pack size when cost_type = 'pack' (e.g., 12 for 12-pack)
            case_size: Case size when cost_type = 'case' (e.g., 48 for case of 48)
        
        Returns:
            True per-unit cost
            
        Examples:
            - Unit: $10 → $10/unit
            - Pack (12-pack for $48): $48 / 12 = $4/unit
            - Case (case of 48 for $200): $200 / 48 = $4.17/unit
        """
        if cost_type == 'unit':
            return Decimal(str(wholesale_cost))
        
        elif cost_type == 'pack':
            if not pack_size_for_cost or pack_size_for_cost <= 0:
                logger.warning("cost_type is 'pack' but pack_size_for_cost not provided, treating as unit")
                return Decimal(str(wholesale_cost))
            return Decimal(str(wholesale_cost)) / Decimal(str(pack_size_for_cost))
        
        elif cost_type == 'case':
            if not case_size or case_size <= 0:
                logger.warning("cost_type is 'case' but case_size not provided, treating as unit")
                return Decimal(str(wholesale_cost))
            return Decimal(str(wholesale_cost)) / Decimal(str(case_size))
        
        else:
            logger.warning(f"Unknown cost_type '{cost_type}', defaulting to unit")
            return Decimal(str(wholesale_cost))
    
    @staticmethod
    def calculate_amazon_unit_cost(
        unit_cost: Decimal,
        amazon_pack_size: int = 1
    ) -> Decimal:
        """
        Calculate cost per Amazon selling unit.
        
        Args:
            unit_cost: True per-unit cost (from calculate_unit_cost)
            amazon_pack_size: Amazon's selling pack size (1-pack, 2-pack, etc.)
        
        Returns:
            Cost per Amazon unit
            
        Example:
            - Unit cost: $4
            - Amazon sells as 2-pack
            - Amazon unit cost: $4 × 2 = $8
        """
        if not amazon_pack_size or amazon_pack_size <= 0:
            amazon_pack_size = 1
        
        return unit_cost * Decimal(str(amazon_pack_size))
    
    @staticmethod
    def calculate_cost_breakdown(
        wholesale_cost: Decimal,
        cost_type: str,
        pack_size_for_cost: Optional[int] = None,
        case_size: Optional[int] = None,
        amazon_pack_size: int = 1
    ) -> Dict:
        """
        Calculate complete cost breakdown.
        
        Returns:
            {
                'wholesale_cost': 200.00,
                'cost_type': 'case',
                'case_size': 48,
                'unit_cost': 4.17,
                'amazon_pack_size': 2,
                'cost_per_amazon_unit': 8.34,
                'breakdown_text': 'Case of 48 ($200) = $4.17/unit × 2-pack = $8.34 per Amazon unit'
            }
        """
        unit_cost = CostIntelligence.calculate_unit_cost(
            wholesale_cost, cost_type, pack_size_for_cost, case_size
        )
        
        amazon_unit_cost = CostIntelligence.calculate_amazon_unit_cost(
            unit_cost, amazon_pack_size
        )
        
        # Generate breakdown text
        breakdown_parts = []
        
        if cost_type == 'unit':
            breakdown_parts.append(f"${float(wholesale_cost):.2f}/unit")
        elif cost_type == 'pack':
            breakdown_parts.append(f"{pack_size_for_cost}-pack (${float(wholesale_cost):.2f})")
            breakdown_parts.append(f"= ${float(unit_cost):.2f}/unit")
        elif cost_type == 'case':
            breakdown_parts.append(f"Case of {case_size} (${float(wholesale_cost):.2f})")
            breakdown_parts.append(f"= ${float(unit_cost):.2f}/unit")
        
        if amazon_pack_size > 1:
            breakdown_parts.append(f"× {amazon_pack_size}-pack = ${float(amazon_unit_cost):.2f} per Amazon unit")
        
        return {
            'wholesale_cost': float(wholesale_cost),
            'cost_type': cost_type,
            'pack_size_for_cost': pack_size_for_cost,
            'case_size': case_size,
            'unit_cost': float(unit_cost),
            'amazon_pack_size': amazon_pack_size,
            'cost_per_amazon_unit': float(amazon_unit_cost),
            'breakdown_text': ' → '.join(breakdown_parts)
        }
    
    @staticmethod
    def validate_cost_type(
        cost_type: str,
        pack_size_for_cost: Optional[int] = None,
        case_size: Optional[int] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate cost type configuration.
        
        Returns:
            (is_valid, error_message)
        """
        if cost_type not in CostIntelligence.COST_TYPES:
            return False, f"Invalid cost_type '{cost_type}'. Must be one of: {', '.join(CostIntelligence.COST_TYPES)}"
        
        if cost_type == 'pack' and (not pack_size_for_cost or pack_size_for_cost <= 0):
            return False, "cost_type is 'pack' but pack_size_for_cost is required and must be > 0"
        
        if cost_type == 'case' and (not case_size or case_size <= 0):
            return False, "cost_type is 'case' but case_size is required and must be > 0"
        
        return True, None

