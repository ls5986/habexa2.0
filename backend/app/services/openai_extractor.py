import openai
import json
import re
from typing import Dict, Any, List, Optional
from app.core.config import settings

openai.api_key = settings.OPENAI_API_KEY


async def extract_products_from_message(raw_message: str) -> List[Dict[str, Any]]:
    """
    Use GPT-4 to extract product information from a supplier message.
    
    Returns list of products with: asin, price, moq, notes
    """
    
    system_prompt = """You are a product data extractor for Amazon wholesale deals.
Extract ALL products from the message. For each product, find:
- ASIN (10-character Amazon ID starting with B0)
- Price (the cost/wholesale price, not retail)
- MOQ (minimum order quantity)
- Any relevant notes

Return ONLY valid JSON array. If no products found, return [].

Do NOT include any explanation or markdown.

Example output:
[
  {"asin": "B08XYZ1234", "price": 45.00, "moq": 24, "notes": "Ships from NJ"},
  {"asin": "B09ABC5678", "price": 32.50, "moq": 12, "notes": null}
]"""

    user_prompt = f"""Extract products from this supplier message:

{raw_message}

Return JSON array only."""

    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
            max_tokens=2000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean up any markdown formatting
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        products = json.loads(content)
        
        # Validate ASINs
        valid_products = []
        for p in products:
            asin = p.get("asin", "")
            if re.match(r'^B0[A-Z0-9]{8}$', asin):
                valid_products.append({
                    "asin": asin,
                    "price": float(p.get("price", 0)) if p.get("price") else None,
                    "moq": int(p.get("moq", 1)) if p.get("moq") else 1,
                    "notes": p.get("notes")
                })
        
        return valid_products
        
    except Exception as e:
        print(f"OpenAI extraction error: {e}")
        
        # Fallback: regex extraction
        return extract_products_regex(raw_message)


def extract_products_regex(message: str) -> List[Dict[str, Any]]:
    """Fallback regex-based extraction."""
    
    products = []
    
    # Find all ASINs
    asins = re.findall(r'B0[A-Z0-9]{8}', message, re.IGNORECASE)
    
    # Find all prices
    prices = re.findall(r'\$?([\d,]+(?:\.\d{2})?)', message)
    
    for i, asin in enumerate(asins):
        price = None
        if i < len(prices):
            try:
                price = float(prices[i].replace(',', ''))
            except:
                pass
        
        products.append({
            "asin": asin.upper(),
            "price": price,
            "moq": 1,
            "notes": None
        })
    
    return products

