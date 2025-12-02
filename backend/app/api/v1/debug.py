"""
Debug endpoint to test all integrations.

Access at: GET /api/v1/debug/test-all
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.api.deps import get_current_user
from app.services.supabase_client import supabase
import os
import traceback

router = APIRouter(tags=["debug"])
security = HTTPBearer(auto_error=False)  # Don't auto-raise 403

async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user if authenticated, otherwise return None."""
    if not credentials:
        return None
    try:
        token = credentials.credentials
        result = supabase.auth.get_user(token)
        if result.user:
            return result.user
    except:
        pass
    return None

@router.get("/test-all")
async def test_all_integrations(current_user = Depends(get_current_user_optional)):
    """Test all integrations and return detailed status."""
    
    results = {
        "user": str(current_user.id) if current_user else "NOT_AUTHENTICATED",
        "authenticated": current_user is not None,
        "env_vars": {},
        "database": {},
        "stripe": {},
        "amazon": {},
        "telegram": {},
        "keepa": {},
        "openai": {},
    }
    
    # ==========================================
    # 1. CHECK ENVIRONMENT VARIABLES
    # ==========================================
    env_checks = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "STRIPE_SECRET_KEY",
        "STRIPE_PRICE_STARTER_MONTHLY",
        "STRIPE_PRICE_STARTER_YEARLY",
        "STRIPE_PRICE_PRO_MONTHLY",
        "STRIPE_PRICE_PRO_YEARLY",
        "STRIPE_PRICE_AGENCY_MONTHLY",
        "STRIPE_PRICE_AGENCY_YEARLY",
        "STRIPE_WEBHOOK_SECRET",
        "SPAPI_LWA_CLIENT_ID",
        "SPAPI_LWA_CLIENT_SECRET",
        "SPAPI_REFRESH_TOKEN",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "SP_API_ROLE_ARN",
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "KEEPA_API_KEY",
        "OPENAI_API_KEY",
        "SECRET_KEY",
    ]
    
    for var in env_checks:
        value = os.getenv(var)
        if value:
            # Show first/last 4 chars only for security
            if len(value) > 10:
                masked = f"{value[:4]}...{value[-4:]}"
            else:
                masked = "****"
            results["env_vars"][var] = {"status": "SET", "preview": masked}
        else:
            results["env_vars"][var] = {"status": "MISSING", "preview": None}
    
    # ==========================================
    # 2. TEST DATABASE CONNECTION
    # ==========================================
    try:
        from app.services.supabase_client import supabase
        
        # Test query
        test = supabase.table("subscriptions").select("id").limit(1).execute()
        results["database"]["connection"] = "OK"
        results["database"]["subscriptions_table"] = "EXISTS"
    except Exception as e:
        results["database"]["connection"] = "FAILED"
        results["database"]["error"] = str(e)[:200]
    
    # Test other tables
    tables_to_check = [
        "profiles", "suppliers", "analyses", "subscriptions", 
        "feature_usage", "usage_records",  # Both names for compatibility
        "amazon_connections", "telegram_sessions",
        "tracked_channels", "telegram_channels",  # Both names for compatibility
        "keepa_cache", "eligibility_cache"
    ]
    
    for table in tables_to_check:
        try:
            supabase.table(table).select("id").limit(1).execute()
            results["database"][f"{table}_table"] = "EXISTS"
        except Exception as e:
            results["database"][f"{table}_table"] = f"MISSING: {str(e)[:50]}"
    
    # ==========================================
    # 3. TEST STRIPE
    # ==========================================
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        
        if not stripe.api_key:
            results["stripe"]["status"] = "NO API KEY"
        else:
            # Test API connection
            prices = stripe.Price.list(limit=1)
            results["stripe"]["status"] = "CONNECTED"
            results["stripe"]["api_works"] = True
            
            # Check price IDs exist
            price_keys = {
                "starter_monthly": os.getenv("STRIPE_PRICE_STARTER_MONTHLY"),
                "starter_yearly": os.getenv("STRIPE_PRICE_STARTER_YEARLY"),
                "pro_monthly": os.getenv("STRIPE_PRICE_PRO_MONTHLY"),
                "pro_yearly": os.getenv("STRIPE_PRICE_PRO_YEARLY"),
                "agency_monthly": os.getenv("STRIPE_PRICE_AGENCY_MONTHLY"),
                "agency_yearly": os.getenv("STRIPE_PRICE_AGENCY_YEARLY"),
            }
            
            for key, price_id in price_keys.items():
                if price_id:
                    try:
                        price = stripe.Price.retrieve(price_id)
                        amount = price.unit_amount / 100 if price.unit_amount else 0
                        interval = price.recurring.interval if price.recurring else "one-time"
                        results["stripe"][key] = f"OK - ${amount}/{interval}"
                    except Exception as e:
                        results["stripe"][key] = f"INVALID: {str(e)[:50]}"
                else:
                    results["stripe"][key] = "NOT SET"
                    
    except ImportError:
        results["stripe"]["status"] = "stripe NOT INSTALLED"
        results["stripe"]["fix"] = "Run: pip install stripe"
    except Exception as e:
        results["stripe"]["status"] = "ERROR"
        results["stripe"]["error"] = str(e)[:200]
    
    # ==========================================
    # 4. TEST AMAZON SP-API
    # ==========================================
    try:
        from sp_api.api import Products
        from sp_api.base import Marketplaces
        
        credentials = {
            "refresh_token": os.getenv("SPAPI_REFRESH_TOKEN"),
            "lwa_app_id": os.getenv("SPAPI_LWA_CLIENT_ID"),
            "lwa_client_secret": os.getenv("SPAPI_LWA_CLIENT_SECRET"),
            "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "role_arn": os.getenv("SP_API_ROLE_ARN"),
        }
        
        missing = [k for k, v in credentials.items() if not v]
        if missing:
            results["amazon"]["status"] = "MISSING CREDENTIALS"
            results["amazon"]["missing"] = missing
        else:
            # Try a simple API call
            products_api = Products(credentials=credentials, marketplace=Marketplaces.US)
            # Just check if we can create the client
            results["amazon"]["status"] = "CREDENTIALS OK"
            results["amazon"]["client_created"] = True
            
            # Try an actual call
            try:
                response = products_api.get_competitive_pricing_for_asins(["B08N5WRWNW"])
                results["amazon"]["api_call"] = "SUCCESS"
            except Exception as api_err:
                results["amazon"]["api_call"] = f"FAILED: {str(api_err)[:100]}"
                
    except ImportError:
        results["amazon"]["status"] = "python-amazon-sp-api NOT INSTALLED"
        results["amazon"]["fix"] = "Run: pip install python-amazon-sp-api boto3"
    except Exception as e:
        results["amazon"]["status"] = "ERROR"
        results["amazon"]["error"] = str(e)[:200]
    
    # ==========================================
    # 5. TEST TELEGRAM
    # ==========================================
    try:
        from telethon import TelegramClient
        
        api_id = os.getenv("TELEGRAM_API_ID")
        api_hash = os.getenv("TELEGRAM_API_HASH")
        
        if not api_id or not api_hash:
            results["telegram"]["status"] = "MISSING CREDENTIALS"
            results["telegram"]["api_id"] = "SET" if api_id else "MISSING"
            results["telegram"]["api_hash"] = "SET" if api_hash else "MISSING"
        else:
            results["telegram"]["status"] = "CREDENTIALS OK"
            results["telegram"]["api_id"] = "SET"
            results["telegram"]["api_hash"] = "SET"
            
    except ImportError:
        results["telegram"]["status"] = "telethon NOT INSTALLED"
        results["telegram"]["fix"] = "Run: pip install telethon"
    except Exception as e:
        results["telegram"]["status"] = "ERROR"
        results["telegram"]["error"] = str(e)[:200]
    
    # ==========================================
    # 6. TEST KEEPA
    # ==========================================
    try:
        import httpx
        
        keepa_key = os.getenv("KEEPA_API_KEY")
        
        if not keepa_key:
            results["keepa"]["status"] = "NO API KEY"
        else:
            # Test token status endpoint
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.keepa.com/token",
                    params={"key": keepa_key},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results["keepa"]["status"] = "CONNECTED"
                    results["keepa"]["tokens_left"] = data.get("tokensLeft", "unknown")
                else:
                    results["keepa"]["status"] = f"API ERROR: {response.status_code}"
                    results["keepa"]["response"] = response.text[:100]
                    
    except ImportError:
        results["keepa"]["status"] = "httpx NOT INSTALLED"
        results["keepa"]["fix"] = "Run: pip install httpx"
    except Exception as e:
        results["keepa"]["status"] = "ERROR"
        results["keepa"]["error"] = str(e)[:200]
    
    # ==========================================
    # 7. TEST OPENAI
    # ==========================================
    try:
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            results["openai"]["status"] = "NO API KEY"
        else:
            client = OpenAI(api_key=api_key)
            # Quick test
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Say 'OK'"}],
                max_tokens=5
            )
            results["openai"]["status"] = "CONNECTED"
            results["openai"]["test_response"] = response.choices[0].message.content
            
    except ImportError:
        results["openai"]["status"] = "openai NOT INSTALLED"
        results["openai"]["fix"] = "Run: pip install openai"
    except Exception as e:
        results["openai"]["status"] = "ERROR"
        results["openai"]["error"] = str(e)[:200]
    
    return results

@router.get("/test-stripe-checkout")
async def test_stripe_checkout(current_user = Depends(get_current_user_optional)):
    """Test creating a Stripe checkout session."""
    
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        
        price_id = os.getenv("STRIPE_PRICE_STARTER_MONTHLY")
        if not price_id:
            return {"error": "STRIPE_PRICE_STARTER_MONTHLY not set"}
        
        # Create a test checkout session
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            success_url="http://localhost:5173/success",
            cancel_url="http://localhost:5173/cancel",
            subscription_data={"trial_period_days": 14},
        )
        
        return {
            "status": "SUCCESS",
            "checkout_url": session.url,
            "session_id": session.id,
        }
        
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.get("/test-keepa/{asin}")
async def test_keepa(asin: str, current_user = Depends(get_current_user_optional)):
    """Test fetching Keepa data for an ASIN."""
    
    try:
        import httpx
        
        keepa_key = os.getenv("KEEPA_API_KEY")
        if not keepa_key:
            return {"error": "KEEPA_API_KEY not set"}
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                "https://api.keepa.com/product",
                params={
                    "key": keepa_key,
                    "domain": 1,  # US
                    "asin": asin,
                    "history": 1,
                    "days": 30,
                }
            )
            
            if response.status_code != 200:
                return {
                    "status": "API_ERROR",
                    "code": response.status_code,
                    "response": response.text[:500]
                }
            
            data = response.json()
            
            if "error" in data:
                return {"status": "KEEPA_ERROR", "error": data["error"]}
            
            products = data.get("products", [])
            if not products:
                return {"status": "NO_DATA", "asin": asin}
            
            product = products[0]
            
            return {
                "status": "SUCCESS",
                "asin": asin,
                "title": product.get("title"),
                "brand": product.get("brand"),
                "salesRank": product.get("stats", {}).get("current", [None])[3] if product.get("stats") else None,
                "tokensUsed": data.get("tokensConsumed"),
            }
            
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.get("/test-amazon/{asin}")
async def test_amazon(asin: str, current_user = Depends(get_current_user_optional)):
    """Test Amazon SP-API for an ASIN."""
    
    try:
        from sp_api.api import Products, ListingsRestrictions
        from sp_api.base import Marketplaces
        
        credentials = {
            "refresh_token": os.getenv("SPAPI_REFRESH_TOKEN"),
            "lwa_app_id": os.getenv("SPAPI_LWA_CLIENT_ID"),
            "lwa_client_secret": os.getenv("SPAPI_LWA_CLIENT_SECRET"),
            "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "role_arn": os.getenv("SP_API_ROLE_ARN"),
        }
        
        # Test pricing
        products_api = Products(credentials=credentials, marketplace=Marketplaces.US)
        pricing = products_api.get_competitive_pricing_for_asins([asin])
        
        return {
            "status": "SUCCESS",
            "asin": asin,
            "pricing_response": str(pricing.payload)[:500] if pricing.payload else "No data",
        }
        
    except Exception as e:
        return {
            "status": "ERROR",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

