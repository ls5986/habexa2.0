#!/usr/bin/env python3
"""
Test UPC to ASIN conversion for UPC: 860124000177
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.upc_converter import upc_converter
from app.tasks.base import run_async

async def test_upc_conversion():
    upc = "860124000177"
    print(f"Testing UPC to ASIN conversion for: {upc}")
    print("-" * 60)
    
    try:
        # Test single UPC conversion
        asin = await upc_converter.upc_to_asin(upc)
        
        if asin:
            print(f"✅ SUCCESS: UPC {upc} → ASIN {asin}")
            return asin
        else:
            print(f"❌ FAILED: No ASIN found for UPC {upc}")
            return None
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = run_async(test_upc_conversion())
    sys.exit(0 if result else 1)

