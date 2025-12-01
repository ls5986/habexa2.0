import stripe
from typing import Optional, Dict, Any
from datetime import datetime
from app.services.supabase_client import supabase
from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

# Price ID mapping
PRICE_IDS = {
    "starter_monthly": settings.STRIPE_PRICE_STARTER_MONTHLY,
    "starter_yearly": settings.STRIPE_PRICE_STARTER_YEARLY,
    "pro_monthly": settings.STRIPE_PRICE_PRO_MONTHLY,
    "pro_yearly": settings.STRIPE_PRICE_PRO_YEARLY,
    "agency_monthly": settings.STRIPE_PRICE_AGENCY_MONTHLY,
    "agency_yearly": settings.STRIPE_PRICE_AGENCY_YEARLY,
}

PRICE_TO_TIER = {}
if settings.STRIPE_PRICE_STARTER_MONTHLY:
    PRICE_TO_TIER[settings.STRIPE_PRICE_STARTER_MONTHLY] = "starter"
if settings.STRIPE_PRICE_STARTER_YEARLY:
    PRICE_TO_TIER[settings.STRIPE_PRICE_STARTER_YEARLY] = "starter"
if settings.STRIPE_PRICE_PRO_MONTHLY:
    PRICE_TO_TIER[settings.STRIPE_PRICE_PRO_MONTHLY] = "pro"
if settings.STRIPE_PRICE_PRO_YEARLY:
    PRICE_TO_TIER[settings.STRIPE_PRICE_PRO_YEARLY] = "pro"
if settings.STRIPE_PRICE_AGENCY_MONTHLY:
    PRICE_TO_TIER[settings.STRIPE_PRICE_AGENCY_MONTHLY] = "agency"
if settings.STRIPE_PRICE_AGENCY_YEARLY:
    PRICE_TO_TIER[settings.STRIPE_PRICE_AGENCY_YEARLY] = "agency"

TIER_LIMITS = {
    "free": {
        "telegram_channels": 1,
        "analyses_per_month": 10,
        "suppliers": 3,
        "alerts": False,
        "bulk_analyze": False,
        "api_access": False,
        "team_seats": 1,
    },
    "starter": {
        "telegram_channels": 3,
        "analyses_per_month": 100,
        "suppliers": 10,
        "alerts": True,
        "bulk_analyze": False,
        "api_access": False,
        "team_seats": 1,
    },
    "pro": {
        "telegram_channels": 10,
        "analyses_per_month": 500,
        "suppliers": 50,
        "alerts": True,
        "bulk_analyze": True,
        "api_access": False,
        "team_seats": 3,
    },
    "agency": {
        "telegram_channels": -1,
        "analyses_per_month": -1,
        "suppliers": -1,
        "alerts": True,
        "bulk_analyze": True,
        "api_access": True,
        "team_seats": 10,
    }
}


class StripeService:
    """Handle all Stripe operations."""
    
    @staticmethod
    async def get_or_create_customer(user_id: str, email: str, name: str = None) -> str:
        """Get existing Stripe customer or create new one."""
        
        # Check if customer exists
        result = supabase.table("subscriptions")\
            .select("stripe_customer_id")\
            .eq("user_id", user_id)\
            .execute()
        
        if result.data and len(result.data) > 0 and result.data[0].get("stripe_customer_id"):
            return result.data[0]["stripe_customer_id"]
        
        # Create new customer
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={"user_id": user_id}
        )
        
        # Store in database
        supabase.table("subscriptions").upsert({
            "user_id": user_id,
            "stripe_customer_id": customer.id,
            "tier": "free",
            "status": "active"
        }, on_conflict="user_id").execute()
        
        return customer.id
    
    @staticmethod
    async def create_checkout_session(
        user_id: str,
        email: str,
        price_key: str,
        success_url: str = None,
        cancel_url: str = None
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout session for subscription."""
        
        price_id = PRICE_IDS.get(price_key)
        if not price_id:
            raise ValueError(f"Invalid price key: {price_key}")
        
        # Get or create customer
        customer_id = await StripeService.get_or_create_customer(user_id, email)
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=success_url or (settings.STRIPE_SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}"),
            cancel_url=cancel_url or settings.STRIPE_CANCEL_URL,
            allow_promotion_codes=True,
            billing_address_collection="auto",
            subscription_data={
                "trial_period_days": 14,
                "metadata": {"user_id": user_id}
            },
            metadata={"user_id": user_id}
        )
        
        return {
            "session_id": session.id,
            "url": session.url
        }
    
    @staticmethod
    async def create_portal_session(user_id: str) -> str:
        """Create a Stripe Customer Portal session."""
        
        result = supabase.table("subscriptions")\
            .select("stripe_customer_id")\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data or len(result.data) == 0 or not result.data[0].get("stripe_customer_id"):
            raise ValueError("No Stripe customer found")
        
        session = stripe.billing_portal.Session.create(
            customer=result.data[0]["stripe_customer_id"],
            return_url=settings.FRONTEND_URL + "/settings?tab=billing"
        )
        
        return session.url
    
    @staticmethod
    async def get_subscription(user_id: str) -> Dict[str, Any]:
        """Get user's subscription details."""
        
        result = supabase.table("subscriptions")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data or len(result.data) == 0:
            return {
                "tier": "free",
                "status": "active",
                "limits": TIER_LIMITS["free"]
            }
        
        sub = result.data[0]
        tier = sub.get("tier", "free")
        
        return {
            "tier": tier,
            "status": sub.get("status", "active"),
            "billing_interval": sub.get("billing_interval"),
            "current_period_end": sub.get("current_period_end"),
            "cancel_at_period_end": sub.get("cancel_at_period_end", False),
            "trial_end": sub.get("trial_end"),
            "analyses_used": sub.get("analyses_used_this_period", 0),
            "limits": TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        }
    
    @staticmethod
    async def cancel_subscription(user_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        """Cancel a subscription."""
        
        result = supabase.table("subscriptions")\
            .select("stripe_subscription_id")\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data or len(result.data) == 0 or not result.data[0].get("stripe_subscription_id"):
            raise ValueError("No active subscription found")
        
        if at_period_end:
            subscription = stripe.Subscription.modify(
                result.data[0]["stripe_subscription_id"],
                cancel_at_period_end=True
            )
        else:
            subscription = stripe.Subscription.delete(
                result.data[0]["stripe_subscription_id"]
            )
        
        return {"status": "canceled", "cancel_at_period_end": at_period_end}
    
    @staticmethod
    async def reactivate_subscription(user_id: str) -> Dict[str, Any]:
        """Reactivate a subscription that was set to cancel."""
        
        result = supabase.table("subscriptions")\
            .select("stripe_subscription_id")\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data or len(result.data) == 0 or not result.data[0].get("stripe_subscription_id"):
            raise ValueError("No subscription found")
        
        subscription = stripe.Subscription.modify(
            result.data[0]["stripe_subscription_id"],
            cancel_at_period_end=False
        )
        
        supabase.table("subscriptions")\
            .update({"cancel_at_period_end": False})\
            .eq("user_id", user_id)\
            .execute()
        
        return {"status": "reactivated"}
    
    @staticmethod
    async def change_plan(user_id: str, new_price_key: str) -> Dict[str, Any]:
        """Change subscription plan (upgrade/downgrade)."""
        
        new_price_id = PRICE_IDS.get(new_price_key)
        if not new_price_id:
            raise ValueError(f"Invalid price key: {new_price_key}")
        
        result = supabase.table("subscriptions")\
            .select("stripe_subscription_id")\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data or len(result.data) == 0 or not result.data[0].get("stripe_subscription_id"):
            raise ValueError("No active subscription found")
        
        subscription = stripe.Subscription.retrieve(
            result.data[0]["stripe_subscription_id"]
        )
        
        updated = stripe.Subscription.modify(
            subscription.id,
            items=[{
                "id": subscription["items"]["data"][0].id,
                "price": new_price_id,
            }],
            proration_behavior="create_prorations"
        )
        
        return {"status": "updated", "new_tier": PRICE_TO_TIER.get(new_price_id)}
    
    @staticmethod
    async def get_invoices(user_id: str, limit: int = 10) -> list:
        """Get user's invoice history."""
        
        result = supabase.table("invoices")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return result.data or []
    
    @staticmethod
    async def check_feature_access(user_id: str, feature: str) -> bool:
        """Check if user has access to a feature based on their tier."""
        
        sub = await StripeService.get_subscription(user_id)
        limits = sub.get("limits", TIER_LIMITS["free"])
        
        if feature in ["alerts", "bulk_analyze", "api_access"]:
            return limits.get(feature, False)
        
        limit = limits.get(feature, 0)
        if limit == -1:
            return True
        
        if feature == "analyses_per_month":
            used = sub.get("analyses_used", 0)
            return used < limit
        
        return True
    
    @staticmethod
    async def increment_usage(user_id: str, feature: str, amount: int = 1):
        """Increment usage counter for a feature."""
        
        if feature == "analyses_per_month":
            try:
                supabase.rpc("increment_analyses", {
                    "p_user_id": user_id,
                    "p_amount": amount
                }).execute()
            except Exception as e:
                # Fallback if RPC doesn't work
                result = supabase.table("subscriptions")\
                    .select("analyses_used_this_period")\
                    .eq("user_id", user_id)\
                    .execute()
                
                current = result.data[0].get("analyses_used_this_period", 0) if result.data else 0
                supabase.table("subscriptions")\
                    .update({"analyses_used_this_period": current + amount})\
                    .eq("user_id", user_id)\
                    .execute()
        
        supabase.table("usage_records").insert({
            "user_id": user_id,
            "feature": feature,
            "quantity": amount
        }).execute()


class StripeWebhookHandler:
    """Handle Stripe webhook events."""
    
    @staticmethod
    async def handle_checkout_completed(session: Dict[str, Any]):
        """Handle successful checkout."""
        
        user_id = session.get("metadata", {}).get("user_id")
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        
        if not user_id or not subscription_id:
            return
        
        subscription = stripe.Subscription.retrieve(subscription_id)
        price_id = subscription["items"]["data"][0]["price"]["id"]
        tier = PRICE_TO_TIER.get(price_id, "starter")
        interval = subscription["items"]["data"][0]["price"]["recurring"]["interval"]
        
        supabase.table("subscriptions").upsert({
            "user_id": user_id,
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "stripe_price_id": price_id,
            "tier": tier,
            "billing_interval": interval,
            "status": subscription["status"],
            "current_period_start": datetime.fromtimestamp(subscription["current_period_start"]).isoformat(),
            "current_period_end": datetime.fromtimestamp(subscription["current_period_end"]).isoformat(),
            "trial_start": datetime.fromtimestamp(subscription["trial_start"]).isoformat() if subscription.get("trial_start") else None,
            "trial_end": datetime.fromtimestamp(subscription["trial_end"]).isoformat() if subscription.get("trial_end") else None,
        }, on_conflict="user_id").execute()
    
    @staticmethod
    async def handle_subscription_updated(subscription: Dict[str, Any]):
        """Handle subscription updates."""
        
        subscription_id = subscription["id"]
        price_id = subscription["items"]["data"][0]["price"]["id"]
        tier = PRICE_TO_TIER.get(price_id, "starter")
        interval = subscription["items"]["data"][0]["price"]["recurring"]["interval"]
        
        supabase.table("subscriptions")\
            .update({
                "stripe_price_id": price_id,
                "tier": tier,
                "billing_interval": interval,
                "status": subscription["status"],
                "current_period_start": datetime.fromtimestamp(subscription["current_period_start"]).isoformat(),
                "current_period_end": datetime.fromtimestamp(subscription["current_period_end"]).isoformat(),
                "cancel_at_period_end": subscription.get("cancel_at_period_end", False),
                "canceled_at": datetime.fromtimestamp(subscription["canceled_at"]).isoformat() if subscription.get("canceled_at") else None,
            })\
            .eq("stripe_subscription_id", subscription_id)\
            .execute()
    
    @staticmethod
    async def handle_subscription_deleted(subscription: Dict[str, Any]):
        """Handle subscription cancellation."""
        
        subscription_id = subscription["id"]
        
        supabase.table("subscriptions")\
            .update({
                "tier": "free",
                "status": "canceled",
                "stripe_subscription_id": None,
                "stripe_price_id": None,
            })\
            .eq("stripe_subscription_id", subscription_id)\
            .execute()
    
    @staticmethod
    async def handle_invoice_paid(invoice: Dict[str, Any]):
        """Handle successful payment."""
        
        customer_id = invoice["customer"]
        
        result = supabase.table("subscriptions")\
            .select("user_id")\
            .eq("stripe_customer_id", customer_id)\
            .execute()
        
        if not result.data or len(result.data) == 0:
            return
        
        user_id = result.data[0]["user_id"]
        
        supabase.table("invoices").upsert({
            "user_id": user_id,
            "stripe_invoice_id": invoice["id"],
            "stripe_invoice_url": invoice.get("hosted_invoice_url"),
            "stripe_pdf_url": invoice.get("invoice_pdf"),
            "amount_due": invoice["amount_due"],
            "amount_paid": invoice["amount_paid"],
            "currency": invoice["currency"],
            "status": invoice["status"],
            "period_start": datetime.fromtimestamp(invoice["period_start"]).isoformat(),
            "period_end": datetime.fromtimestamp(invoice["period_end"]).isoformat(),
        }, on_conflict="stripe_invoice_id").execute()
        
        supabase.table("payments").insert({
            "user_id": user_id,
            "stripe_invoice_id": invoice["id"],
            "stripe_payment_intent_id": invoice.get("payment_intent"),
            "amount": invoice["amount_paid"],
            "currency": invoice["currency"],
            "status": "succeeded",
            "description": f"Payment for subscription",
            "receipt_url": invoice.get("hosted_invoice_url")
        }).execute()
        
        supabase.table("subscriptions")\
            .update({
                "analyses_used_this_period": 0,
                "last_usage_reset": datetime.utcnow().isoformat()
            })\
            .eq("user_id", user_id)\
            .execute()
    
    @staticmethod
    async def handle_invoice_payment_failed(invoice: Dict[str, Any]):
        """Handle failed payment."""
        
        customer_id = invoice["customer"]
        
        result = supabase.table("subscriptions")\
            .select("user_id")\
            .eq("stripe_customer_id", customer_id)\
            .execute()
        
        if not result.data or len(result.data) == 0:
            return
        
        supabase.table("subscriptions")\
            .update({"status": "past_due"})\
            .eq("stripe_customer_id", customer_id)\
            .execute()

