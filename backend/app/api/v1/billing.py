from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import stripe
from datetime import datetime

from app.api.deps import get_current_user
from app.services.stripe_service import StripeService, StripeWebhookHandler, TIER_LIMITS
from app.services.feature_gate import SUPER_ADMIN_EMAILS
from app.services.supabase_client import supabase
from app.core.config import settings

router = APIRouter()

stripe.api_key = settings.STRIPE_SECRET_KEY


class CheckoutRequest(BaseModel):
    price_key: str  # e.g., "starter_monthly", "pro_yearly"
    include_trial: bool = True  # Include 7-day trial if user hasn't had one


class ChangePlanRequest(BaseModel):
    new_price_key: str


class SetTierRequest(BaseModel):
    tier: str  # 'free', 'starter', 'pro', 'agency'


@router.get("/subscription")
async def get_subscription(current_user=Depends(get_current_user)):
    """Get current subscription details."""
    return await StripeService.get_subscription(current_user.id)


@router.post("/sync")
async def sync_subscription(
    session_id: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """Sync subscription from Stripe checkout session OR check for existing subscriptions.
    
    If session_id provided: syncs from that checkout session.
    If no session_id: checks Stripe for any existing active subscriptions and syncs them.
    """
    try:
        if session_id:
            # Sync from specific checkout session
            result = await StripeService.sync_subscription_from_session(
                session_id,
                current_user.id
            )
            if not result.get("success"):
                raise HTTPException(status_code=400, detail=result.get("error", "Failed to sync"))
        else:
            # Check for existing subscriptions in Stripe
            customer_id = await StripeService.get_or_create_customer(
                current_user.id,
                current_user.email
            )
            
            # List active subscriptions
            stripe_subs = stripe.Subscription.list(
                customer=customer_id,
                status="all",  # Check all statuses
                limit=10
            )
            
            if stripe_subs.data:
                # Sync the most recent active/trialing subscription
                active_subs = [s for s in stripe_subs.data if s.status in ["active", "trialing"]]
                if active_subs:
                    from app.services.stripe_service import StripeWebhookHandler
                    await StripeWebhookHandler.handle_subscription_updated(active_subs[0])
                elif stripe_subs.data:
                    # Sync the most recent one even if not active
                    from app.services.stripe_service import StripeWebhookHandler
                    await StripeWebhookHandler.handle_subscription_updated(stripe_subs.data[0])
        
        # Invalidate cache
        try:
            from app.services.redis_client import cache_service
            if cache_service:
                cache_service.invalidate_subscription_cache(current_user.id)
        except:
            pass
        
        # Return updated subscription
        return await StripeService.get_subscription(current_user.id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Sync subscription error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans")
async def get_available_plans():
    """Get available subscription plans."""
    return {
        "plans": [
            {
                "tier": "starter",
                "name": "Starter",
                "description": "Perfect for individual sellers getting started",
                "monthly_price": 29,
                "yearly_price": 290,
                "price_keys": {
                    "monthly": "starter_monthly",
                    "yearly": "starter_yearly"
                },
                "features": TIER_LIMITS["starter"]
            },
            {
                "tier": "pro",
                "name": "Pro",
                "description": "For serious sellers scaling their business",
                "monthly_price": 79,
                "yearly_price": 790,
                "price_keys": {
                    "monthly": "pro_monthly",
                    "yearly": "pro_yearly"
                },
                "features": TIER_LIMITS["pro"],
                "popular": True
            },
            {
                "tier": "agency",
                "name": "Agency",
                "description": "For teams and agencies managing multiple accounts",
                "monthly_price": 199,
                "yearly_price": 1990,
                "price_keys": {
                    "monthly": "agency_monthly",
                    "yearly": "agency_yearly"
                },
                "features": TIER_LIMITS["agency"]
            }
        ]
    }


@router.post("/checkout")
@router.post("/create-checkout-session")  # Alias for frontend compatibility
async def create_checkout_session(
    request: CheckoutRequest,
    current_user=Depends(get_current_user)
):
    """Create a Stripe Checkout session with optional 7-day trial.
    
    IMPORTANT: Checks for existing subscriptions first.
    If user already has an active subscription, returns existing subscription info.
    
    Trial is only included if:
    - include_trial=True (default)
    - User hasn't had a free trial before (had_free_trial=False)
    """
    
    try:
        result = await StripeService.create_checkout_session(
            user_id=current_user.id,
            email=current_user.email,
            price_key=request.price_key,
            include_trial=request.include_trial
        )
        
        # If existing subscription found, return it with a message
        if result.get("existing"):
            return {
                "existing": True,
                "subscription": result.get("subscription"),
                "message": result.get("message", "You already have an active subscription."),
                "portal_url": await StripeService.create_portal_session(current_user.id)
            }
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create checkout: {str(e)}")


@router.post("/portal")
@router.post("/portal-session")  # Alias for frontend compatibility
async def create_portal_session(current_user=Depends(get_current_user)):
    """Create a Stripe Customer Portal session."""
    try:
        url = await StripeService.create_portal_session(current_user.id)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel")
async def cancel_subscription(
    at_period_end: bool = True,
    current_user=Depends(get_current_user)
):
    """Cancel subscription at period end (keeps access until billing period ends)."""
    try:
        result = await StripeService.cancel_subscription(
            current_user.id,
            at_period_end=at_period_end
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel-immediately")
async def cancel_subscription_immediately(
    current_user=Depends(get_current_user)
):
    """Cancel subscription immediately (for trials or special cases). Downgrades to free."""
    try:
        result = await StripeService.cancel_subscription(
            current_user.id,
            at_period_end=False  # Cancel immediately
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reactivate")
async def reactivate_subscription(current_user=Depends(get_current_user)):
    """Resume a subscription that was set to cancel at period end."""
    try:
        result = await StripeService.reactivate_subscription(current_user.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resubscribe")
async def resubscribe(
    request: CheckoutRequest,
    current_user=Depends(get_current_user)
):
    """Resubscribe after full cancellation (creates new subscription, no trial if already had one)."""
    # Check current status
    subscription = await StripeService.get_subscription(current_user.id)
    
    if subscription.get("status") in ["active", "trialing"]:
        raise HTTPException(
            status_code=400,
            detail="Already have active subscription. Use change-plan endpoint instead."
        )
    
    # Create new checkout (no trial if they already had one)
    try:
        result = await StripeService.create_checkout_session(
            user_id=current_user.id,
            email=current_user.email,
            price_key=request.price_key,
            include_trial=False  # No trial on resubscribe
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/change-plan")
async def change_plan(
    request: ChangePlanRequest,
    current_user=Depends(get_current_user)
):
    """Change subscription plan."""
    try:
        result = await StripeService.change_plan(
            current_user.id,
            request.new_price_key
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class SetTierRequest(BaseModel):
    tier: str  # 'free', 'starter', 'pro', 'agency'


@router.post("/set-tier")
async def set_tier(
    request: SetTierRequest,
    current_user=Depends(get_current_user)
):
    """
    Super user endpoint to directly set tier without payment.
    Only available for super admin users.
    """
    user_email = getattr(current_user, 'email', None)
    
    # Check if user is super admin
    if not user_email or user_email.lower() not in [email.lower() for email in SUPER_ADMIN_EMAILS]:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only available for super admin users"
        )
    
    # Validate tier
    valid_tiers = ['free', 'starter', 'pro', 'agency']
    if request.tier not in valid_tiers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier. Must be one of: {', '.join(valid_tiers)}"
        )
    
    try:
        # Get or create subscription record
        result = supabase.table("subscriptions")\
            .select("id")\
            .eq("user_id", str(current_user.id))\
            .maybe_single()\
            .execute()
        
        subscription_data = {
            "user_id": str(current_user.id),
            "tier": request.tier,
            "status": "active" if request.tier != "free" else "free",
            "billing_interval": None if request.tier == "free" else "month",
            "cancel_at_period_end": False,
            "trial_end": None,
        }
        
        if result.data:
            # Update existing subscription
            supabase.table("subscriptions")\
                .update(subscription_data)\
                .eq("id", result.data["id"])\
                .execute()
        else:
            # Create new subscription
            supabase.table("subscriptions").insert(subscription_data).execute()
        
        # Invalidate cache
        try:
            from app.services.redis_client import cache_service
            if cache_service:
                cache_service.invalidate_subscription_cache(current_user.id)
        except:
            pass
        
        # Return updated subscription
        subscription = await StripeService.get_subscription(current_user.id)
        
        return {
            "success": True,
            "message": f"Tier updated to {request.tier}",
            "subscription": subscription
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error setting tier: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to set tier: {str(e)}")


@router.get("/invoices")
async def get_invoices(
    limit: int = 10,
    current_user=Depends(get_current_user)
):
    """Get invoice history."""
    invoices = await StripeService.get_invoices(current_user.id, limit)
    return {"invoices": invoices}


@router.get("/usage")
async def get_usage(current_user=Depends(get_current_user)):
    """Get current usage stats."""
    subscription = await StripeService.get_subscription(current_user.id)
    
    return {
        "tier": subscription["tier"],
        "analyses": {
            "used": subscription.get("analyses_used", 0),
            "limit": subscription["limits"]["analyses_per_month"],
            "unlimited": subscription["limits"]["analyses_per_month"] == -1
        },
        "period_ends": subscription.get("current_period_end")
    }


@router.get("/user/limits")
async def get_user_limits(current_user=Depends(get_current_user)):
    """
    Returns user's effective limits and current usage.
    Frontend should call this instead of using hardcoded limits.
    This endpoint properly handles super admin bypass.
    """
    import time
    start_time = time.time()
    
    from app.services.permissions_service import PermissionsService
    from app.services.feature_gate import feature_gate
    
    # Get effective limits (includes super admin bypass)
    limits = PermissionsService.get_effective_limits(current_user)
    
    # OPTIMIZATION: Batch usage queries in parallel
    import asyncio
    from app.services.feature_gate import FeatureGate
    user_id = str(current_user.id)
    
    # Get all usage counts in parallel
    usage_tasks = [
        FeatureGate._get_usage(user_id, "analyses_per_month"),
        FeatureGate._get_usage(user_id, "telegram_channels"),
        FeatureGate._get_usage(user_id, "suppliers"),
        FeatureGate._get_usage(user_id, "team_seats"),
    ]
    
    usage_results = await asyncio.gather(*usage_tasks, return_exceptions=True)
    
    # Map results back to features
    features = ["analyses_per_month", "telegram_channels", "suppliers", "team_seats"]
    usage_values = {}
    for idx, feature in enumerate(features):
        result = usage_results[idx]
        if isinstance(result, Exception):
            usage_values[feature] = 0
        else:
            usage_values[feature] = result
    
    # Build usage data
    usage_data = {}
    for feature in ["analyses_per_month", "telegram_channels", "suppliers", "team_seats"]:
        used = usage_values.get(feature, 0)
        feature_limit = limits.get(feature, 0)
        
        usage_data[feature] = {
            "limit": feature_limit,
            "used": used,
            "remaining": -1 if limits["unlimited"] or feature_limit == -1 else max(0, feature_limit - used),
            "unlimited": limits["unlimited"] or feature_limit == -1
        }
    
    # Add boolean features
    for feature in ["alerts", "bulk_analyze", "api_access", "export_data", "priority_support"]:
        usage_data[feature] = {
            "allowed": limits.get(feature, False),
            "unlimited": limits["unlimited"]
        }
    
    elapsed = time.time() - start_time
    if elapsed > 1.0:
        logger = logging.getLogger(__name__)
        logger.warning(f"Slow /billing/user/limits request: {elapsed:.2f}s")
    
    return {
        "tier": limits["tier"],
        "tier_display": limits.get("tier_display", limits["tier"].title()),
        "is_super_admin": limits.get("is_super_admin", False),
        "unlimited": limits["unlimited"],
        "limits": usage_data
    }


@router.get("/limits")
async def get_all_limits(current_user=Depends(get_current_user)):
    """Get all feature limits and current usage."""
    from app.services.feature_gate import feature_gate
    return await feature_gate.get_all_usage(current_user)


@router.get("/limits/{feature}")
async def check_feature_limit(
    feature: str,
    current_user=Depends(get_current_user)
):
    """Check limit for a specific feature."""
    from app.services.feature_gate import feature_gate
    
    valid_features = [
        "analyses_per_month", "telegram_channels", "suppliers", 
        "team_seats", "alerts", "bulk_analyze", "api_access", "export_data"
    ]
    
    if feature not in valid_features:
        raise HTTPException(400, f"Invalid feature. Valid: {valid_features}")
    
    return await feature_gate.check_limit(current_user, feature)


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    event_type = event["type"]
    data = event["data"]["object"]
    
    handlers = {
        "checkout.session.completed": StripeWebhookHandler.handle_checkout_completed,
        "customer.subscription.created": StripeWebhookHandler.handle_subscription_updated,  # Same handler as updated
        "customer.subscription.updated": StripeWebhookHandler.handle_subscription_updated,
        "customer.subscription.deleted": StripeWebhookHandler.handle_subscription_deleted,
        "customer.subscription.trial_will_end": StripeWebhookHandler.handle_trial_will_end,
        "invoice.paid": StripeWebhookHandler.handle_invoice_paid,
        "invoice.payment_failed": StripeWebhookHandler.handle_invoice_payment_failed,
    }
    
    handler = handlers.get(event_type)
    if handler:
        await handler(data)
    
    return {"status": "success"}


@router.post("/initialize-subscription")
async def initialize_subscription(current_user=Depends(get_current_user)):
    """
    Initialize subscription record for new users.
    Called after signup to create free tier subscription and send welcome email.
    """
    try:
        user_id = str(current_user.id)
        
        # Ensure profile exists first (required for foreign key constraint)
        profile_check = supabase.table("profiles").select("id").eq("id", user_id).maybe_single().execute()
        if not profile_check or not profile_check.data:
            # Create profile if it doesn't exist
            supabase.table("profiles").insert({
                "id": user_id,
                "email": current_user.email,
                "full_name": getattr(current_user, 'user_metadata', {}).get('full_name'),
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }).execute()
        
        # Check if subscription already exists
        result = supabase.table("subscriptions")\
            .select("id")\
            .eq("user_id", user_id)\
            .maybe_single()\
            .execute()
        
        if result and result.data:
            # Subscription already exists, return it
            return {
                "status": "exists",
                "message": "Subscription already initialized"
            }
        
        # Create free tier subscription
        supabase.table("subscriptions").insert({
            "user_id": user_id,
            "tier": "free",
            "status": "active",
            "analyses_used_this_period": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).execute()
        
        # Send welcome email
        try:
            from app.services.email_service import EmailService
            if hasattr(EmailService, 'send_welcome_email'):
                await EmailService.send_welcome_email(user_id)
        except Exception as email_error:
            import logging
            logging.getLogger(__name__).warning(f"Failed to send welcome email: {email_error}")
        
        return {
            "status": "initialized",
            "tier": "free",
            "message": "Subscription initialized successfully"
        }
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to initialize subscription: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

