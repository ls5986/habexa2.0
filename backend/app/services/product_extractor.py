"""
Product extractor using OpenAI to parse supplier messages.
Extracts ASINs, prices, MOQ, and other deal info from raw text.
"""
import os
import re
import json
from typing import List, Dict, Any, Optional
import openai
import logging

logger = logging.getLogger(__name__)

# ASIN regex pattern
ASIN_PATTERN = r'\b[A-Z0-9]{10}\b'

# Common price patterns
PRICE_PATTERNS = [
    r'\$\s*(\d+(?:\.\d{2})?)',  # $10.99
    r'(\d+(?:\.\d{2})?)\s*(?:USD|usd|\$)',  # 10.99 USD
    r'(?:cost|price|buy)\s*:?\s*\$?\s*(\d+(?:\.\d{2})?)',  # cost: 10.99
]


class ProductExtractor:
    """Extract product information from supplier messages using OpenAI."""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = openai.OpenAI(api_key=api_key)
        else:
            self.client = None
        self.model = "gpt-4o-mini"
    
    async def extract_products(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract products from message text.
        
        Args:
            text: Raw message text from Telegram
            
        Returns:
            List of extracted products with asin, price, moq, notes
        """
        
        if not text or len(text.strip()) < 10:
            return []
        
        # First, try simple regex extraction
        asins = self._extract_asins_regex(text)
        
        if not asins:
            return []
        
        # If we have ASINs, use OpenAI for detailed extraction
        if self.client:
            try:
                products = await self._extract_with_openai(text, asins)
                return products
            except Exception as e:
                logger.error(f"OpenAI extraction failed: {e}")
                # Fallback to basic extraction
                return self._basic_extraction(text, asins)
        else:
            return self._basic_extraction(text, asins)
    
    def _extract_asins_regex(self, text: str) -> List[str]:
        """Extract potential ASINs using regex."""
        
        # Find all 10-character alphanumeric strings
        matches = re.findall(ASIN_PATTERN, text.upper())
        
        # Filter likely ASINs (start with B0 for products, or are all alphanumeric)
        asins = []
        for match in matches:
            # Common ASIN patterns
            if match.startswith('B0'):
                asins.append(match)
            # Also include if it looks like an ASIN (mix of letters and numbers)
            elif any(c.isdigit() for c in match) and any(c.isalpha() for c in match):
                asins.append(match)
        
        return list(set(asins))  # Remove duplicates
    
    async def _extract_with_openai(
        self,
        text: str,
        found_asins: List[str]
    ) -> List[Dict[str, Any]]:
        """Use OpenAI to extract detailed product information."""
        
        prompt = f"""Extract product deal information from this supplier message.

Message:

{text}

Already found these potential ASINs: {', '.join(found_asins)}

For each product mentioned, extract:

1. ASIN (10-character Amazon product ID)

2. Buy cost/price (the wholesale price being offered)

3. MOQ (Minimum Order Quantity, default to 1 if not mentioned)

4. Any notes (brand, condition, restrictions mentioned)

Return ONLY a JSON array of products. Example format:

[

  {{

    "asin": "B08N5WRWNW",

    "price": 12.99,

    "moq": 1,

    "title": "Product name if mentioned",

    "notes": "Any relevant notes"

  }}

]

If no valid products found, return empty array: []

Return ONLY the JSON array, no other text."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You extract product deals from supplier messages. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean up response
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            products = json.loads(content)
            
            # Validate and clean products
            valid_products = []
            for p in products:
                if "asin" in p and len(p["asin"]) == 10:
                    valid_products.append({
                        "asin": p["asin"].upper(),
                        "price": float(p.get("price") or 0) if p.get("price") else None,
                        "moq": int(p.get("moq") or 1),
                        "title": p.get("title"),
                        "notes": p.get("notes")
                    })
            
            return valid_products
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse OpenAI response: {content}")
            return self._basic_extraction(text, found_asins)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return self._basic_extraction(text, found_asins)
    
    def _basic_extraction(
        self,
        text: str,
        asins: List[str]
    ) -> List[Dict[str, Any]]:
        """Fallback basic extraction without OpenAI."""
        
        products = []
        
        # Try to find price in text
        price = None
        for pattern in PRICE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    price = float(match.group(1))
                    break
                except:
                    pass
        
        # Try to find MOQ with comprehensive patterns
        moq = self._extract_moq(text)
        
        for asin in asins:
            products.append({
                "asin": asin,
                "price": price,
                "moq": moq,
                "title": None,
                "notes": None
            })
        
        return products
    
    def _extract_moq(self, text: str) -> int:
        """Extract MOQ from message text using comprehensive patterns."""
        text_lower = text.lower()
        
        # Common MOQ patterns in supplier messages
        patterns = [
            r'moq[:\s]*(\d+)',                    # "MOQ: 6" or "MOQ 6"
            r'min(?:imum)?[:\s]*(\d+)',           # "Min: 6" or "Minimum 6"
            r'(\d+)\s*(?:min|moq|minimum)',       # "6 min" or "6 MOQ"
            r'pack\s*of\s*(\d+)',                 # "Pack of 6"
            r'(\d+)\s*pack',                      # "6 pack"
            r'(\d+)\s*(?:case|cs)',               # "6 case" or "6 cs"
            r'case\s*of\s*(\d+)',                 # "Case of 6"
            r'(\d+)\s*(?:ct|count)',              # "6 ct" or "6 count"
            r'qty[:\s]*(\d+)',                    # "Qty: 6"
            r'x\s*(\d+)\b',                       # "x6" or "x 6"
            r'\b(\d+)\s*units?\b',                # "6 units"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    moq = int(match.group(1))
                    # Sanity check - MOQ usually between 1-1000
                    if 1 <= moq <= 1000:
                        return moq
                except:
                    pass
        
        # Default to 1 if no MOQ found
        return 1
    
    def extract_amazon_links(self, text: str) -> List[str]:
        """Extract Amazon product URLs from text."""
        
        patterns = [
            r'https?://(?:www\.)?amazon\.com/(?:dp|gp/product)/([A-Z0-9]{10})',
            r'https?://(?:www\.)?amazon\.com/[^/]+/dp/([A-Z0-9]{10})',
            r'https?://amzn\.to/\w+',  # Short links
        ]
        
        asins = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            asins.extend(matches)
        
        return list(set(asins))


# Singleton
product_extractor = ProductExtractor()

