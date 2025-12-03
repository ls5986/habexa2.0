"""
Email service for sending transactional emails.
Supports multiple providers: Resend, SendGrid, Postmark, SES.

Set EMAIL_PROVIDER and EMAIL_API_KEY in environment variables.
"""
import os
import logging
from typing import Optional
from datetime import datetime
from app.core.config import settings
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "resend")  # resend, sendgrid, postmark, ses
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@habexa.com")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Habexa")


class EmailService:
    """Email service with provider abstraction."""
    
    @staticmethod
    async def send_email(
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send email using configured provider.
        
        Returns True if sent successfully, False otherwise.
        """
        if not EMAIL_API_KEY:
            logger.warning("EMAIL_API_KEY not configured. Email not sent.")
            return False
        
        try:
            if EMAIL_PROVIDER == "resend":
                return await EmailService._send_resend(to, subject, html_body, text_body)
            elif EMAIL_PROVIDER == "sendgrid":
                return await EmailService._send_sendgrid(to, subject, html_body, text_body)
            elif EMAIL_PROVIDER == "postmark":
                return await EmailService._send_postmark(to, subject, html_body, text_body)
            elif EMAIL_PROVIDER == "ses":
                return await EmailService._send_ses(to, subject, html_body, text_body)
            else:
                logger.error(f"Unknown email provider: {EMAIL_PROVIDER}")
                return False
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def _send_resend(to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
        """Send email via Resend API."""
        try:
            import httpx
            
            response = httpx.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {EMAIL_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>",
                    "to": [to],
                    "subject": subject,
                    "html": html_body,
                    "text": text_body or html_body.replace("<br>", "\n").replace("</p>", "\n\n")
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Email sent via Resend to {to}")
                return True
            else:
                logger.error(f"Resend API error: {response.status_code} - {response.text}")
                return False
        except ImportError:
            logger.error("httpx not installed. Install with: pip install httpx")
            return False
    
    @staticmethod
    async def _send_sendgrid(to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
        """Send email via SendGrid API."""
        try:
            import httpx
            
            response = httpx.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {EMAIL_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "personalizations": [{"to": [{"email": to}]}],
                    "from": {"email": EMAIL_FROM, "name": EMAIL_FROM_NAME},
                    "subject": subject,
                    "content": [
                        {"type": "text/html", "value": html_body}
                    ] + ([{"type": "text/plain", "value": text_body}] if text_body else [])
                },
                timeout=10
            )
            
            if response.status_code == 202:
                logger.info(f"Email sent via SendGrid to {to}")
                return True
            else:
                logger.error(f"SendGrid API error: {response.status_code} - {response.text}")
                return False
        except ImportError:
            logger.error("httpx not installed. Install with: pip install httpx")
            return False
    
    @staticmethod
    async def _send_postmark(to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
        """Send email via Postmark API."""
        try:
            import httpx
            
            response = httpx.post(
                "https://api.postmarkapp.com/email",
                headers={
                    "X-Postmark-Server-Token": EMAIL_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "From": f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>",
                    "To": to,
                    "Subject": subject,
                    "HtmlBody": html_body,
                    "TextBody": text_body or html_body.replace("<br>", "\n").replace("</p>", "\n\n")
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Email sent via Postmark to {to}")
                return True
            else:
                logger.error(f"Postmark API error: {response.status_code} - {response.text}")
                return False
        except ImportError:
            logger.error("httpx not installed. Install with: pip install httpx")
            return False
    
    @staticmethod
    async def _send_ses(to: str, subject: str, html_body: str, text_body: Optional[str] = None) -> bool:
        """Send email via AWS SES."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            ses = boto3.client(
                'ses',
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "us-east-1")
            )
            
            response = ses.send_email(
                Source=f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>",
                Destination={"ToAddresses": [to]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_body, "Charset": "UTF-8"},
                        "Text": {"Data": text_body or html_body.replace("<br>", "\n").replace("</p>", "\n\n"), "Charset": "UTF-8"}
                    }
                }
            )
            
            logger.info(f"Email sent via SES to {to}: {response['MessageId']}")
            return True
        except ImportError:
            logger.error("boto3 not installed. Install with: pip install boto3")
            return False
        except ClientError as e:
            logger.error(f"SES error: {e}")
            return False
    
    @staticmethod
    async def send_trial_ending_email(user_id: str, trial_end_date: datetime):
        """Send trial ending reminder email (3 days before trial ends)."""
        try:
            # Get user email
            result = supabase.table("profiles")\
                .select("email, full_name")\
                .eq("id", user_id)\
                .maybe_single()\
                .execute()
            
            if not result.data:
                logger.warning(f"User {user_id} not found for trial ending email")
                return False
            
            email = result.data.get("email")
            name = result.data.get("full_name") or "there"
            
            if not email:
                logger.warning(f"No email for user {user_id}")
                return False
            
            trial_end_str = trial_end_date.strftime("%B %d, %Y")
            
            subject = "Your Habexa trial ends soon"
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #7C6AFA;">Your trial ends on {trial_end_str}</h1>
                    <p>Hi {name},</p>
                    <p>Your 7-day free trial of Habexa ends in 3 days ({trial_end_str}).</p>
                    <p>To continue using Habexa after your trial, make sure your payment method is up to date.</p>
                    <p style="margin-top: 30px;">
                        <a href="{settings.FRONTEND_URL}/settings?tab=billing" 
                           style="background-color: #7C6AFA; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                            Update Payment Method
                        </a>
                    </p>
                    <p style="margin-top: 30px; color: #666; font-size: 14px;">
                        If you have any questions, reply to this email or visit our help center.
                    </p>
                </div>
            </body>
            </html>
            """
            
            return await EmailService.send_email(email, subject, html_body)
        except Exception as e:
            logger.error(f"Failed to send trial ending email: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def send_payment_failed_email(user_id: str):
        """Send payment failed notification."""
        try:
            result = supabase.table("profiles")\
                .select("email, full_name")\
                .eq("id", user_id)\
                .maybe_single()\
                .execute()
            
            if not result.data:
                return False
            
            email = result.data.get("email")
            name = result.data.get("full_name") or "there"
            
            if not email:
                return False
            
            subject = "Payment failed - Update your payment method"
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #dc3545;">Payment Failed</h1>
                    <p>Hi {name},</p>
                    <p>We couldn't process your payment for your Habexa subscription.</p>
                    <p>Please update your payment method to continue using Habexa without interruption.</p>
                    <p style="margin-top: 30px;">
                        <a href="{settings.FRONTEND_URL}/settings?tab=billing" 
                           style="background-color: #7C6AFA; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                            Update Payment Method
                        </a>
                    </p>
                    <p style="margin-top: 30px; color: #666; font-size: 14px;">
                        If you continue to have issues, please contact support.
                    </p>
                </div>
            </body>
            </html>
            """
            
            return await EmailService.send_email(email, subject, html_body)
        except Exception as e:
            logger.error(f"Failed to send payment failed email: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def send_subscription_cancelled_email(user_id: str):
        """Send subscription cancelled confirmation."""
        try:
            result = supabase.table("profiles")\
                .select("email, full_name")\
                .eq("id", user_id)\
                .maybe_single()\
                .execute()
            
            if not result.data:
                return False
            
            email = result.data.get("email")
            name = result.data.get("full_name") or "there"
            
            if not email:
                return False
            
            subject = "Your Habexa subscription has been cancelled"
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #7C6AFA;">Subscription Cancelled</h1>
                    <p>Hi {name},</p>
                    <p>Your Habexa subscription has been cancelled.</p>
                    <p>You'll continue to have access until the end of your current billing period, then you'll be moved to the Free plan.</p>
                    <p style="margin-top: 30px;">
                        <a href="{settings.FRONTEND_URL}/pricing" 
                           style="background-color: #7C6AFA; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                            Resubscribe
                        </a>
                    </p>
                    <p style="margin-top: 30px; color: #666; font-size: 14px;">
                        We're sorry to see you go! If you change your mind, you can resubscribe anytime.
                    </p>
                </div>
            </body>
            </html>
            """
            
            return await EmailService.send_email(email, subject, html_body)
        except Exception as e:
            logger.error(f"Failed to send cancellation email: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def send_welcome_email(user_id: str):
        """Send welcome email after signup."""
        try:
            result = supabase.table("profiles")\
                .select("email, full_name")\
                .eq("id", user_id)\
                .maybe_single()\
                .execute()
            
            if not result.data:
                return False
            
            email = result.data.get("email")
            name = result.data.get("full_name") or "there"
            
            if not email:
                return False
            
            subject = "Welcome to Habexa!"
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #7C6AFA;">Welcome to Habexa, {name}!</h1>
                    <p>Thanks for signing up. You're all set to start analyzing Amazon products and finding profitable opportunities.</p>
                    <p style="margin-top: 30px;">
                        <a href="{settings.FRONTEND_URL}/dashboard" 
                           style="background-color: #7C6AFA; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                            Get Started
                        </a>
                    </p>
                    <p style="margin-top: 30px; color: #666; font-size: 14px;">
                        Need help? Check out our <a href="{settings.FRONTEND_URL}/docs">documentation</a> or reply to this email.
                    </p>
                </div>
            </body>
            </html>
            """
            
            return await EmailService.send_email(email, subject, html_body)
        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}", exc_info=True)
            return False

