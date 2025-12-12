"""
Template Engine Service
Handles supplier template application, formula evaluation, and data transformation.
"""
import logging
import re
from typing import Dict, Any, List, Optional
from decimal import Decimal
import math

logger = logging.getLogger(__name__)


class TemplateEngine:
    """
    Engine for applying supplier templates to uploaded files.
    Handles column mapping, calculations, transformations, and validation.
    """
    
    # Available Habexa fields
    HABEXA_FIELDS = {
        # Identifiers
        'upc': {'label': 'UPC', 'required': True, 'type': 'string'},
        'asin': {'label': 'ASIN', 'required': False, 'type': 'string'},
        'supplier_sku': {'label': 'Supplier SKU', 'required': False, 'type': 'string'},
        
        # Product Info
        'title': {'label': 'Product Title', 'required': False, 'type': 'string'},
        'brand': {'label': 'Brand', 'required': False, 'type': 'string'},
        'manufacturer': {'label': 'Manufacturer', 'required': False, 'type': 'string'},
        'category': {'label': 'Category', 'required': False, 'type': 'string'},
        
        # Pricing
        'wholesale_cost': {'label': 'Wholesale Cost (Unit)', 'required': True, 'type': 'currency'},
        'case_cost': {'label': 'Case Cost', 'required': False, 'type': 'currency'},
        'list_price': {'label': 'List Price', 'required': False, 'type': 'currency'},
        'msrp': {'label': 'MSRP', 'required': False, 'type': 'currency'},
        
        # Packaging
        'package_quantity': {'label': 'Package Quantity', 'required': False, 'type': 'number'},
        'case_pack': {'label': 'Case Pack', 'required': False, 'type': 'number'},
        
        # Other
        'is_hazmat': {'label': 'Hazmat', 'required': False, 'type': 'boolean'},
        'weight': {'label': 'Weight (lbs)', 'required': False, 'type': 'number'},
        'min_order_qty': {'label': 'Min Order Quantity', 'required': False, 'type': 'number'},
    }
    
    # Built-in transformations
    TRANSFORMATIONS = {
        'REMOVE_DASHES': lambda val: str(val).replace('-', '') if val else '',
        'REMOVE_SPACES': lambda val: str(val).replace(' ', '') if val else '',
        'UPPERCASE': lambda val: str(val).upper() if val else '',
        'LOWERCASE': lambda val: str(val).lower() if val else '',
        'TRIM': lambda val: str(val).strip() if val else '',
        'PARSE_CURRENCY': lambda val: float(re.sub(r'[$,]', '', str(val))) if val else 0.0,
        'PARSE_PERCENTAGE': lambda val: float(re.sub(r'[%]', '', str(val))) / 100 if val else 0.0,
        'ADD_LEADING_ZEROS': lambda val, length=12: str(val).zfill(int(length)) if val else '',
        'REMOVE_LEADING_ZEROS': lambda val: str(val).lstrip('0') if val else '',
    }
    
    @staticmethod
    def apply_template(
        rows: List[Dict[str, Any]],
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply template to rows of data.
        
        Args:
            rows: List of dictionaries with supplier column names as keys
            template: Template configuration with mappings, calculations, etc.
        
        Returns:
            {
                'products': List of processed products,
                'errors': List of validation errors,
                'skipped': Number of skipped rows,
                'processed': Number of successfully processed rows
            }
        """
        products = []
        errors = []
        skipped = 0
        
        column_mappings = template.get('column_mappings', {})
        calculations = template.get('calculations', [])
        default_values = template.get('default_values', {})
        transformations = template.get('transformations', [])
        validation_rules = template.get('validation_rules', {})
        row_filters = template.get('row_filters', [])
        
        for idx, row in enumerate(rows, start=1):
            try:
                # Step 1: Apply column mappings
                product = {}
                for supplier_col, habexa_field in column_mappings.items():
                    if supplier_col in row:
                        product[habexa_field] = row[supplier_col]
                
                # Step 2: Apply transformations
                for transform_config in transformations:
                    field = transform_config.get('field')
                    transform_type = transform_config.get('transform')
                    transform_params = transform_config.get('params', {})
                    
                    if field in product and transform_type in TemplateEngine.TRANSFORMATIONS:
                        transform_func = TemplateEngine.TRANSFORMATIONS[transform_type]
                        if transform_params:
                            product[field] = transform_func(product[field], **transform_params)
                        else:
                            product[field] = transform_func(product[field])
                
                # Step 3: Apply default values
                for field, value in default_values.items():
                    if field not in product or not product[field]:
                        product[field] = value
                
                # Step 4: Check row filters
                should_skip = False
                skip_reason = None
                for filter_config in row_filters:
                    condition = filter_config.get('condition', '')
                    action = filter_config.get('action', 'skip')
                    
                    if TemplateEngine._evaluate_condition(condition, product):
                        if action == 'skip':
                            should_skip = True
                            skip_reason = filter_config.get('reason', 'Row filtered out')
                            break
                        elif action == 'flag':
                            product['_flags'] = product.get('_flags', [])
                            product['_flags'].append(filter_config.get('reason', 'Flagged'))
                
                if should_skip:
                    skipped += 1
                    errors.append({
                        'row': idx,
                        'type': 'filtered',
                        'message': skip_reason
                    })
                    continue
                
                # Step 5: Apply calculations
                for calc in calculations:
                    field = calc.get('field')
                    formula = calc.get('formula', '')
                    
                    if field and formula:
                        try:
                            result = TemplateEngine._evaluate_formula(formula, product)
                            product[field] = result
                        except Exception as e:
                            logger.warning(f"Calculation error for field {field}: {e}")
                            product[field] = None
                
                # Step 6: Validate
                validation_errors = TemplateEngine._validate_product(product, validation_rules)
                if validation_errors:
                    product['_errors'] = validation_errors
                    errors.append({
                        'row': idx,
                        'type': 'validation',
                        'message': '; '.join(validation_errors),
                        'product': product
                    })
                    # Still add to products but mark as invalid
                
                products.append(product)
                
            except Exception as e:
                logger.error(f"Error processing row {idx}: {e}", exc_info=True)
                errors.append({
                    'row': idx,
                    'type': 'processing',
                    'message': str(e)
                })
                skipped += 1
        
        processed = len(products) - len([e for e in errors if e.get('type') == 'validation'])
        
        return {
            'products': products,
            'errors': errors,
            'skipped': skipped,
            'processed': processed,
            'total': len(rows)
        }
    
    @staticmethod
    def _evaluate_formula(formula: str, data: Dict[str, Any]) -> Any:
        """
        Evaluate a formula with data variables.
        
        Supports:
        - Variables: {field_name}
        - Math operations: +, -, *, /, %
        - Functions: ROUND(value, decimals), IF(condition, true_val, false_val)
        """
        try:
            # Replace {variable} with actual values
            expression = formula
            
            # Replace variables
            variable_pattern = r'\{(\w+)\}'
            def replace_var(match):
                field = match.group(1)
                value = data.get(field, 0)
                # Convert to number if possible
                try:
                    return str(float(value))
                except (ValueError, TypeError):
                    return f'"{str(value)}"'
            
            expression = re.sub(variable_pattern, replace_var, expression)
            
            # Handle ROUND function
            def round_func(match):
                value = float(match.group(1))
                decimals = int(match.group(2))
                return str(round(value, decimals))
            
            expression = re.sub(r'ROUND\(([^,]+),\s*(\d+)\)', round_func, expression)
            
            # Handle IF function (simple version)
            def if_func(match):
                condition = match.group(1)
                true_val = match.group(2)
                false_val = match.group(3)
                
                # Simple condition evaluation
                if '==' in condition:
                    parts = condition.split('==')
                    left = parts[0].strip().strip('"\'')
                    right = parts[1].strip().strip('"\'')
                    result = str(left) == str(right)
                elif '!=' in condition:
                    parts = condition.split('!=')
                    left = parts[0].strip().strip('"\'')
                    right = parts[1].strip().strip('"\'')
                    result = str(left) != str(right)
                elif '>' in condition:
                    parts = condition.split('>')
                    left = float(parts[0].strip())
                    right = float(parts[1].strip())
                    result = left > right
                elif '<' in condition:
                    parts = condition.split('<')
                    left = float(parts[0].strip())
                    right = float(parts[1].strip())
                    result = left < right
                else:
                    result = bool(condition.strip())
                
                return true_val if result else false_val
            
            expression = re.sub(r'IF\(([^,]+),\s*([^,]+),\s*([^)]+)\)', if_func, expression)
            
            # Evaluate safely (only math operations)
            # Remove any remaining non-safe characters
            safe_expression = re.sub(r'[^0-9+\-*/().\s]', '', expression)
            
            try:
                result = eval(safe_expression)
                # Convert to appropriate type
                if isinstance(result, float):
                    if result.is_integer():
                        return int(result)
                    return round(result, 2)
                return result
            except:
                # Fallback: try original expression
                return eval(expression)
                
        except Exception as e:
            logger.error(f"Formula evaluation error: {e}")
            raise ValueError(f"Invalid formula: {formula}")
    
    @staticmethod
    def _evaluate_condition(condition: str, data: Dict[str, Any]) -> bool:
        """
        Evaluate a condition string against data.
        
        Supports: ==, !=, >, <, >=, <=, CONTAINS
        """
        try:
            # Replace variables
            variable_pattern = r'\{(\w+)\}'
            def replace_var(match):
                field = match.group(1)
                value = data.get(field, '')
                return f'"{str(value)}"'
            
            condition = re.sub(variable_pattern, replace_var, condition)
            
            # Handle CONTAINS
            if 'CONTAINS' in condition:
                # CONTAINS({field}, "value")
                match = re.search(r'CONTAINS\(([^,]+),\s*"([^"]+)"\)', condition)
                if match:
                    field_value = match.group(1).strip('"\'')
                    search_value = match.group(2)
                    return search_value.lower() in str(field_value).lower()
            
            # Handle comparison operators
            if '==' in condition:
                parts = condition.split('==')
                left = parts[0].strip().strip('"\'')
                right = parts[1].strip().strip('"\'')
                return str(left) == str(right)
            elif '!=' in condition:
                parts = condition.split('!=')
                left = parts[0].strip().strip('"\'')
                right = parts[1].strip().strip('"\'')
                return str(left) != str(right)
            elif '>=' in condition:
                parts = condition.split('>=')
                left = float(parts[0].strip().strip('"\'') or 0)
                right = float(parts[1].strip().strip('"\'') or 0)
                return left >= right
            elif '<=' in condition:
                parts = condition.split('<=')
                left = float(parts[0].strip().strip('"\'') or 0)
                right = float(parts[1].strip().strip('"\'') or 0)
                return left <= right
            elif '>' in condition:
                parts = condition.split('>')
                left = float(parts[0].strip().strip('"\'') or 0)
                right = float(parts[1].strip().strip('"\'') or 0)
                return left > right
            elif '<' in condition:
                parts = condition.split('<')
                left = float(parts[0].strip().strip('"\'') or 0)
                right = float(parts[1].strip().strip('"\'') or 0)
                return left < right
            
            return bool(condition.strip())
            
        except Exception as e:
            logger.warning(f"Condition evaluation error: {e}")
            return False
    
    @staticmethod
    def _validate_product(product: Dict[str, Any], rules: Dict[str, Any]) -> List[str]:
        """
        Validate product against validation rules.
        
        Returns list of error messages.
        """
        errors = []
        
        for field, rule in rules.items():
            value = product.get(field)
            
            # Required check
            if rule.get('type') == 'required' and not value:
                errors.append(f"{field} is required")
                continue
            
            if not value:
                continue  # Skip other validations if value is empty
            
            # Regex validation
            if rule.get('type') == 'regex':
                pattern = rule.get('pattern', '')
                if pattern and not re.match(pattern, str(value)):
                    errors.append(f"{field} format invalid")
            
            # Min value
            if rule.get('type') == 'min':
                try:
                    num_value = float(value)
                    min_val = float(rule.get('value', 0))
                    if num_value < min_val:
                        errors.append(f"{field} must be >= {min_val}")
                except (ValueError, TypeError):
                    pass
            
            # Max value
            if rule.get('type') == 'max':
                try:
                    num_value = float(value)
                    max_val = float(rule.get('value', float('inf')))
                    if num_value > max_val:
                        errors.append(f"{field} must be <= {max_val}")
                except (ValueError, TypeError):
                    pass
        
        return errors
    
    @staticmethod
    def detect_template(
        filename: str,
        columns: List[str],
        supplier_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Detect matching template from filename and/or column headers.
        
        Args:
            filename: Uploaded filename
            columns: List of column names from file
            supplier_id: Optional supplier ID to narrow search
        
        Returns:
            Template configuration if match found, None otherwise
        """
        from app.services.supabase_client import supabase
        
        try:
            # Build query
            query = supabase.table('supplier_templates')\
                .select('*')\
                .eq('is_active', True)
            
            if supplier_id:
                query = query.eq('supplier_id', supplier_id)
            
            templates = query.execute()
            
            if not templates.data:
                return None
            
            # Score templates by match quality
            best_match = None
            best_score = 0
            
            for template in templates.data:
                score = 0
                
                # Check filename pattern
                filename_pattern = template.get('filename_pattern')
                if filename_pattern:
                    try:
                        if re.match(filename_pattern, filename, re.IGNORECASE):
                            score += 10
                    except:
                        pass
                
                # Check column fingerprint
                fingerprint = template.get('column_fingerprint', [])
                if fingerprint:
                    matches = sum(1 for col in fingerprint if col in columns)
                    if matches == len(fingerprint):
                        score += 20  # Perfect match
                    elif matches > 0:
                        score += matches * 2  # Partial match
                
                if score > best_score:
                    best_score = score
                    best_match = template
            
            # Return match if score is high enough
            if best_match and best_score >= 5:
                return best_match
            
            return None
            
        except Exception as e:
            logger.error(f"Template detection error: {e}", exc_info=True)
            return None
    
    @staticmethod
    def extract_column_fingerprint(columns: List[str]) -> List[str]:
        """
        Extract a fingerprint of unique columns for template matching.
        
        Returns list of distinctive column names.
        """
        # Common columns to ignore (too generic)
        common_columns = {'id', 'name', 'description', 'price', 'cost', 'quantity', 'qty'}
        
        # Return columns that are not too common
        fingerprint = [
            col for col in columns
            if col.lower() not in common_columns
        ]
        
        # Limit to top 5 most distinctive
        return fingerprint[:5]

