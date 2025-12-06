"""
AI-powered column mapping for CSV/Excel imports.

Uses OpenAI to intelligently detect column purposes.
"""
import os
import logging
from typing import Dict, List, Optional, Tuple, Any
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = None
if settings.OPENAI_API_KEY:
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

class ColumnMapper:
    """
    Maps CSV/Excel columns to expected product fields.
    """
    
    # Expected fields for product import
    EXPECTED_FIELDS = {
        'asin': 'Amazon ASIN identifier',
        'upc': 'Universal Product Code (barcode)',
        'sku': 'Stock Keeping Unit',
        'title': 'Product name/title/description',
        'brand': 'Brand name/manufacturer',
        'category': 'Product category',
        'cost': 'Buy cost/wholesale price/unit cost',
        'moq': 'Minimum order quantity',
        'case_pack': 'Items per case/pack size',
        'wholesale_cost_case': 'Wholesale cost per case',
        'supplier_name': 'Supplier name'
    }
    
    def __init__(self):
        self.has_openai = bool(client)
        if not self.has_openai:
            logger.warning("⚠️ OpenAI API key not set - AI column mapping disabled")
    
    async def map_columns_ai(
        self, 
        columns: List[str],
        sample_data: Optional[Dict] = None
    ) -> Dict[str, str]:
        """
        Use OpenAI to intelligently map columns.
        
        Args:
            columns: List of column names from CSV/Excel
            sample_data: Optional dict of sample data (first row)
        
        Returns:
            Dict mapping our fields to CSV columns
            e.g. {'title': 'DESCRIPTION', 'cost': 'WHOLESALE', ...}
        """
        
        if not self.has_openai:
            logger.warning("OpenAI not available, using fallback mapping")
            return self.map_columns_fallback(columns)
        
        try:
            # Build prompt for OpenAI
            prompt = self._build_mapping_prompt(columns, sample_data)
            
            logger.info("🤖 Asking OpenAI to map columns...")
            
            # Call OpenAI (synchronous call in async function - OpenAI client is sync)
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a data mapping expert. Map CSV/Excel columns to product fields. Return ONLY valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0,
                    response_format={"type": "json_object"}
                )
            )
            
            # Parse response
            mapping_json = response.choices[0].message.content
            import json
            mapping = json.loads(mapping_json)
            
            logger.info(f"✅ AI column mapping: {mapping}")
            
            return mapping.get('mapping', {})
            
        except Exception as e:
            logger.error(f"❌ OpenAI mapping failed: {e}")
            return self.map_columns_fallback(columns)
    
    def _build_mapping_prompt(
        self, 
        columns: List[str],
        sample_data: Optional[Dict] = None
    ) -> str:
        """Build prompt for OpenAI column mapping."""
        
        prompt = f"""You are mapping CSV/Excel columns to product fields.

CSV COLUMNS:
{chr(10).join(f"- {col}" for col in columns)}
"""
        
        if sample_data:
            prompt += f"""

SAMPLE DATA (first row):
{chr(10).join(f"- {col}: {sample_data.get(col, 'N/A')}" for col in list(columns)[:10])}
"""
        
        prompt += f"""

TARGET FIELDS TO MAP:
{chr(10).join(f"- {field}: {desc}" for field, desc in self.EXPECTED_FIELDS.items())}

INSTRUCTIONS:
1. Map each CSV column to the most appropriate target field
2. Only include mappings where you're confident
3. A CSV column can only map to ONE target field
4. Common patterns:
   - "UPC" → upc
   - "DESCRIPTION" or "PRODUCT NAME" → title
   - "BRAND" → brand
   - "WHOLESALE" or "COST" or "PRICE" → cost
   - "PACK" or "CASE PACK" → case_pack
5. Return ONLY valid JSON in this format:

{{
  "mapping": {{
    "title": "DESCRIPTION",
    "cost": "WHOLESALE",
    "brand": "BRAND",
    ...
  }}
}}

Return the JSON mapping now:"""
        
        return prompt
    
    def map_columns_fallback(self, columns: List[str]) -> Dict[str, str]:
        """
        Fallback column mapping using simple rules.
        Used when OpenAI is unavailable.
        """
        
        mapping = {}
        
        # Convert to lowercase for matching
        columns_lower = {col.lower(): col for col in columns}
        
        # Simple mapping rules
        rules = {
            'asin': ['asin', 'amazon asin', 'amazon_asin'],
            'upc': ['upc', 'barcode', 'upc code', 'upc_code'],
            'sku': ['sku', 'item', 'item number', 'item_number', 'product code'],
            'title': ['title', 'name', 'product name', 'description', 'product_name', 'product description'],
            'brand': ['brand', 'manufacturer', 'mfg', 'vendor'],
            'category': ['category', 'cat', 'cat1', 'department', 'dept'],
            'cost': ['cost', 'price', 'wholesale', 'unit cost', 'buy cost', 'wholesale price'],
            'moq': ['moq', 'minimum order', 'min qty', 'min_qty'],
            'case_pack': ['case pack', 'pack', 'pack size', 'units per case', 'case_pack'],
            'wholesale_cost_case': ['wholesale cost case', 'case cost', 'total deal cost'],
            'supplier_name': ['supplier', 'supplier name', 'vendor', 'vendor name']
        }
        
        for field, patterns in rules.items():
            for pattern in patterns:
                if pattern in columns_lower:
                    mapping[field] = columns_lower[pattern]
                    break
        
        logger.info(f"📋 Fallback mapping: {mapping}")
        
        return mapping
    
    def validate_mapping(self, mapping: Dict[str, str]) -> Dict:
        """
        Validate column mapping.
        
        Returns:
            {
                'valid': bool,
                'missing_required': List[str],
                'warnings': List[str]
            }
        """
        
        # Required fields
        required = ['cost']  # Only cost is truly required
        
        # Recommended fields
        recommended = ['title', 'brand', 'upc', 'asin']
        
        missing_required = [f for f in required if f not in mapping]
        missing_recommended = [f for f in recommended if f not in mapping]
        
        warnings = []
        if missing_recommended:
            warnings.append(
                f"Missing recommended fields: {', '.join(missing_recommended)}"
            )
        
        return {
            'valid': len(missing_required) == 0,
            'missing_required': missing_required,
            'missing_recommended': missing_recommended,
            'warnings': warnings
        }


# Singleton instance
column_mapper = ColumnMapper()

# Export functions for backward compatibility with upload.py
def auto_map_columns(headers: List[str], sample_data: Optional[Dict] = None) -> Dict[str, str]:
    """
    Auto-map CSV/Excel columns to product fields.
    Wrapper around ColumnMapper for backward compatibility.
    Uses fallback mapping (synchronous) for simplicity.
    
    Args:
        headers: List of column names from CSV/Excel
        sample_data: Optional dict of sample data (first row) - not used in fallback
    
    Returns:
        Dict mapping our fields to CSV columns
    """
    # Use fallback mapping (synchronous) for now
    # If AI mapping is needed, it should be called directly via map_columns_ai
    return column_mapper.map_columns_fallback(headers)


def validate_mapping(mapping_dict: Dict[str, str], headers: List[str] = None) -> Dict:
    """
    Validate column mapping.
    Wrapper around ColumnMapper.validate_mapping for backward compatibility.
    
    Args:
        mapping_dict: Dict mapping our fields to CSV columns
        headers: Optional list of headers (not used, kept for compatibility)
    
    Returns:
        {
            'valid': bool,
            'errors': List[str],  # Missing required fields
            'warnings': List[str]
        }
    """
    result = column_mapper.validate_mapping(mapping_dict)
    
    # Convert to expected format
    return {
        'valid': result['valid'],
        'errors': result.get('missing_required', []),
        'warnings': result.get('warnings', [])
    }


# Export expected fields as MAPPABLE_FIELDS for backward compatibility
MAPPABLE_FIELDS = ColumnMapper.EXPECTED_FIELDS


def apply_mapping(row: Dict[str, Any], column_mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Apply column mapping to a CSV/Excel row.
    
    Args:
        row: Dict with CSV column names as keys
        column_mapping: Dict mapping our field names to CSV column names
            e.g. {'title': 'DESCRIPTION', 'cost': 'WHOLESALE', ...}
    
    Returns:
        Dict with our field names as keys, values from row
    """
    mapped = {}
    
    # Apply mapping: for each target field, get value from CSV column
    for target_field, csv_column in column_mapping.items():
        if csv_column in row:
            value = row[csv_column]
            # Convert empty strings to None
            if isinstance(value, str) and not value.strip():
                value = None
            mapped[target_field] = value
        else:
            mapped[target_field] = None
    
    return mapped


def validate_row(mapped: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate a mapped row.
    
    Args:
        mapped: Dict with our field names as keys (from apply_mapping)
    
    Returns:
        (is_valid: bool, error_msg: str)
    """
    # Required field: cost
    if 'cost' not in mapped or mapped['cost'] is None:
        return False, "Missing required field: cost"
    
    # Try to convert cost to float
    try:
        cost = float(mapped['cost'])
        if cost <= 0:
            return False, "Cost must be greater than 0"
    except (ValueError, TypeError):
        return False, f"Invalid cost value: {mapped.get('cost')}"
    
    # Optional validation: if ASIN provided, should be valid format
    if mapped.get('asin'):
        asin = str(mapped['asin']).strip()
        if len(asin) != 10 or not asin.startswith('B'):
            # Not a hard error, just a warning - but we'll allow it
            pass
    
    return True, ""
