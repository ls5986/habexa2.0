"""
PO Email API - Generate POs and send emails
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import Optional
import logging

from app.api.deps import get_current_user
from app.services.po_email_service import POEmailService
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/po-emails", tags=["po-emails"])


class GeneratePORequest(BaseModel):
    supplier_order_id: str
    template_id: Optional[str] = None
    send_email: bool = True


class CreateEmailTemplateRequest(BaseModel):
    supplier_id: Optional[str] = None
    name: str
    subject: str
    body_text: str
    body_html: Optional[str] = None
    is_default: bool = False
    cc_emails: Optional[list[str]] = None
    bcc_emails: Optional[list[str]] = None


@router.post("/generate")
async def generate_and_send_po(
    request: GeneratePORequest,
    current_user = Depends(get_current_user)
):
    """Generate PO PDF and optionally send email to supplier."""
    user_id = str(current_user.id)
    
    try:
        # Verify order belongs to user
        order_result = supabase.table('supplier_orders').select('id, user_id').eq(
            'id', request.supplier_order_id
        ).limit(1).execute()
        
        if not order_result.data:
            raise HTTPException(404, "Order not found")
        
        if order_result.data[0].get('user_id') != user_id:
            raise HTTPException(403, "Order doesn't belong to you")
        
        # Initialize service
        po_service = POEmailService(user_id)
        
        # Generate PO number
        po_number = await po_service.generate_po_number()
        
        # Generate PDF
        pdf_bytes = await po_service.generate_po_pdf(
            request.supplier_order_id,
            po_number
        )
        
        if not pdf_bytes:
            raise HTTPException(500, "Failed to generate PDF")
        
        # Create PO generation record
        po_gen_result = await po_service.create_po_generation(
            supplier_order_id=request.supplier_order_id,
            pdf_bytes=pdf_bytes,
            pdf_filename=f"{po_number}.pdf"
        )
        
        po_generation_id = po_gen_result['po_generation_id']
        
        # Send email if requested
        email_result = None
        if request.send_email:
            try:
                email_result = await po_service.send_po_email(
                    supplier_order_id=request.supplier_order_id,
                    po_number=po_number,
                    template_id=request.template_id,
                    pdf_bytes=pdf_bytes
                )
                
                # Update PO generation status
                supabase.table('po_generations').update({
                    'status': 'sent',
                    'email_sent_at': 'now()'
                }).eq('id', po_generation_id).execute()
                
                # Update order status
                supabase.table('supplier_orders').update({
                    'status': 'sent'
                }).eq('id', request.supplier_order_id).execute()
            
            except Exception as e:
                logger.error(f"Failed to send email: {e}")
                # Don't fail the whole request if email fails
                email_result = {'error': str(e)}
        
        return {
            'success': True,
            'po_number': po_number,
            'po_generation_id': po_generation_id,
            'pdf_generated': True,
            'email_sent': email_result is not None and 'error' not in email_result,
            'email_result': email_result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PO generation failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.post("/templates")
async def create_email_template(
    request: CreateEmailTemplateRequest,
    current_user = Depends(get_current_user)
):
    """Create email template for PO emails."""
    user_id = str(current_user.id)
    
    try:
        template_data = {
            'user_id': user_id,
            'supplier_id': request.supplier_id,
            'name': request.name,
            'subject': request.subject,
            'body_text': request.body_text,
            'body_html': request.body_html,
            'is_default': request.is_default,
            'cc_emails': request.cc_emails or [],
            'bcc_emails': request.bcc_emails or []
        }
        
        result = supabase.table('email_templates').insert(template_data).execute()
        
        return {
            'success': True,
            'template': result.data[0] if result.data else None
        }
    
    except Exception as e:
        logger.error(f"Failed to create template: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.get("/templates")
async def get_email_templates(
    supplier_id: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Get email templates."""
    user_id = str(current_user.id)
    
    try:
        query = supabase.table('email_templates').select('*').eq('user_id', user_id)
        
        if supplier_id:
            query = query.eq('supplier_id', supplier_id)
        
        result = query.order('name').execute()
        
        return {
            'templates': result.data or [],
            'count': len(result.data) if result.data else 0
        }
    
    except Exception as e:
        logger.error(f"Failed to get templates: {e}", exc_info=True)
        raise HTTPException(500, str(e))


@router.get("/generations/{supplier_order_id}")
async def get_po_generations(
    supplier_order_id: str,
    current_user = Depends(get_current_user)
):
    """Get PO generation history for an order."""
    user_id = str(current_user.id)
    
    try:
        result = supabase.table('po_generations').select(
            '''
            *,
            tracking:email_tracking(*)
            '''
        ).eq('supplier_order_id', supplier_order_id).eq('user_id', user_id).order(
            'created_at', desc=True
        ).execute()
        
        return {
            'generations': result.data or [],
            'count': len(result.data) if result.data else 0
        }
    
    except Exception as e:
        logger.error(f"Failed to get PO generations: {e}", exc_info=True)
        raise HTTPException(500, str(e))

