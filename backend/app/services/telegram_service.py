"""
Telegram monitoring service using Telethon.

Handles user authentication, channel monitoring, and message processing.
"""
import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    FloodWaitError,
    AuthKeyUnregisteredError
)

from app.services.supabase_client import supabase
from app.core.encryption import encrypt_token, decrypt_token
from app.services.product_extractor import product_extractor
from app.core.config import settings

logger = logging.getLogger(__name__)

# Store active clients per user
_active_clients: Dict[str, TelegramClient] = {}
_monitoring_tasks: Dict[str, asyncio.Task] = {}
_pending_codes: Dict[str, Dict] = {}


class TelegramServiceError(Exception):
    """Custom exception for Telegram service errors."""
    pass


class TelegramService:
    """
    Telegram monitoring service.
    Each user has their own Telegram session for monitoring their channels.
    """
    
    def __init__(self):
        self.api_id = int(settings.TELEGRAM_API_ID or 0)
        self.api_hash = settings.TELEGRAM_API_HASH or ""
        
        if not self.api_id or not self.api_hash:
            logger.warning("Telegram API credentials not configured")
    
    # ==========================================
    # AUTHENTICATION
    # ==========================================
    
    async def start_auth(self, user_id: str, phone_number: str) -> Dict[str, Any]:
        """Start Telegram authentication. user_id must be a string."""
        user_id = str(user_id)  # Ensure it's a string
        
        # Ensure profile exists (required for foreign key constraint)
        try:
            profile_check = supabase.table("profiles").select("id").eq("id", user_id).execute()
            if not profile_check.data or len(profile_check.data) == 0:
                # Try to get user email from current_user if available
                # Otherwise create with placeholder
                try:
                    # Create profile - email will be updated later if needed
                    supabase.table("profiles").insert({
                        "id": user_id,
                        "email": f"user_{user_id}@habexa.local",  # Placeholder, will be updated
                        "full_name": None,
                    }).execute()
                    logger.info(f"Created missing profile for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to create profile for user {user_id}: {e}")
                    raise TelegramServiceError(f"Profile not found. Please ensure your account is properly set up.")
        except Exception as e:
            if "violates foreign key constraint" in str(e) or "not present in table" in str(e):
                # Profile definitely doesn't exist, try to create it
                try:
                    supabase.table("profiles").insert({
                        "id": user_id,
                        "email": f"user_{user_id}@habexa.local",
                        "full_name": None,
                    }).execute()
                    logger.info(f"Created profile for user {user_id} after FK error")
                except Exception as create_error:
                    logger.error(f"Cannot create profile for user {user_id}: {create_error}")
                    raise TelegramServiceError("Your account profile is missing. Please contact support or try logging out and back in.")
            else:
                logger.warning(f"Error checking profile for user {user_id}: {e}")
        
        """
        Start Telegram authentication flow.
        Sends verification code to user's phone.
        """
        
        if not self.api_id or not self.api_hash:
            raise TelegramServiceError("Telegram not configured")
        
        # Normalize phone number
        phone = phone_number.strip().replace(" ", "").replace("-", "")
        # Normalize phone number - ensure it starts with +
        phone = phone.strip()
        if not phone.startswith("+"):
            # Try to add + if it's missing
            # If it starts with a digit, assume it needs country code
            if phone[0].isdigit():
                # Default to US country code if no + and starts with digit
                # User should provide full international format
                phone = f"+{phone}"
            else:
                raise ValueError("Phone number must be in international format starting with + (e.g., +1234567890)")
        
        try:
            # Create new client with empty session
            client = TelegramClient(
                StringSession(),
                self.api_id,
                self.api_hash,
                device_model="Habexa",
                system_version="1.0",
                app_version="1.0"
            )
            
            await client.connect()
            
            # Send code request
            result = await client.send_code_request(phone)
            
            # Store pending auth state
            _pending_codes[user_id] = {
                "client": client,
                "phone": phone,
                "phone_code_hash": result.phone_code_hash,
                "created_at": datetime.utcnow()
            }
            
            # Update database
            supabase.table("telegram_sessions").upsert({
                "user_id": user_id,
                "phone_number": phone,
                "is_connected": False,
                "is_authorized": False
            }, on_conflict="user_id").execute()
            
            logger.info(f"Sent Telegram code to {phone} for user {user_id}")
            
            return {
                "status": "code_sent",
                "phone": phone,
                "message": "Verification code sent to your Telegram app"
            }
            
        except FloodWaitError as e:
            raise TelegramServiceError(f"Too many attempts. Please wait {e.seconds} seconds.")
        except Exception as e:
            logger.error(f"Failed to start Telegram auth: {e}")
            raise TelegramServiceError(f"Failed to send code: {str(e)}")
    
    async def verify_code(
        self,
        user_id: str,
        code: str,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify the code sent to user's Telegram.
        """
        user_id = str(user_id)  # Ensure it's a string
        
        if user_id not in _pending_codes:
            raise TelegramServiceError("No pending verification. Please start again.")
        
        pending = _pending_codes[user_id]
        client = pending["client"]
        phone = pending["phone"]
        phone_code_hash = pending["phone_code_hash"]
        
        try:
            # Try to sign in
            await client.sign_in(
                phone=phone,
                code=code,
                phone_code_hash=phone_code_hash
            )
            
        except SessionPasswordNeededError:
            # 2FA is enabled
            if not password:
                return {
                    "status": "2fa_required",
                    "message": "Two-factor authentication is enabled. Please provide your password."
                }
            
            try:
                await client.sign_in(password=password)
            except Exception as e:
                raise TelegramServiceError(f"Invalid 2FA password: {str(e)}")
                
        except PhoneCodeInvalidError:
            raise TelegramServiceError("Invalid verification code")
        except PhoneCodeExpiredError:
            del _pending_codes[user_id]
            raise TelegramServiceError("Code expired. Please request a new one.")
        except Exception as e:
            raise TelegramServiceError(f"Verification failed: {str(e)}")
        
        # Get session string for storage
        session_string = client.session.save()
        
        # Store encrypted session
        supabase.table("telegram_sessions").update({
            "session_string_encrypted": encrypt_token(session_string),
            "is_connected": True,
            "is_authorized": True,
            "last_error": None,
            "error_count": 0
        }).eq("user_id", user_id).execute()
        
        # Store active client
        _active_clients[user_id] = client
        
        # Clean up pending
        del _pending_codes[user_id]
        
        # Get user info
        me = await client.get_me()
        
        logger.info(f"User {user_id} connected Telegram account: {me.username or me.phone}")
        
        return {
            "status": "connected",
            "telegram_user": {
                "id": me.id,
                "username": me.username,
                "first_name": me.first_name,
                "phone": me.phone
            }
        }
    
    async def disconnect(self, user_id: str) -> Dict[str, str]:
        """Disconnect Telegram account."""
        
        # Stop monitoring if active
        await self.stop_monitoring(user_id)
        
        # Disconnect client
        if user_id in _active_clients:
            try:
                await _active_clients[user_id].disconnect()
            except:
                pass
            del _active_clients[user_id]
        
        # Update database
        supabase.table("telegram_sessions").update({
            "session_string_encrypted": None,
            "is_connected": False,
            "is_authorized": False,
            "is_monitoring": False
        }).eq("user_id", user_id).execute()
        
        # Delete channels
        supabase.table("telegram_channels").delete().eq("user_id", user_id).execute()
        
        logger.info(f"Disconnected Telegram for user {user_id}")
        
        return {"message": "Telegram disconnected"}
    
    async def get_status(self, user_id: str) -> Dict[str, Any]:
        """Get Telegram connection status."""
        
        result = supabase.table("telegram_sessions")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data or len(result.data) == 0:
            return {
                "connected": False,
                "authorized": False,
                "monitoring": False
            }
        
        data = result.data[0]
        
        return {
            "connected": data["is_connected"],
            "authorized": data["is_authorized"],
            "monitoring": data["is_monitoring"],
            "phone": data.get("phone_number"),
            "error": data.get("last_error"),
            "monitoring_since": data.get("monitoring_started_at")
        }
    
    # ==========================================
    # CLIENT MANAGEMENT
    # ==========================================
    
    async def _get_client(self, user_id: str) -> TelegramClient:
        """Get or create Telegram client for user."""
        
        if user_id in _active_clients:
            client = _active_clients[user_id]
            if client.is_connected():
                return client
        
        # Load session from database
        result = supabase.table("telegram_sessions")\
            .select("session_string_encrypted")\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data or len(result.data) == 0 or not result.data[0].get("session_string_encrypted"):
            raise TelegramServiceError("Telegram not connected")
        
        session_string = decrypt_token(result.data[0]["session_string_encrypted"])
        
        client = TelegramClient(
            StringSession(session_string),
            self.api_id,
            self.api_hash,
            device_model="Habexa",
            system_version="1.0",
            app_version="1.0"
        )
        
        try:
            await client.connect()
            
            if not await client.is_user_authorized():
                raise TelegramServiceError("Session expired. Please reconnect.")
            
            _active_clients[user_id] = client
            return client
            
        except AuthKeyUnregisteredError:
            # Session is invalid
            supabase.table("telegram_sessions").update({
                "is_connected": False,
                "is_authorized": False,
                "last_error": "Session expired"
            }).eq("user_id", user_id).execute()
            
            raise TelegramServiceError("Session expired. Please reconnect your Telegram account.")
    
    # ==========================================
    # CHANNEL MANAGEMENT
    # ==========================================
    
    async def get_available_channels(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get list of channels/groups the user is member of.
        """
        
        client = await self._get_client(user_id)
        
        channels = []
        
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            
            # Only include channels and groups
            if isinstance(entity, Channel):
                channels.append({
                    "id": entity.id,
                    "name": entity.title,
                    "username": entity.username,
                    "type": "channel" if entity.broadcast else "supergroup",
                    "member_count": entity.participants_count,
                    "is_verified": entity.verified,
                    "is_restricted": entity.restricted
                })
            elif isinstance(entity, Chat):
                channels.append({
                    "id": entity.id,
                    "name": entity.title,
                    "username": None,
                    "type": "group",
                    "member_count": entity.participants_count
                })
        
        # Sort by name
        channels.sort(key=lambda x: x["name"].lower())
        
        return channels
    
    async def add_channel(
        self,
        user_id: str,
        channel_id: int,
        channel_name: str,
        channel_username: Optional[str] = None,
        channel_type: str = "channel",
        supplier_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a channel to monitoring list."""
        
        channel_data = {
            "user_id": user_id,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "channel_username": channel_username,
            "channel_type": channel_type,
            "is_active": True
        }
        
        if supplier_id:
            channel_data["supplier_id"] = supplier_id
        
        result = supabase.table("telegram_channels").upsert(
            channel_data,
            on_conflict="user_id,channel_id"
        ).execute()
        
        logger.info(f"User {user_id} added channel: {channel_name} ({channel_id}, @{channel_username or 'no-username'})" + (f" with supplier {supplier_id}" if supplier_id else ""))
        
        return result.data[0] if result.data else None
    
    async def remove_channel(self, user_id: str, channel_id: int):
        """Remove a channel from monitoring."""
        
        supabase.table("telegram_channels")\
            .update({"is_active": False})\
            .eq("user_id", user_id)\
            .eq("channel_id", channel_id)\
            .execute()
        
        logger.info(f"User {user_id} removed channel: {channel_id}")
    
    async def get_monitored_channels(self, user_id: str) -> List[Dict[str, Any]]:
        """Get list of channels being monitored."""
        
        result = supabase.table("telegram_channels")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("is_active", True)\
            .order("created_at")\
            .execute()
        
        return result.data or []
    
    # ==========================================
    # BACKFILL (Historical Messages)
    # ==========================================
    
    async def backfill_channel(
        self,
        user_id: str,
        channel_id: int,
        days: int = 14
    ) -> Dict[str, Any]:
        """
        Fetch last N days of messages from a channel.
        Call this when a channel is first added.
        """
        
        client = await self._get_client(user_id)
        
        if not client:
            logger.error("DEBUG: Client is None - not connected to Telegram")
            raise TelegramServiceError("Not connected to Telegram")
        
        try:
            # Get channel info from database (need username, not just ID)
            channel_result = supabase.table("telegram_channels")\
                .select("id, channel_username, channel_name")\
                .eq("user_id", user_id)\
                .eq("channel_id", channel_id)\
                .single()\
                .execute()
            
            if not channel_result.data:
                logger.error(f"DEBUG: Channel not found in database - user_id: {user_id}, channel_id: {channel_id}")
                raise TelegramServiceError("Channel not found in database")
            
            channel_db_id = channel_result.data["id"]
            channel_username = channel_result.data.get("channel_username")
            channel_name = channel_result.data.get("channel_name", "Unknown")
            
            logger.info(f"DEBUG: Looking for channel - username: {channel_username}, name: {channel_name}, id: {channel_id}")
            
            # Use username to get entity (more reliable than ID)
            entity = None
            
            if channel_username:
                try:
                    # Remove @ if present, then add it back for consistency
                    username = channel_username.lstrip('@')
                    entity = await client.get_entity(username)
                    logger.info(f"DEBUG: Found entity via username @{username}: {type(entity).__name__} - {getattr(entity, 'title', 'N/A')}")
                except Exception as e:
                    logger.warning(f"DEBUG: Username lookup failed for @{username}: {e}")
            
            if not entity:
                try:
                    entity = await client.get_entity(channel_id)
                    logger.info(f"DEBUG: Found entity via ID {channel_id}: {type(entity).__name__} - {getattr(entity, 'title', 'N/A')}")
                except Exception as id_error:
                    logger.warning(f"DEBUG: ID lookup failed for {channel_id}: {id_error}")
                    # Try as a channel peer
                    try:
                        from telethon.tl.types import PeerChannel
                        entity = await client.get_entity(PeerChannel(channel_id))
                        logger.info(f"DEBUG: Found entity via PeerChannel({channel_id}): {type(entity).__name__} - {getattr(entity, 'title', 'N/A')}")
                    except Exception as peer_error:
                        logger.error(f"DEBUG: PeerChannel lookup failed: {peer_error}")
            
            if not entity:
                error_msg = f"Could not find channel with username={channel_username}, id={channel_id}"
                logger.error(f"DEBUG: {error_msg}")
                raise TelegramServiceError(error_msg)
            
            logger.info(f"DEBUG: Entity resolved - type: {type(entity).__name__}, title: {getattr(entity, 'title', 'N/A')}, id: {getattr(entity, 'id', 'N/A')}")
            
            # Calculate date cutoff
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            logger.info(f"DEBUG: Fetching messages from {cutoff_date} to {datetime.utcnow()} (last {days} days)")
            
            messages_saved = 0
            deals_extracted = 0
            messages_checked = 0
            
            # Fetch messages (iter_messages handles pagination)
            logger.info(f"DEBUG: Starting message iteration for entity {getattr(entity, 'id', 'N/A')}")
            
            async for message in client.iter_messages(
                entity,
                offset_date=datetime.utcnow(),
                reverse=False,  # newest first
                limit=1000  # increased limit
            ):
                messages_checked += 1
                
                # Log first few messages for debugging
                if messages_checked <= 5:
                    msg_preview = message.text[:50] if message.text else 'NO TEXT'
                    logger.info(f"DEBUG: Message {message.id} - date: {message.date}, has_text: {bool(message.text)}, text_preview: {msg_preview}...")
                
                # Stop if message is older than cutoff
                if message.date:
                    # Handle timezone-aware dates
                    msg_date = message.date.replace(tzinfo=None) if message.date.tzinfo else message.date
                    if msg_date < cutoff_date:
                        logger.info(f"DEBUG: Stopping - message {message.id} date {msg_date} is before cutoff {cutoff_date} (checked {messages_checked} messages so far)")
                        break
                
                if not message.text:
                    continue
                
                # Save raw message (use upsert to avoid duplicates)
                msg_data = {
                    "user_id": user_id,
                    "channel_id": channel_db_id,
                    "telegram_channel_id": channel_id,
                    "telegram_message_id": message.id,
                    "content": message.text,
                    "sender_id": message.sender_id,
                    "telegram_date": message.date.isoformat() if message.date else None,
                    "is_processed": False,
                    "has_media": message.media is not None,
                    "media_type": type(message.media).__name__ if message.media else None,
                }
                
                # Upsert to avoid duplicates
                try:
                    result = supabase.table("telegram_messages").upsert(
                        msg_data,
                        on_conflict="user_id,telegram_channel_id,telegram_message_id"
                    ).execute()
                    
                    message_db_id = result.data[0]["id"] if result.data and len(result.data) > 0 else None
                    messages_saved += 1
                    
                    if messages_saved <= 3:
                        logger.info(f"DEBUG: Saved message {message.id} to database (ID: {message_db_id})")
                    
                    # Try to extract deals
                    if message_db_id:
                        try:
                            products = await product_extractor.extract_products(message.text)
                            
                            if products:
                                logger.info(f"DEBUG: Extracted {len(products)} products from message {message.id}")
                                # Update message with extraction results
                                supabase.table("telegram_messages").update({
                                    "is_processed": True,
                                    "extracted_products": products,
                                    "processed_at": datetime.utcnow().isoformat()
                                }).eq("id", message_db_id).execute()
                                
                                # Create deals for each product
                                for product in products:
                                    await self._create_deal(
                                        user_id=user_id,
                                        message_id=message_db_id,
                                        channel_id=channel_db_id,
                                        product=product
                                    )
                                
                                deals_extracted += len(products)
                        except Exception as e:
                            logger.warning(f"DEBUG: Product extraction failed for message {message.id}: {e}")
                except Exception as e:
                    # Skip duplicates or other errors
                    logger.warning(f"DEBUG: Failed to save message {message.id}: {e}")
                    continue
            
            # Update channel stats
            supabase.table("telegram_channels").update({
                "messages_received": messages_saved,
                "deals_extracted": deals_extracted,
                "last_message_at": datetime.utcnow().isoformat(),
            }).eq("user_id", user_id).eq("channel_id", channel_id).execute()
            
            logger.info(f"DEBUG: Checked {messages_checked} messages, saved {messages_saved}, extracted {deals_extracted} deals")
            logger.info(f"Backfill complete for {channel_name} (@{channel_username or 'no-username'}): {messages_saved} messages, {deals_extracted} deals")
            
            return {
                "messages": messages_saved,
                "deals": deals_extracted,
                "checked": messages_checked,
                "channel": channel_username or str(channel_id)
            }
            
        except Exception as e:
            logger.error(f"DEBUG: Backfill exception for channel {channel_id}: {e}")
            import traceback
            logger.error(f"DEBUG: Traceback:\n{traceback.format_exc()}")
            raise TelegramServiceError(f"Backfill failed: {str(e)}")
    
    # ==========================================
    # MONITORING
    # ==========================================
    
    async def start_monitoring(self, user_id: str) -> Dict[str, str]:
        """
        Start monitoring all active channels for a user.
        Creates background task that processes incoming messages.
        """
        
        if user_id in _monitoring_tasks:
            return {"status": "already_monitoring"}
        
        client = await self._get_client(user_id)
        
        # Get channels to monitor
        channels = await self.get_monitored_channels(user_id)
        
        if not channels:
            raise TelegramServiceError("No channels to monitor. Add channels first.")
        
        channel_ids = [c["channel_id"] for c in channels]
        
        # Create message handler
        @client.on(events.NewMessage(chats=channel_ids))
        async def message_handler(event: events.NewMessage.Event):
            await self._process_message(user_id, event)
        
        # Update status
        supabase.table("telegram_sessions").update({
            "is_monitoring": True,
            "monitoring_started_at": datetime.utcnow().isoformat()
        }).eq("user_id", user_id).execute()
        
        # Start client (runs until disconnected)
        task = asyncio.create_task(self._run_monitoring(user_id, client))
        _monitoring_tasks[user_id] = task
        
        logger.info(f"Started monitoring {len(channels)} channels for user {user_id}")
        
        return {
            "status": "monitoring",
            "channels": len(channels),
            "message": f"Monitoring {len(channels)} channels"
        }
    
    async def _run_monitoring(self, user_id: str, client: TelegramClient):
        """Background task that keeps monitoring running."""
        
        try:
            await client.run_until_disconnected()
        except Exception as e:
            logger.error(f"Monitoring error for user {user_id}: {e}")
            
            # Get current error count
            result = supabase.table("telegram_sessions")\
                .select("error_count")\
                .eq("user_id", user_id)\
                .execute()
            
            error_count = result.data[0].get("error_count", 0) if result.data else 0
            
            supabase.table("telegram_sessions").update({
                "is_monitoring": False,
                "last_error": str(e),
                "error_count": error_count + 1
            }).eq("user_id", user_id).execute()
        finally:
            if user_id in _monitoring_tasks:
                del _monitoring_tasks[user_id]
    
    async def stop_monitoring(self, user_id: str) -> Dict[str, str]:
        """Stop monitoring for a user."""
        
        if user_id in _monitoring_tasks:
            _monitoring_tasks[user_id].cancel()
            try:
                await _monitoring_tasks[user_id]
            except asyncio.CancelledError:
                pass
            del _monitoring_tasks[user_id]
        
        supabase.table("telegram_sessions").update({
            "is_monitoring": False
        }).eq("user_id", user_id).execute()
        
        logger.info(f"Stopped monitoring for user {user_id}")
        
        return {"status": "stopped"}
    
    # ==========================================
    # MESSAGE PROCESSING
    # ==========================================
    
    async def _process_message(self, user_id: str, event: events.NewMessage.Event):
        """
        Process incoming Telegram message.
        Stores message and extracts products.
        """
        
        message = event.message
        
        # Get channel info
        channel_result = supabase.table("telegram_channels")\
            .select("id")\
            .eq("user_id", user_id)\
            .eq("channel_id", event.chat_id)\
            .execute()
        
        channel_db_id = channel_result.data[0]["id"] if channel_result.data and len(channel_result.data) > 0 else None
        
        # Store message
        msg_data = {
            "user_id": user_id,
            "channel_id": channel_db_id,
            "telegram_message_id": message.id,
            "telegram_channel_id": event.chat_id,
            "content": message.text or "",
            "has_media": message.media is not None,
            "media_type": type(message.media).__name__ if message.media else None,
            "sender_id": message.sender_id,
            "sender_name": None,  # Would need to fetch sender
            "telegram_date": message.date.isoformat() if message.date else None,
            "is_processed": False
        }
        
        result = supabase.table("telegram_messages").insert(msg_data).execute()
        message_db_id = result.data[0]["id"] if result.data and len(result.data) > 0 else None
        
        # Extract products from message
        if message.text:
            try:
                products = await product_extractor.extract_products(message.text)
                
                if products:
                    # Update message with extraction results
                    supabase.table("telegram_messages").update({
                        "is_processed": True,
                        "extracted_products": products,
                        "processed_at": datetime.utcnow().isoformat()
                    }).eq("id", message_db_id).execute()
                    
                    # Create deals for each product
                    for product in products:
                        await self._create_deal(
                            user_id=user_id,
                            message_id=message_db_id,
                            channel_id=channel_db_id,
                            product=product
                        )
                    
                    logger.info(f"Extracted {len(products)} products from message for user {user_id}")
                else:
                    supabase.table("telegram_messages").update({
                        "is_processed": True,
                        "processed_at": datetime.utcnow().isoformat()
                    }).eq("id", message_db_id).execute()
                    
            except Exception as e:
                logger.error(f"Product extraction failed: {e}")
                supabase.table("telegram_messages").update({
                    "is_processed": True,
                    "extraction_error": str(e),
                    "processed_at": datetime.utcnow().isoformat()
                }).eq("id", message_db_id).execute()
    
    async def _create_deal(
        self,
        user_id: str,
        message_id: str,
        channel_id: str,
        product: Dict[str, Any]
    ):
        """Create a deal record from extracted product."""
        
        deal_data = {
            "user_id": user_id,
            "message_id": message_id,
            "channel_id": channel_id,
            "asin": product["asin"],
            "buy_cost": product.get("price"),
            "moq": product.get("moq", 1),
            "product_title": product.get("title"),
            "notes": product.get("notes"),
            "stage": "new",
            "status": "pending"
        }
        
        # Use upsert to avoid duplicates (based on user_id, channel_id, asin)
        result = supabase.table("telegram_deals").upsert(
            deal_data,
            on_conflict="user_id,channel_id,asin"
        ).execute()
        deal_id = result.data[0]["id"] if result.data and len(result.data) > 0 else None
        
        # Queue for analysis if auto_analyze is enabled
        channel_result = supabase.table("telegram_channels")\
            .select("auto_analyze")\
            .eq("id", channel_id)\
            .execute()
        
        if channel_result.data and len(channel_result.data) > 0 and channel_result.data[0].get("auto_analyze"):
            # TODO: Queue analysis task
            # For now, we'll let the frontend trigger analysis
            pass
        
        return deal_id
    
    # ==========================================
    # DEAL MANAGEMENT
    # ==========================================
    
    async def get_pending_deals(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get pending deals that haven't been analyzed."""
        
        result = supabase.table("telegram_deals")\
            .select("*, telegram_channels(channel_name)")\
            .eq("user_id", user_id)\
            .eq("status", "pending")\
            .order("extracted_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return result.data or []
    
    async def get_recent_messages(
        self,
        user_id: str,
        channel_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent messages from monitored channels."""
        
        query = supabase.table("telegram_messages")\
            .select("*, telegram_channels(channel_name)")\
            .eq("user_id", user_id)\
            .order("telegram_date", desc=True)\
            .limit(limit)
        
        if channel_id:
            query = query.eq("channel_id", channel_id)
        
        result = query.execute()
        
        return result.data or []


# Singleton instance
telegram_service = TelegramService()

