"""
Compare ASINs and extract differences.
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class AsinComparisonService:
    """
    Compare ASINs to highlight differences.
    """
    
    def find_differences(self, asins: List[Dict]) -> List[Dict]:
        """
        Find and highlight differences between ASINs.
        """
        
        if len(asins) < 2:
            return asins
        
        # Extract common patterns
        titles = [a.get('title', '') for a in asins]
        
        # Find common prefix/suffix
        common_prefix = self._find_common_prefix(titles)
        common_suffix = self._find_common_suffix(titles)
        
        # Extract differences
        for i, asin in enumerate(asins):
            title = titles[i]
            
            # Remove common parts to show differences
            diff = title
            if common_prefix:
                diff = diff[len(common_prefix):].strip()
            if common_suffix:
                diff = diff[:-len(common_suffix)].strip()
            
            # Extract key attributes from difference
            differences = []
            
            # Check for common variation patterns
            diff_lower = diff.lower()
            colors = ['black', 'white', 'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'brown', 'gray', 'grey']
            for color in colors:
                if color in diff_lower:
                    differences.append(f"Color: {color.title()}")
                    break
            
            sizes = ['small', 'medium', 'large', 'xl', 'xxl', 'xs', 's,', 'm,', 'l,']
            for size in sizes:
                if size in diff_lower:
                    differences.append(f"Size: {size.upper().replace(',', '')}")
                    break
            
            if 'pack' in diff_lower or 'count' in diff_lower:
                # Extract numbers
                import re
                numbers = re.findall(r'\d+', diff)
                if numbers:
                    differences.append(f"Pack: {numbers[0]}")
            
            if not differences and diff:
                differences.append(diff[:50])  # Truncate long differences
            
            asin['differences'] = differences
            asin['unique_attributes'] = diff
        
        return asins
    
    def _find_common_prefix(self, strings: List[str]) -> str:
        """Find longest common prefix."""
        if not strings:
            return ""
        
        prefix = strings[0]
        for s in strings[1:]:
            while not s.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    return ""
        
        return prefix
    
    def _find_common_suffix(self, strings: List[str]) -> str:
        """Find longest common suffix."""
        if not strings:
            return ""
        
        suffix = strings[0]
        for s in strings[1:]:
            while not s.endswith(suffix):
                suffix = suffix[1:]
                if not suffix:
                    return ""
        
        return suffix


# Singleton
asin_comparison_service = AsinComparisonService()

