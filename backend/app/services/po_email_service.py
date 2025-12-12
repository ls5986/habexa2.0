"""
Purchase Order Email Service

Generates PO PDFs and sends emails to suppliers via SendGrid.
"""
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime
import re
import os

from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail, Email, To, Attachment, FileContent, FileName, FileType, Disposition
    from sendgrid import SendGridAPIClient
    SENDGRID_AVAILABLE = True
except ImportError:
    logger.warning("SendGrid not installed. PO emails will not work.")
    SENDGRID_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    logger.warning("ReportLab not installed. PO PDF generation will not work.")
    REPORTLAB_AVAILABLE = False


class POEmailService:
    """Generate PO PDFs and send emails."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.sendgrid_api_key = os.getenv('SENDGRID_API_KEY')
        self.sendgrid_enabled = SENDGRID_AVAILABLE and bool(self.sendgrid_api_key)
    
    async def generate_po_number(self) -> str:
        """Generate unique PO number: PO-YYYY-MM-#####"""
        try:
            # Call database function
            result = supabase.rpc('generate_po_number').execute()
            if result.data:
                return result.data
        except Exception as e:
            logger.warning(f"Could not use database function, generating manually: {e}")
        
        # Fallback: manual generation
        now = datetime.utcnow()
        date_str = now.strftime('%Y-%m')
        
        # Get max sequence for this month
        try:
            max_result = supabase.table('po_generations').select('po_number').like(
                'po_number', f'PO-{date_str}-%'
            ).order('po_number', desc=True).limit(1).execute()
            
            if max_result.data:
                last_po = max_result.data[0]['po_number']
                last_seq = int(last_po.split('-')[-1])
                sequence = last_seq + 1
            else:
                sequence = 1
        except:
            sequence = 1
        
        return f"PO-{date_str}-{sequence:05d}"
    
    async def generate_po_pdf(
        self,
        supplier_order_id: str,
        po_number: str
    ) -> Optional[bytes]:
        """Generate PO PDF."""
        if not REPORTLAB_AVAILABLE:
            logger.error("ReportLab not available, cannot generate PDF")
            return None
        
        try:
            # Get order data
            order_result = supabase.table('supplier_orders').select(
                '''
                *,
                supplier:suppliers(*),
                items:supplier_order_items(
                    *,
                    product:products(*)
                )
                '''
            ).eq('id', supplier_order_id).limit(1).execute()
            
            if not order_result.data:
                raise ValueError("Order not found")
            
            order = order_result.data[0]
            supplier = order.get('supplier', {})
            items = order.get('items', [])
            
            # Create PDF in memory
            from io import BytesIO
            buffer = BytesIO()
            
            doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1a1a1a'),
                alignment=TA_CENTER,
                spaceAfter=30
            )
            story.append(Paragraph("PURCHASE ORDER", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # PO Number
            po_style = ParagraphStyle(
                'PONumber',
                parent=styles['Normal'],
                fontSize=14,
                alignment=TA_RIGHT
            )
            story.append(Paragraph(f"PO Number: <b>{po_number}</b>", po_style))
            story.append(Paragraph(f"Date: {datetime.utcnow().strftime('%B %d, %Y')}", po_style))
            story.append(Spacer(1, 0.3*inch))
            
            # Supplier Info
            supplier_data = [
                ['Supplier:', supplier.get('name', '')],
                ['Contact:', supplier.get('contact_email', '')],
                ['Phone:', supplier.get('contact_phone', '')],
                ['Address:', supplier.get('address', '')]
            ]
            
            supplier_table = Table(supplier_data, colWidths=[1.5*inch, 4.5*inch])
            supplier_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(supplier_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Line Items
            table_data = [['SKU', 'Description', 'Qty', 'Unit Price', 'Total']]
            
            total = 0
            for item in items:
                product = item.get('product', {})
                qty = item.get('quantity', 0)
                unit_price = float(item.get('unit_cost', 0))
                item_total = qty * unit_price
                total += item_total
                
                table_data.append([
                    item.get('supplier_sku', product.get('asin', '')),
                    product.get('title', '')[:50],  # Truncate long titles
                    str(qty),
                    f"${unit_price:.2f}",
                    f"${item_total:.2f}"
                ])
            
            # Total row
            table_data.append(['', '', '', 'TOTAL:', f"${total:.2f}"])
            
            items_table = Table(table_data, colWidths=[1*inch, 3*inch, 0.8*inch, 1*inch, 1*inch])
            items_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (-1, -1), (-1, -1), 'Helvetica-Bold'),
                ('ALIGN', (-1, -1), (-1, -1), 'RIGHT'),
            ]))
            story.append(items_table)
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            return buffer.read()
        
        except Exception as e:
            logger.error(f"Failed to generate PO PDF: {e}", exc_info=True)
            return None
    
    def render_email_template(
        self,
        template: Dict,
        variables: Dict[str, Any]
    ) -> tuple[str, str]:
        """
        Render email template with variables.
        
        Variables: {{order_number}}, {{total}}, {{supplier_name}}, etc.
        """
        subject = template.get('subject', '')
        body_text = template.get('body_text', '')
        body_html = template.get('body_html', body_text.replace('\n', '<br>'))
        
        # Replace variables
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            body_text = body_text.replace(placeholder, str(value))
            body_html = body_html.replace(placeholder, str(value))
        
        return subject, body_text, body_html
    
    async def send_po_email(
        self,
        supplier_order_id: str,
        po_number: str,
        template_id: Optional[str] = None,
        pdf_bytes: Optional[bytes] = None
    ) -> Dict:
        """Send PO email to supplier."""
        if not self.sendgrid_enabled:
            raise ValueError("SendGrid not configured")
        
        try:
            # Get order and supplier
            order_result = supabase.table('supplier_orders').select(
                '''
                *,
                supplier:suppliers(*)
                '''
            ).eq('id', supplier_order_id).limit(1).execute()
            
            if not order_result.data:
                raise ValueError("Order not found")
            
            order = order_result.data[0]
            supplier = order.get('supplier', {})
            
            # Get email template
            if template_id:
                template_result = supabase.table('email_templates').select('*').eq(
                    'id', template_id
                ).limit(1).execute()
                template = template_result.data[0] if template_result.data else None
            else:
                # Get default template for supplier
                template_result = supabase.table('email_templates').select('*').eq(
                    'supplier_id', supplier.get('id')
                ).eq('is_default', True).limit(1).execute()
                template = template_result.data[0] if template_result.data else None
            
            # Use default template if none found
            if not template:
                template = {
                    'subject': 'Purchase Order {{order_number}}',
                    'body_text': 'Please find attached Purchase Order {{order_number}} for {{supplier_name}}.\n\nTotal: {{total}}\n\nThank you!',
                    'body_html': None,
                    'cc_emails': [],
                    'bcc_emails': []
                }
            
            # Prepare variables
            variables = {
                'order_number': po_number,
                'total': f"${float(order.get('total_cost', 0)):.2f}",
                'supplier_name': supplier.get('name', ''),
                'order_date': datetime.utcnow().strftime('%B %d, %Y'),
                'items_count': len(order.get('items', []))
            }
            
            # Render template
            subject, body_text, body_html = self.render_email_template(template, variables)
            
            # Get recipient email
            recipient_email = supplier.get('contact_email') or supplier.get('email')
            if not recipient_email:
                raise ValueError("Supplier has no email address")
            
            # Send via SendGrid
            sg = SendGridAPIClient(self.sendgrid_api_key)
            
            from_email = Email(os.getenv('SENDGRID_FROM_EMAIL', 'orders@habexa.com'))
            to_email = To(recipient_email)
            
            message = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                plain_text_content=body_text,
                html_content=body_html
            )
            
            # Add CC/BCC
            for cc in template.get('cc_emails', []):
                message.add_cc(Email(cc))
            
            for bcc in template.get('bcc_emails', []):
                message.add_bcc(Email(bcc))
            
            # Add BCC to user
            user_result = supabase.table('profiles').select('email').eq('id', self.user_id).limit(1).execute()
            if user_result.data and user_result.data[0].get('email'):
                message.add_bcc(Email(user_result.data[0]['email']))
            
            # Attach PDF if provided
            if pdf_bytes:
                import base64
                encoded_pdf = base64.b64encode(pdf_bytes).decode()
                attachment = Attachment()
                attachment.file_content = FileContent(encoded_pdf)
                attachment.file_type = FileType('application/pdf')
                attachment.file_name = FileName(f"{po_number}.pdf")
                attachment.disposition = Disposition('attachment')
                message.attachment = attachment
            
            # Send
            response = sg.send(message)
            
            # Store email tracking
            email_id = response.headers.get('X-Message-Id')
            
            tracking_data = {
                'user_id': self.user_id,
                'po_generation_id': None,  # Will be set after creating po_generation
                'email_id': email_id,
                'recipient': recipient_email,
                'subject': subject,
                'status': 'sent',
                'sent_at': datetime.utcnow().isoformat()
            }
            
            tracking_result = supabase.table('email_tracking').insert(tracking_data).execute()
            tracking_id = tracking_result.data[0]['id'] if tracking_result.data else None
            
            return {
                'success': True,
                'email_id': email_id,
                'tracking_id': tracking_id,
                'status_code': response.status_code
            }
        
        except Exception as e:
            logger.error(f"Failed to send PO email: {e}", exc_info=True)
            raise
    
    async def create_po_generation(
        self,
        supplier_order_id: str,
        pdf_bytes: Optional[bytes] = None,
        pdf_filename: Optional[str] = None
    ) -> Dict:
        """Create PO generation record and optionally send email."""
        import base64
        
        try:
            # Generate PO number
            po_number = await self.generate_po_number()
            
            # TODO: Upload PDF to S3/storage and get URL
            pdf_url = None
            if pdf_bytes:
                # For now, store as base64 in database (not ideal for production)
                # In production, upload to S3 and store URL
                pdf_url = f"data:application/pdf;base64,{base64.b64encode(pdf_bytes).decode()}"
            
            # Create PO generation record
            po_data = {
                'user_id': self.user_id,
                'supplier_order_id': supplier_order_id,
                'po_number': po_number,
                'pdf_url': pdf_url,
                'pdf_filename': pdf_filename or f"{po_number}.pdf",
                'status': 'draft'
            }
            
            result = supabase.table('po_generations').insert(po_data).execute()
            po_generation_id = result.data[0]['id'] if result.data else None
            
            return {
                'success': True,
                'po_generation_id': po_generation_id,
                'po_number': po_number
            }
        
        except Exception as e:
            logger.error(f"Failed to create PO generation: {e}", exc_info=True)
            raise

