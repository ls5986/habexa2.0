"""
Upload Template Service
Manages CSV/Excel column mapping templates for suppliers.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.database import supabase

logger = logging.getLogger(__name__)


class UploadTemplateService:
    """Manage upload templates for CSV/Excel column mappings."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    async def create_template(
        self,
        name: str,
        supplier_id: Optional[str] = None,
        column_mappings: Dict[str, str] = None,
        default_values: Dict[str, Any] = None,
        validation_rules: List[Dict[str, Any]] = None,
        transformations: List[Dict[str, Any]] = None,
        is_default: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new upload template.
        
        Args:
            name: Template name (e.g., "KEHE Standard Format")
            supplier_id: Optional supplier ID (None for global template)
            column_mappings: Dict mapping Habexa fields to CSV columns
                Example: {"upc": "UPC Code", "wholesale_cost": "Cost"}
            default_values: Default values for missing fields
            validation_rules: List of validation rules
            transformations: List of data transformations
            is_default: Mark as default template for supplier
        """
        try:
            template = {
                'user_id': self.user_id,
                'supplier_id': supplier_id,
                'name': name,
                'column_mappings': column_mappings or {},
                'default_values': default_values or {},
                'validation_rules': validation_rules or [],
                'transformations': transformations or [],
                'is_default': is_default
            }
            
            result = supabase.table('upload_templates').insert(template).execute()
            
            if result.data:
                logger.info(f"Created upload template: {name}")
                return result.data[0]
            
            return None
        
        except Exception as e:
            logger.error(f"Error creating upload template: {e}", exc_info=True)
            raise
    
    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a template by ID."""
        try:
            result = supabase.table('upload_templates').select('*').eq(
                'id', template_id
            ).eq('user_id', self.user_id).limit(1).execute()
            
            return result.data[0] if result.data else None
        
        except Exception as e:
            logger.error(f"Error getting template: {e}", exc_info=True)
            return None
    
    async def get_default_template(self, supplier_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the default template for a supplier (or global)."""
        try:
            query = supabase.table('upload_templates').select('*').eq(
                'user_id', self.user_id
            ).eq('is_default', True)
            
            if supplier_id:
                query = query.eq('supplier_id', supplier_id)
            else:
                query = query.is_('supplier_id', 'null')
            
            result = query.limit(1).execute()
            
            return result.data[0] if result.data else None
        
        except Exception as e:
            logger.error(f"Error getting default template: {e}", exc_info=True)
            return None
    
    async def list_templates(self, supplier_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all templates for user (optionally filtered by supplier)."""
        try:
            query = supabase.table('upload_templates').select('*').eq('user_id', self.user_id)
            
            if supplier_id:
                query = query.eq('supplier_id', supplier_id)
            
            result = query.order('created_at', desc=True).execute()
            
            return result.data or []
        
        except Exception as e:
            logger.error(f"Error listing templates: {e}", exc_info=True)
            return []
    
    async def update_template(
        self,
        template_id: str,
        name: Optional[str] = None,
        column_mappings: Optional[Dict[str, str]] = None,
        default_values: Optional[Dict[str, Any]] = None,
        validation_rules: Optional[List[Dict[str, Any]]] = None,
        transformations: Optional[List[Dict[str, Any]]] = None,
        is_default: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a template."""
        try:
            update_data = {}
            
            if name is not None:
                update_data['name'] = name
            if column_mappings is not None:
                update_data['column_mappings'] = column_mappings
            if default_values is not None:
                update_data['default_values'] = default_values
            if validation_rules is not None:
                update_data['validation_rules'] = validation_rules
            if transformations is not None:
                update_data['transformations'] = transformations
            if is_default is not None:
                update_data['is_default'] = is_default
            
            update_data['updated_at'] = datetime.utcnow().isoformat()
            
            result = supabase.table('upload_templates').update(update_data).eq(
                'id', template_id
            ).eq('user_id', self.user_id).execute()
            
            return result.data[0] if result.data else None
        
        except Exception as e:
            logger.error(f"Error updating template: {e}", exc_info=True)
            raise
    
    async def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        try:
            supabase.table('upload_templates').delete().eq(
                'id', template_id
            ).eq('user_id', self.user_id).execute()
            
            logger.info(f"Deleted upload template: {template_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting template: {e}", exc_info=True)
            return False
    
    async def auto_detect_template(self, file_headers: List[str], supplier_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Auto-detect which template to use based on file headers.
        
        Uses fuzzy matching to find the best matching template.
        """
        try:
            # Get all templates for supplier (or global)
            templates = await self.list_templates(supplier_id)
            
            if not templates:
                return None
            
            best_match = None
            best_score = 0
            
            for template in templates:
                mappings = template.get('column_mappings', {})
                template_columns = list(mappings.values())
                
                # Calculate match score (how many columns match)
                matches = sum(1 for col in template_columns if any(
                    col.lower().strip() == header.lower().strip() for header in file_headers
                ))
                
                score = matches / len(template_columns) if template_columns else 0
                
                if score > best_score and score >= 0.5:  # At least 50% match
                    best_score = score
                    best_match = template
            
            return best_match
        
        except Exception as e:
            logger.error(f"Error auto-detecting template: {e}", exc_info=True)
            return None
    
    def apply_template_to_row(
        self,
        template: Dict[str, Any],
        row: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply template mappings and transformations to a data row.
        
        Returns mapped and transformed row data.
        """
        try:
            mappings = template.get('column_mappings', {})
            default_values = template.get('default_values', {})
            transformations = template.get('transformations', [])
            
            mapped_row = {}
            
            # Apply column mappings
            for habexa_field, csv_column in mappings.items():
                value = row.get(csv_column)
                
                # Apply transformation if exists
                for trans in transformations:
                    if trans.get('field') == csv_column:
                        value = self._apply_transformation(value, trans)
                
                mapped_row[habexa_field] = value
            
            # Apply default values for missing fields
            for field, default_value in default_values.items():
                if field not in mapped_row or mapped_row[field] is None:
                    mapped_row[field] = default_value
            
            return mapped_row
        
        except Exception as e:
            logger.error(f"Error applying template to row: {e}", exc_info=True)
            return row
    
    def _apply_transformation(self, value: Any, transformation: Dict[str, Any]) -> Any:
        """Apply a single transformation to a value."""
        if value is None:
            return value
        
        trans_type = transformation.get('transformation')
        
        if trans_type == 'remove_dashes':
            return str(value).replace('-', '').replace('_', '')
        
        elif trans_type == 'parse_currency':
            # Remove $, commas, etc.
            if isinstance(value, str):
                return float(value.replace('$', '').replace(',', '').strip())
            return float(value)
        
        elif trans_type == 'uppercase':
            return str(value).upper()
        
        elif trans_type == 'lowercase':
            return str(value).lower()
        
        elif trans_type == 'strip_whitespace':
            return str(value).strip()
        
        elif trans_type == 'parse_integer':
            return int(float(str(value).replace(',', '')))
        
        elif trans_type == 'parse_decimal':
            return float(str(value).replace(',', ''))
        
        return value
    
    async def validate_row(self, template: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a row against template validation rules.
        
        Returns: {
            'valid': bool,
            'errors': List[str]
        }
        """
        try:
            validation_rules = template.get('validation_rules', [])
            errors = []
            
            for rule in validation_rules:
                field = rule.get('field')
                rule_type = rule.get('rule')
                
                value = row.get(field)
                
                if rule_type == 'required' and (value is None or value == ''):
                    errors.append(f"{field} is required")
                
                elif rule_type == 'length':
                    if value:
                        length = len(str(value))
                        min_len = rule.get('min')
                        max_len = rule.get('max')
                        
                        if min_len and length < min_len:
                            errors.append(f"{field} must be at least {min_len} characters")
                        if max_len and length > max_len:
                            errors.append(f"{field} must be at most {max_len} characters")
                
                elif rule_type == 'min' and value is not None:
                    min_val = rule.get('value')
                    try:
                        num_val = float(value)
                        if num_val < min_val:
                            errors.append(f"{field} must be at least {min_val}")
                    except:
                        pass
                
                elif rule_type == 'max' and value is not None:
                    max_val = rule.get('value')
                    try:
                        num_val = float(value)
                        if num_val > max_val:
                            errors.append(f"{field} must be at most {max_val}")
                    except:
                        pass
            
            return {
                'valid': len(errors) == 0,
                'errors': errors
            }
        
        except Exception as e:
            logger.error(f"Error validating row: {e}", exc_info=True)
            return {
                'valid': False,
                'errors': [str(e)]
            }

