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

# Import from centralized config - single source of truth
from app.config.tiers import TIER_LIMITS


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
        cancel_url: str = None,
        include_trial: bool = True
    ) -> Dict[str, Any]:
        """Create a Stripe Checkout session for subscription.
        
        IMPORTANT: Checks for existing active subscriptions first.
        If user already has an active subscription, returns existing subscription info.
        
        Args:
            user_id: User ID
            email: User email
            price_key: Price key (e.g., "starter_monthly")
            success_url: Success redirect URL
            cancel_url: Cancel redirect URL
            include_trial: Whether to include 7-day trial (only if user hasn't had one)
        """
        
        price_id = PRICE_IDS.get(price_key)
        if not price_id:
            raise ValueError(f"Invalid price key: {price_key}")
        
        # Get or create customer
        customer_id = await StripeService.get_or_create_customer(user_id, email)
        
        # Check if user already had a free trial
        had_trial = False
        try:
            result = supabase.table("subscriptions")\
                .select("had_free_trial")\
                .eq("user_id", user_id)\
                .maybe_single()\
                .execute()
            if result.data:
                had_trial = result.data.get("had_free_trial", False)
        except Exception:
            pass  # Default to False if check fails
        
        # CHECK FOR EXISTING ACTIVE SUBSCRIPTION
        # First check database
        db_sub = supabase.table("subscriptions")\
            .select("stripe_subscription_id, status, tier")\
            .eq("user_id", user_id)\
            .execute()
        
        if db_sub.data and len(db_sub.data) > 0:
            existing_sub_id = db_sub.data[0].get("stripe_subscription_id")
            existing_status = db_sub.data[0].get("status", "")
            
            # If has active subscription in DB, verify with Stripe
            if existing_sub_id and existing_status in ["active", "trialing"]:
                try:
                    stripe_sub = stripe.Subscription.retrieve(existing_sub_id)
                    if stripe_sub.status in ["active", "trialing"]:
                        # User already has active subscription
                        return {
                            "existing": True,
                            "subscription": await StripeService.get_subscription(user_id),
                            "message": "You already have an active subscription. Use the customer portal to change plans."
                        }
                except stripe.error.StripeError:
                    # Subscription doesn't exist in Stripe, continue to create new one
                    pass
        
        # Also check Stripe directly for any active subscriptions for this customer
        try:
            stripe_subs = stripe.Subscription.list(
                customer=customer_id,
                status="active",
                limit=1
            )
            
            if stripe_subs.data and len(stripe_subs.data) > 0:
                # User has active subscription in Stripe but not in our DB
                # Sync it first
                active_sub = stripe_subs.data[0]
                await StripeWebhookHandler.handle_subscription_updated(active_sub)
                
                return {
                    "existing": True,
                    "subscription": await StripeService.get_subscription(user_id),
                    "message": "Found existing subscription. It has been synced."
                }
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Error checking Stripe subscriptions: {e}")
        
        # No existing subscription, create new checkout session
        session_params = {
            "customer": customer_id,
            "payment_method_types": ["card"],
            "line_items": [{
                "price": price_id,
                "quantity": 1,
            }],
            "mode": "subscription",
            "success_url": success_url or (settings.STRIPE_SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}"),
            "cancel_url": cancel_url or settings.STRIPE_CANCEL_URL,
            "allow_promotion_codes": True,
            "billing_address_collection": "auto",
            "metadata": {"user_id": user_id}
        }
        
        # Add 7-day trial if user hasn't had one and include_trial is True
        if include_trial and not had_trial:
            session_params["subscription_data"] = {
                "trial_period_days": 7,  # Changed from 14 to 7 days
                "metadata": {"user_id": user_id, "plan": price_key}
            }
        else:
            # Still include metadata for subscription
            session_params["subscription_data"] = {
                "metadata": {"user_id": user_id, "plan": price_key}
            }
        
        session = stripe.checkout.Session.create(**session_params)
        
        return {
            "session_id": session.id,
            "url": session.url,
            "existing": False
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
    async def sync_subscription_from_session(session_id: str, user_id: str) -> Dict[str, Any]:
        """Sync subscription from Stripe checkout session (fallback if webhook hasn't fired)."""
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            subscription_id = session.get("subscription")
            
            if not subscription_id:
                return {"success": False, "error": "No subscription in session"}
            
            # Use the same logic as webhook handler
            await StripeWebhookHandler.handle_checkout_completed({
                "metadata": {"user_id": user_id},
                "customer": session.get("customer"),
                "subscription": subscription_id
            })
            
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_subscription(user_id: str) -> Dict[str, Any]:
        """Get user's subscription details.
        
        Optionally syncs with Stripe for fresh data.
        """
        
        result = supabase.table("subscriptions")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data or len(result.data) == 0:
            return {
                "tier": "free",
                "status": "none",
                "limits": TIER_LIMITS["free"],
                "had_free_trial": False,
                "cancel_at_period_end": False
            }
        
        sub = result.data[0]
        tier = sub.get("tier", "free")
        
        # Optionally sync with Stripe for fresh status
        subscription_id = sub.get("stripe_subscription_id")
        if subscription_id:
            try:
                stripe_sub = stripe.Subscription.retrieve(subscription_id)
                # Update local cache if status changed
                if stripe_sub.status != sub.get("status"):
                    await StripeWebhookHandler.handle_subscription_updated(stripe_sub)
                    # Re-fetch after update
                    result = supabase.table("subscriptions")\
                        .select("*")\
                        .eq("user_id", user_id)\
                        .execute()
                    if result.data:
                        sub = result.data[0]
            except Exception:
                pass  # Use cached data if Stripe fails
        
        return {
            "tier": tier,
            "status": sub.get("status", "active"),
            "billing_interval": sub.get("billing_interval"),
            "current_period_start": sub.get("current_period_start"),
            "current_period_end": sub.get("current_period_end"),
            "cancel_at_period_end": sub.get("cancel_at_period_end", False),
            "trial_start": sub.get("trial_start"),
            "trial_end": sub.get("trial_end"),
            "had_free_trial": sub.get("had_free_trial", False),
            "analyses_used": sub.get("analyses_used_this_period", 0),
            "limits": TIER_LIMITS.get(tier, TIER_LIMITS["free"])
        }
    
    @staticmethod
    async def cancel_subscription(user_id: str, at_period_end: bool = True) -> Dict[str, Any]:
        """Cancel a subscription.
        
        Args:
            user_id: User ID
            at_period_end: If True, cancel at period end (keeps access). If False, cancel immediately.
        """
        
        result = supabase.table("subscriptions")\
            .select("stripe_subscription_id, status")\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data or len(result.data) == 0 or not result.data[0].get("stripe_subscription_id"):
            raise ValueError("No active subscription found")
        
        subscription_id = result.data[0]["stripe_subscription_id"]
        current_status = result.data[0].get("status", "")
        
        if at_period_end:
            # Cancel at period end (user keeps access until then)
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            
            # Update database
            supabase.table("subscriptions")\
                .update({
                    "cancel_at_period_end": True,
                    "status": "active" if current_status == "trialing" else current_status
                })\
                .eq("user_id", user_id)\
                .execute()
            
            return {
                "status": "scheduled_cancellation",
                "cancel_at_period_end": True,
                "access_until": datetime.fromtimestamp(subscription.current_period_end).isoformat(),
                "message": "Subscription will cancel at end of billing period"
            }
        else:
            # Cancel immediately (for trials or special cases)
            subscription = stripe.Subscription.delete(subscription_id)
            
            # Downgrade to free immediately
            supabase.table("subscriptions")\
                .update({
                    "tier": "free",
                    "status": "canceled",
                    "stripe_subscription_id": None,
                    "stripe_price_id": None,
                    "cancel_at_period_end": False,
                    "canceled_at": datetime.utcnow().isoformat()
                })\
                .eq("user_id", user_id)\
                .execute()
            
            return {
                "status": "canceled",
                "cancel_at_period_end": False,
                "new_tier": "free",
                "message": "Subscription cancelled immediately"
            }
    
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
        
        # Check if this subscription has a trial
        has_trial = subscription.get("trial_start") is not None and subscription.get("trial_end") is not None
        had_trial_before = False
        
        # Check if user already had a trial
        try:
            existing = supabase.table("subscriptions")\
                .select("had_free_trial")\
                .eq("user_id", user_id)\
                .maybe_single()\
                .execute()
            if existing.data:
                had_trial_before = existing.data.get("had_free_trial", False)
        except Exception:
            pass
        
        # Set had_free_trial if this subscription has a trial
        had_free_trial = had_trial_before or has_trial
        
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
            "had_free_trial": had_free_trial,  # Track that user had a trial
        }, on_conflict="user_id").execute()
    
    @staticmethod
    async def handle_subscription_updated(subscription: Dict[str, Any]):
        """Handle subscription updates (plan changes, trial ending, cancellation scheduled, etc.)."""
        import logging
        logger = logging.getLogger(__name__)
        
        subscription_id = subscription["id"]
        price_id = subscription["items"]["data"][0]["price"]["id"]
        tier = PRICE_TO_TIER.get(price_id, "starter")
        interval = subscription["items"]["data"][0]["price"]["recurring"]["interval"]
        
        # Get user_id before updating (for logging)
        user_id = None
        try:
            existing = supabase.table("subscriptions")\
                .select("user_id, status, had_free_trial, tier")\
                .eq("stripe_subscription_id", subscription_id)\
                .maybe_single()\
                .execute()
            if existing.data:
                user_id = existing.data.get("user_id")
                was_trialing = existing.data.get("status") == "trialing"
                old_tier = existing.data.get("tier")
        except Exception:
            was_trialing = False
            old_tier = None
        
        # If transitioning from trialing to active, ensure had_free_trial is set
        had_free_trial = False
        if subscription.get("trial_start") or subscription.get("trial_end") or was_trialing:
            had_free_trial = True
        
        update_data = {
            "stripe_price_id": price_id,
            "tier": tier,
            "billing_interval": interval,
            "status": subscription["status"],
            "current_period_start": datetime.fromtimestamp(subscription["current_period_start"]).isoformat(),
            "current_period_end": datetime.fromtimestamp(subscription["current_period_end"]).isoformat(),
            "cancel_at_period_end": subscription.get("cancel_at_period_end", False),
            "canceled_at": datetime.fromtimestamp(subscription["canceled_at"]).isoformat() if subscription.get("canceled_at") else None,
        }
        
        # Update trial fields if present
        if subscription.get("trial_start"):
            update_data["trial_start"] = datetime.fromtimestamp(subscription["trial_start"]).isoformat()
        if subscription.get("trial_end"):
            update_data["trial_end"] = datetime.fromtimestamp(subscription["trial_end"]).isoformat()
        
        # Set had_free_trial if trial exists or was trialing
        if had_free_trial:
            update_data["had_free_trial"] = True
        
        supabase.table("subscriptions")\
            .update(update_data)\
            .eq("stripe_subscription_id", subscription_id)\
            .execute()
        
        # ✅ Log tier change for debugging (frontend will refresh on next /auth/me call)
        if old_tier and old_tier != tier and user_id:
            logger.info(f"✅ Tier changed for user {user_id}: {old_tier} → {tier} (webhook)")
    
    @staticmethod
    async def handle_subscription_deleted(subscription: Dict[str, Any]):
        """Handle subscription cancellation — downgrade to free."""
        
        subscription_id = subscription["id"]
        
        # Get user_id before updating
        result = supabase.table("subscriptions")\
            .select("user_id")\
            .eq("stripe_subscription_id", subscription_id)\
            .maybe_single()\
            .execute()
        
        user_id = result.data.get("user_id") if result.data else None
        
        supabase.table("subscriptions")\
            .update({
                "tier": "free",
                "status": "canceled",
                "stripe_subscription_id": None,
                "stripe_price_id": None,
                "cancel_at_period_end": False,
                "canceled_at": datetime.utcnow().isoformat(),
            })\
            .eq("stripe_subscription_id", subscription_id)\
            .execute()
        
        # Send cancellation email
        if user_id:
            try:
                from app.services.email_service import EmailService
                await EmailService.send_subscription_cancelled_email(user_id)
            except Exception as email_error:
                logger.warning(f"Failed to send cancellation email: {email_error}")
    
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
        
        user_id = result.data[0]["user_id"]
        
        supabase.table("subscriptions")\
            .update({"status": "past_due"})\
            .eq("stripe_customer_id", customer_id)\
            .execute()
        
        # Send payment failed email
        try:
            from app.services.email_service import EmailService
            await EmailService.send_payment_failed_email(user_id)
        except Exception as email_error:
            logger.warning(f"Failed to send payment failed email: {email_error}")
    
    @staticmethod
    async def handle_trial_will_end(subscription: Dict[str, Any]):
        """Handle trial ending soon (3 days before trial ends).
        
        This is a good time to send reminder emails to users.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        subscription_id = subscription["id"]
        customer_id = subscription.get("customer")
        trial_end = subscription.get("trial_end")
        
        if not trial_end:
            return
        
        # Get user from subscription
        try:
            result = supabase.table("subscriptions")\
                .select("user_id")\
                .eq("stripe_subscription_id", subscription_id)\
                .maybe_single()\
                .execute()
            
            if result.data:
                user_id = result.data["user_id"]
                logger.info(f"Trial ending soon for user {user_id}. Trial ends: {datetime.fromtimestamp(trial_end).isoformat()}")
                
                # Send reminder email
                try:
                    from app.services.email_service import EmailService
                    trial_end_dt = datetime.fromtimestamp(trial_end)
                    await EmailService.send_trial_ending_email(user_id, trial_end_dt)
                except Exception as email_error:
                    logger.warning(f"Failed to send trial ending email: {email_error}")
        except Exception as e:
            logger.warning(f"Error handling trial_will_end webhook: {e}")

