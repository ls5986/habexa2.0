"""
Column Mapping Service
Handles automatic column detection, mapping validation, and data transformation.
"""

from typing import Dict, List, Optional, Any
import re
from decimal import Decimal, InvalidOperation


# ============================================================================
# MAPPABLE FIELDS DEFINITIONS
# ============================================================================

MAPPABLE_FIELDS = {
    "upc": {
        "label": "UPC",
        "required": True,
        "data_type": "string",
        "description": "Universal Product Code (12-14 digit barcode)",
        "validation": r"^\d{11,14}$",
        "normalize": True,  # Pad 11-digit to 12
        "common_names": ["UPC", "GTIN", "Barcode", "Item UPC", "UPC Code", "EAN", "UPC/EAN"],
    },
    "buy_cost": {
        "label": "Buy Cost",
        "required": True,
        "data_type": "currency",
        "description": "Your cost per SINGLE UNIT from supplier (not per case)",
        "validation": "positive_number",
        "common_names": ["Unit Cost", "Wholesale", "Cost", "Price Each", "Net Cost", "Supplier Cost", "Wholesale Cost", "Buy Price"],
    },
    "promo_buy_cost": {
        "label": "Promo Buy Cost",
        "required": False,
        "data_type": "currency",
        "description": "Temporary promotional price (optional)",
        "validation": "positive_number",
        "common_names": ["Promo Cost", "Sale Price", "Deal Price", "Special Price", "Promo", "Promo Price", "TOTAL PROMO %"],
    },
    "pack_size": {
        "label": "Pack Size",
        "required": False,
        "data_type": "integer",
        "default": 1,
        "description": "Units per case/pack from supplier",
        "validation": "positive_integer",
        "common_names": ["Case Qty", "Pack Size", "Units/Case", "Case Pack", "Inner Pack", "Qty", "PACK", "Pack Qty"],
    },
    "moq": {
        "label": "MOQ",
        "required": False,
        "data_type": "integer",
        "default": 1,
        "description": "Minimum order quantity (in cases)",
        "validation": "positive_integer",
        "common_names": ["MOQ", "Min Order", "Minimum", "Min Qty", "Order Min", "Minimum Order"],
    },
    "title": {
        "label": "Product Title",
        "required": False,
        "data_type": "string",
        "description": "Product name/description from supplier",
        "common_names": ["Description", "Product Name", "Item Name", "Title", "Name", "DESCRIPTION", "Product Desc"],
    },
    "brand": {
        "label": "Brand",
        "required": False,
        "data_type": "string",
        "description": "Product brand/manufacturer",
        "common_names": ["Brand", "Manufacturer", "Brand Name", "Vendor", "Mfr", "BRAND", "Manufacturer Name"],
    },
    "supplier_sku": {
        "label": "Supplier SKU",
        "required": False,
        "data_type": "string",
        "description": "Supplier's internal product code",
        "common_names": ["SKU", "Item Number", "Item #", "Product Code", "Supplier SKU", "ITEM", "Item Code"],
    },
}


# ============================================================================
# AUTO-MAPPING LOGIC
# ============================================================================

def auto_map_columns(file_columns: List[str]) -> Dict[str, str]:
    """
    Attempt to automatically map columns based on common names.
    
    Args:
        file_columns: List of column names from the uploaded file
        
    Returns:
        Dictionary mapping field keys to column names
        Example: {"upc": "Item UPC", "buy_cost": "Wholesale Cost"}
    """
    mapping = {}
    mapped_columns = set()
    
    # Normalize file columns for comparison
    file_columns_lower = {col.lower().strip(): col for col in file_columns}
    
    for field_key, field_config in MAPPABLE_FIELDS.items():
        if field_key in mapping:  # Already mapped
            continue
            
        common_names = [n.lower() for n in field_config.get("common_names", [])]
        
        # Try exact match first
        for common in common_names:
            if common in file_columns_lower:
                original_col = file_columns_lower[common]
                if original_col not in mapped_columns:
                    mapping[field_key] = original_col
                    mapped_columns.add(original_col)
                    break
        
        # If not found, try partial match
        if field_key not in mapping:
            for file_col_lower, original_col in file_columns_lower.items():
                if original_col in mapped_columns:
                    continue
                    
                # Check if any common name is contained in column name or vice versa
                for common in common_names:
                    if common in file_col_lower or file_col_lower in common:
                        # Additional check: ensure it's a meaningful match (not just "a" in "brand")
                        if len(common) >= 3 and len(file_col_lower) >= 3:
                            mapping[field_key] = original_col
                            mapped_columns.add(original_col)
                            break
                
                if field_key in mapping:
                    break
    
    return mapping


# ============================================================================
# MAPPING VALIDATION
# ============================================================================

def validate_mapping(mapping: Dict[str, str], file_columns: List[str]) -> Dict[str, Any]:
    """
    Validate column mapping before processing.
    
    Args:
        mapping: Dictionary mapping field keys to column names
        file_columns: List of actual column names in the file
        
    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "errors": List[Dict],
            "warnings": List[Dict]
        }
    """
    errors = []
    warnings = []
    
    # Check required fields
    for field_key, config in MAPPABLE_FIELDS.items():
        if config.get("required") and field_key not in mapping:
            errors.append({
                "field": field_key,
                "message": f"{config['label']} is required but not mapped"
            })
    
    # Check for duplicate mappings (same column mapped twice)
    mapped_cols = list(mapping.values())
    duplicates = [col for col in mapped_cols if mapped_cols.count(col) > 1]
    if duplicates:
        errors.append({
            "field": "general",
            "message": f"Column '{duplicates[0]}' is mapped to multiple fields"
        })
    
    # Validate mapped columns exist in file
    file_columns_set = set(file_columns)
    for field_key, col_name in mapping.items():
        if col_name not in file_columns_set:
            errors.append({
                "field": field_key,
                "message": f"Column '{col_name}' not found in file"
            })
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


# ============================================================================
# DATA NORMALIZATION
# ============================================================================

def normalize_upc(upc: str) -> Optional[str]:
    """Normalize UPC: strip whitespace, remove dashes, pad to 12 digits if needed."""
    if not upc:
        return None
    
    # Remove whitespace and dashes
    upc_clean = re.sub(r'[\s-]', '', str(upc))
    
    # Remove leading zeros for validation
    upc_digits = upc_clean.lstrip('0')
    
    # Validate length
    if not re.match(r'^\d{11,14}$', upc_clean):
        return None
    
    # Pad 11-digit UPCs to 12 digits (add leading zero)
    if len(upc_clean) == 11:
        upc_clean = '0' + upc_clean
    
    return upc_clean


def normalize_currency(value: Any) -> Optional[float]:
    """Convert currency string to float, handling $, commas, etc."""
    if value is None:
        return None
    
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    
    # Convert to string and clean
    value_str = str(value).strip()
    
    # Remove currency symbols, commas, whitespace
    value_str = re.sub(r'[$,\s]', '', value_str)
    
    try:
        value_float = float(value_str)
        return value_float if value_float > 0 else None
    except (ValueError, TypeError):
        return None


def normalize_integer(value: Any) -> Optional[int]:
    """Convert value to integer, handling strings with commas."""
    if value is None:
        return None
    
    if isinstance(value, int):
        return value if value > 0 else None
    
    if isinstance(value, float):
        return int(value) if value > 0 else None
    
    # Convert to string and clean
    value_str = str(value).strip()
    value_str = re.sub(r'[,]', '', value_str)
    
    try:
        value_int = int(float(value_str))  # Handle "12.0" -> 12
        return value_int if value_int > 0 else None
    except (ValueError, TypeError):
        return None


# ============================================================================
# APPLY MAPPING TO ROW
# ============================================================================

def apply_mapping(row: Dict[str, Any], column_mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Apply column mapping to a single row of data.
    
    Args:
        row: Dictionary with original column names as keys
        column_mapping: Dictionary mapping field keys to column names
        
    Returns:
        Dictionary with normalized field keys and values
    """
    mapped_row = {}
    
    for field_key, column_name in column_mapping.items():
        if column_name not in row:
            # Use default if available
            field_config = MAPPABLE_FIELDS.get(field_key, {})
            if "default" in field_config:
                mapped_row[field_key] = field_config["default"]
            continue
        
        raw_value = row[column_name]
        field_config = MAPPABLE_FIELDS.get(field_key, {})
        data_type = field_config.get("data_type", "string")
        
        # Normalize based on data type
        if field_key == "upc":
            mapped_row[field_key] = normalize_upc(raw_value)
        elif data_type == "currency":
            mapped_row[field_key] = normalize_currency(raw_value)
        elif data_type == "integer":
            mapped_row[field_key] = normalize_integer(raw_value)
        else:  # string
            mapped_row[field_key] = str(raw_value).strip() if raw_value else None
    
    return mapped_row


# ============================================================================
# VALIDATE ROW DATA
# ============================================================================

def validate_row(row: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate a single mapped row.
    
    Args:
        row: Mapped row with normalized values
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields
    if not row.get("upc"):
        return False, "UPC is required"
    
    # Validate UPC format
    upc = row.get("upc")
    if not re.match(r'^\d{12,14}$', str(upc)):
        return False, f"Invalid UPC format: {upc}"
    
    # Check required buy_cost
    if not row.get("buy_cost") or row.get("buy_cost") <= 0:
        return False, "Buy cost is required and must be positive"
    
    return True, None

