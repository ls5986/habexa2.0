"""
Prep Center Service
Handles prep center management, fee calculation, product assignment, and cost breakdown.
"""
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)


class PrepCenterService:
    """
    Service for managing prep centers, calculating fees, and assigning products.
    """
    
    @staticmethod
    def calculate_prep_cost(
        product: Dict[str, Any],
        prep_center_id: str,
        required_services: List[Dict[str, Any]],
        quantity: int = 1
    ) -> Dict[str, Any]:
        """
        Calculate total prep cost for a product based on required services.
        
        Args:
            product: Product data with weight, dimensions, etc.
            prep_center_id: Prep center ID
            required_services: List of service configs [{"service_code": "FNSKU", "fee_id": "uuid"}]
            quantity: Quantity of units
        
        Returns:
            {
                'total_cost': Decimal,
                'unit_cost': Decimal,
                'breakdown': Dict[str, Decimal],
                'services': List[Dict]
            }
        """
        try:
            # Get all fees for this prep center
            fees_res = supabase.table("prep_center_fees")\
                .select("*")\
                .eq("prep_center_id", prep_center_id)\
                .eq("is_active", True)\
                .execute()
            
            fees = {fee["id"]: fee for fee in fees_res.data or []}
            
            total_cost = Decimal('0')
            breakdown = {}
            service_details = []
            
            for service in required_services:
                fee_id = service.get("fee_id")
                service_code = service.get("service_code")
                
                if not fee_id or fee_id not in fees:
                    logger.warning(f"Fee {fee_id} not found for service {service_code}")
                    continue
                
                fee = fees[fee_id]
                service_cost = PrepCenterService._calculate_service_cost(
                    fee, product, quantity
                )
                
                if service_cost:
                    total_cost += service_cost
                    breakdown[service_code] = float(service_cost)
                    service_details.append({
                        "service_code": service_code,
                        "service_name": fee.get("service_name"),
                        "fee_id": fee_id,
                        "cost": float(service_cost),
                        "fee_type": fee.get("fee_type")
                    })
            
            unit_cost = total_cost / Decimal(str(quantity)) if quantity > 0 else total_cost
            
            return {
                "total_cost": float(total_cost),
                "unit_cost": float(unit_cost),
                "breakdown": breakdown,
                "services": service_details
            }
            
        except Exception as e:
            logger.error(f"Error calculating prep cost: {e}", exc_info=True)
            return {
                "total_cost": 0.0,
                "unit_cost": 0.0,
                "breakdown": {},
                "services": []
            }
    
    @staticmethod
    def _calculate_service_cost(
        fee: Dict[str, Any],
        product: Dict[str, Any],
        quantity: int
    ) -> Optional[Decimal]:
        """
        Calculate cost for a single service based on fee structure.
        
        Supports:
        - per_unit: base_cost * quantity
        - per_pound: base_cost * weight * quantity
        - per_pallet: base_cost (flat)
        - per_day: base_cost * days * quantity
        - percentage: wholesale_cost * percentage_rate * quantity
        - flat: base_cost (one-time)
        """
        fee_type = fee.get("fee_type")
        base_cost = Decimal(str(fee.get("base_cost", 0)))
        
        if fee_type == "per_unit":
            # Check for tiered pricing
            tiered = fee.get("tiered_pricing")
            if tiered and isinstance(tiered, list):
                # Find matching tier
                for tier in tiered:
                    min_qty = tier.get("min_qty", 0)
                    max_qty = tier.get("max_qty")
                    
                    if quantity >= min_qty and (max_qty is None or quantity <= max_qty):
                        tier_cost = Decimal(str(tier.get("cost", base_cost)))
                        return tier_cost * Decimal(str(quantity))
            
            # No tiered pricing or no match, use base cost
            return base_cost * Decimal(str(quantity))
        
        elif fee_type == "per_pound":
            weight = Decimal(str(product.get("item_weight", 0)))
            return base_cost * weight * Decimal(str(quantity))
        
        elif fee_type == "per_pallet":
            # Flat cost per pallet (assume 1 pallet for now)
            return base_cost
        
        elif fee_type == "per_day":
            days = Decimal(str(fee.get("days", 30)))  # Default 30 days
            return base_cost * days * Decimal(str(quantity))
        
        elif fee_type == "percentage":
            wholesale_cost = Decimal(str(product.get("wholesale_cost", 0)))
            percentage = Decimal(str(fee.get("percentage_rate", 0))) / Decimal('100')
            cost = wholesale_cost * percentage * Decimal(str(quantity))
            
            # Apply min/max constraints
            min_charge = Decimal(str(fee.get("minimum_charge", 0))) if fee.get("minimum_charge") else None
            max_charge = Decimal(str(fee.get("maximum_charge", 0))) if fee.get("maximum_charge") else None
            
            if min_charge and cost < min_charge:
                cost = min_charge
            if max_charge and cost > max_charge:
                cost = max_charge
            
            return cost
        
        elif fee_type == "flat":
            return base_cost
        
        else:
            logger.warning(f"Unknown fee type: {fee_type}")
            return base_cost
    
    @staticmethod
    def determine_required_services(product: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Determine required prep services based on product characteristics.
        
        Returns list of service configs:
        [{"service_code": "FNSKU", "fee_id": "uuid"}, ...]
        """
        services = []
        
        # Always need FNSKU labeling for FBA
        services.append({
            "service_code": "FNSKU",
            "service_name": "FNSKU Labeling"
        })
        
        # Determine if polybagging needed
        needs_polybagging = PrepCenterService._needs_polybagging(product)
        if needs_polybagging:
            bag_size = PrepCenterService._determine_bag_size(product)
            services.append({
                "service_code": f"POLYBAG_{bag_size}",
                "service_name": f"Polybagging - {bag_size}"
            })
        
        # Bubble wrap for fragile items
        if product.get("is_fragile") or product.get("category") == "Glass":
            services.append({
                "service_code": "BUBBLE_WRAP",
                "service_name": "Bubble Wrap - Light"
            })
        
        # Hazmat handling
        if product.get("is_hazmat"):
            services.append({
                "service_code": "HAZMAT",
                "service_name": "Hazmat Handling"
            })
        
        # Storage (estimate 30 days)
        services.append({
            "service_code": "STORAGE",
            "service_name": "Storage - 30 days",
            "quantity_days": 30
        })
        
        return services
    
    @staticmethod
    def _needs_polybagging(product: Dict[str, Any]) -> bool:
        """Determine if product needs polybagging."""
        # Categories that typically need polybagging
        needs_polybagging_categories = [
            "Baby Products",
            "Health & Personal Care",
            "Beauty & Personal Care",
            "Food & Beverage"
        ]
        
        category = product.get("category", "")
        return category in needs_polybagging_categories
    
    @staticmethod
    def _determine_bag_size(product: Dict[str, Any]) -> str:
        """Determine polybag size based on product dimensions."""
        # Simple logic - can be enhanced
        length = float(product.get("item_length", 0) or 0)
        width = float(product.get("item_width", 0) or 0)
        height = float(product.get("item_height", 0) or 0)
        
        max_dimension = max(length, width, height)
        
        if max_dimension <= 6:
            return "SMALL"
        elif max_dimension <= 12:
            return "MEDIUM"
        else:
            return "LARGE"
    
    @staticmethod
    def find_matching_fees(
        prep_center_id: str,
        service_code: str,
        product: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find matching fee for a service code at a prep center.
        
        Returns fee configuration or None.
        """
        try:
            fees_res = supabase.table("prep_center_fees")\
                .select("*")\
                .eq("prep_center_id", prep_center_id)\
                .eq("is_active", True)\
                .or_(f"service_code.eq.{service_code},service_name.ilike.%{service_code}%")\
                .execute()
            
            if fees_res.data:
                # Return first match (can be enhanced with better matching logic)
                return fees_res.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding matching fee: {e}", exc_info=True)
            return None
    
    @staticmethod
    def auto_assign_prep_center(
        product: Dict[str, Any],
        user_id: str,
        strategy: str = "cheapest"
    ) -> Optional[Dict[str, Any]]:
        """
        Auto-assign product to best prep center based on strategy.
        
        Strategies:
        - "cheapest": Lowest total cost
        - "fastest": Shortest turnaround (if tracked)
        - "capability": Best match for product requirements
        
        Returns assignment data or None.
        """
        try:
            # Get all active prep centers for user
            centers_res = supabase.table("prep_centers")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("status", "active")\
                .execute()
            
            centers = centers_res.data or []
            
            if not centers:
                return None
            
            # Determine required services
            required_services = PrepCenterService.determine_required_services(product)
            
            # Find matching fees for each service at each center
            best_center = None
            best_cost = None
            
            for center in centers:
                center_id = center["id"]
                
                # Check if center has required capabilities
                if not PrepCenterService._center_has_capabilities(center, product, required_services):
                    continue
                
                # Match services to fees
                matched_services = []
                for service in required_services:
                    service_code = service.get("service_code")
                    fee = PrepCenterService.find_matching_fees(center_id, service_code, product)
                    
                    if fee:
                        matched_services.append({
                            "service_code": service_code,
                            "service_name": service.get("service_name"),
                            "fee_id": fee["id"]
                        })
                
                if not matched_services:
                    continue  # Center doesn't offer required services
                
                # Calculate total cost
                cost_result = PrepCenterService.calculate_prep_cost(
                    product, center_id, matched_services, quantity=1
                )
                
                total_cost = cost_result.get("unit_cost", float('inf'))
                
                if best_cost is None or total_cost < best_cost:
                    best_cost = total_cost
                    best_center = center
                    best_services = matched_services
                    best_breakdown = cost_result
            
            if not best_center:
                return None
            
            return {
                "prep_center_id": best_center["id"],
                "prep_center_name": best_center["company_name"],
                "required_services": best_services,
                "total_prep_cost_per_unit": best_breakdown.get("unit_cost", 0),
                "breakdown": best_breakdown.get("breakdown", {}),
                "assignment_reason": f"auto_{strategy}"
            }
            
        except Exception as e:
            logger.error(f"Error auto-assigning prep center: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _center_has_capabilities(
        center: Dict[str, Any],
        product: Dict[str, Any],
        required_services: List[Dict[str, Any]]
    ) -> bool:
        """Check if prep center has required capabilities."""
        capabilities = center.get("capabilities", {})
        
        # Check hazmat capability
        if product.get("is_hazmat"):
            if not capabilities.get("hazmat", False):
                return False
        
        # Check for required service capabilities
        for service in required_services:
            service_code = service.get("service_code", "")
            
            if "POLYBAG" in service_code and not capabilities.get("polybagging", False):
                return False
            
            if "HAZMAT" in service_code and not capabilities.get("hazmat", False):
                return False
        
        return True

