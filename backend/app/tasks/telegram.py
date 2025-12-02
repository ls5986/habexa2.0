"""
Celery tasks for Telegram monitoring and message processing.
"""
import re
import asyncio
from typing import List, Optional
from app.core.celery_app import celery_app
from app.services.supabase_client import supabase
from app.tasks.base import JobManager, run_async
from app.services.telegram_service import telegram_service
import logging

logger = logging.getLogger(__name__)

# Patterns to extract deal info from Telegram messages
ASIN_PATTERN = re.compile(r'\b[A-Z0-9]{10}\b')
PRICE_PATTERN = re.compile(r'\$[\d,]+\.?\d*|\d+\.?\d*\s*(?:USD|usd)')
MOQ_PATTERN = re.compile(r'(?:MOQ|moq|qty|QTY|quantity)[:\s]*(\d+)', re.IGNORECASE)


def extract_deal_from_message(message_text: str) -> dict:
    """Extract ASIN, price, MOQ from message text."""
    result = {
        "asin": None,
        "buy_cost": None,
        "moq": 1
    }
    
    # Extract ASIN
    asin_match = ASIN_PATTERN.search(message_text.upper())
    if asin_match:
        result["asin"] = asin_match.group()
    
    # Extract price
    price_match = PRICE_PATTERN.search(message_text)
    if price_match:
        price_str = price_match.group().replace("$", "").replace(",", "").replace("USD", "").replace("usd", "").strip()
        try:
            result["buy_cost"] = float(price_str)
        except:
            pass
    
    # Extract MOQ
    moq_match = MOQ_PATTERN.search(message_text)
    if moq_match:
        try:
            result["moq"] = int(moq_match.group(1))
        except:
            pass
    
    return result


@celery_app.task
def check_all_channels():
    """
    Periodic task: Check all monitored Telegram channels for new messages.
    Runs every 60 seconds via Celery Beat.
    """
    # Get all active channel monitors
    # Note: This assumes a telegram_monitors table exists
    # If not, you may need to query telegram_channels instead
    try:
        monitors = supabase.table("telegram_channels")\
            .select("user_id, channel_id, channel_name")\
            .eq("is_active", True)\
            .execute()
        
        for monitor in (monitors.data or []):
            user_id = monitor.get("user_id")
            channel_id = monitor.get("channel_id")
            channel_name = monitor.get("channel_name", "Unknown")
            
            if user_id and channel_id:
                # Queue individual channel check
                check_channel_messages.delay(user_id, str(channel_id), channel_name)
    except Exception as e:
        logger.error(f"Error in check_all_channels: {e}", exc_info=True)


@celery_app.task(bind=True, max_retries=3)
def check_channel_messages(self, user_id: str, channel_id: str, channel_name: str):
    """Check a single Telegram channel for new messages."""
    try:
        from app.services.telegram_service import telegram_service
        
        # Get last processed message ID for this channel
        monitor = supabase.table("telegram_channels")\
            .select("last_message_id")\
            .eq("user_id", user_id)\
            .eq("channel_id", channel_id)\
            .limit(1)\
            .execute()
        
        last_message_id = monitor.data[0].get("last_message_id", 0) if monitor.data else 0
        
        # Use telegram_service to check for new messages
        # The service's backfill_channel method handles message fetching
        # For now, we'll log a warning and return - full implementation needs message fetching endpoint
        logger.warning(f"check_channel_messages: Telegram message fetching not fully implemented for channel {channel_id}")
        logger.info(f"To fully implement: Add get_new_messages() method to telegram_service that fetches messages since last_message_id")
        
        # TODO: Implement message fetching
        # messages = await telegram_service.get_new_messages(user_id, int(channel_id), last_message_id)
        messages = []
        
        if not messages:
            return {"new_messages": 0, "message": "Message fetching not yet implemented"}
        
        # Process messages
        product_cache = {}
        new_deals = 0
        max_message_id = last_message_id
        
        for msg in messages:
            message_id = msg.get("id", 0)
            message_text = msg.get("text", "")
            
            max_message_id = max(max_message_id, message_id)
            
            # Extract deal info
            deal_info = extract_deal_from_message(message_text)
            
            if not deal_info["asin"]:
                continue
            
            asin = deal_info["asin"]
            
            # Get or create product
            if asin not in product_cache:
                existing = supabase.table("products")\
                    .select("id")\
                    .eq("user_id", user_id)\
                    .eq("asin", asin)\
                    .limit(1)\
                    .execute()
                
                if existing.data:
                    product_cache[asin] = existing.data[0]["id"]
                else:
                    new_prod = supabase.table("products").insert({
                        "user_id": user_id,
                        "asin": asin,
                        "status": "pending"
                    }).execute()
                    if new_prod.data:
                        product_cache[asin] = new_prod.data[0]["id"]
            
            product_id = product_cache.get(asin)
            if not product_id:
                continue
            
            # Create deal (upsert - update if exists for same product + no supplier)
            supabase.table("product_sources").upsert({
                "product_id": product_id,
                "supplier_id": None,  # Telegram deals have no supplier
                "buy_cost": deal_info["buy_cost"],
                "moq": deal_info["moq"],
                "source": "telegram",
                "source_detail": channel_name,
                "stage": "new",
                "is_active": True
            }, on_conflict="product_id,supplier_id").execute()
            
            new_deals += 1
        
        # Update last processed message ID
        if max_message_id > last_message_id:
            supabase.table("telegram_channels").update({
                "last_message_id": max_message_id,
                "last_checked_at": "now()"
            }).eq("user_id", user_id).eq("channel_id", channel_id).execute()
        
        return {"new_messages": len(messages), "new_deals": new_deals}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True)
def sync_telegram_channel(self, job_id: str, user_id: str, channel_id: str, channel_name: str, message_limit: int = 500):
    """
    Full sync of a Telegram channel - fetch historical messages.
    Used when first adding a channel.
    """
    job = JobManager(job_id)
    
    try:
        job.start()
        
        # Use telegram_service's backfill_channel method which handles message fetching
        # Run it async via run_async helper
        result = run_async(
            telegram_service.backfill_channel(
                user_id=user_id,
                channel_id=int(channel_id),
                days=14  # Default to 14 days of history
            )
        )
        
        total = result.get("checked", 0)
        messages_saved = result.get("messages", 0)
        deals_extracted = result.get("deals", 0)
        
        job.update_progress(total, total)
        
        # The backfill_channel method already handles all message processing
        # and deal creation, so we just need to report the results
        job.complete({
            "messages_processed": messages_saved,
            "messages_checked": total,
            "deals_found": deals_extracted,
            "channel": result.get("channel", channel_name)
        }, deals_extracted, 0, [])
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        job.fail(str(e))

