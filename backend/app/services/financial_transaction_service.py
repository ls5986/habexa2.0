"""
Financial Transaction Service
Records all financial transactions and calculates P&L summaries.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from decimal import Decimal

from app.core.database import supabase

logger = logging.getLogger(__name__)


class FinancialTransactionService:
    """Manage financial transactions and P&L calculations."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    async def record_transaction(
        self,
        transaction_type: str,
        amount: float,
        description: str = None,
        quantity: int = None,
        unit_price: float = None,
        product_id: str = None,
        supplier_order_id: str = None,
        sale_id: str = None,
        category: str = None,
        transaction_date: date = None,
        notes: str = None
    ) -> Dict[str, Any]:
        """
        Record a financial transaction.
        
        Transaction types:
        - purchase: Buying from supplier (negative amount)
        - sale: Amazon sales (positive amount)
        - fee: Amazon fees (negative amount)
        - shipping: Shipping costs (negative amount)
        - tpl_fee: 3PL fees (negative amount)
        - refund: Customer refunds (negative amount)
        - reimbursement: Amazon reimbursements (positive amount)
        - adjustment: Manual adjustments
        """
        try:
            transaction = {
                'user_id': self.user_id,
                'transaction_type': transaction_type,
                'amount': float(amount),
                'currency': 'USD',
                'quantity': quantity,
                'unit_price': float(unit_price) if unit_price else None,
                'product_id': product_id,
                'supplier_order_id': supplier_order_id,
                'sale_id': sale_id,
                'description': description,
                'category': category,
                'transaction_date': (transaction_date or datetime.utcnow().date()).isoformat(),
                'notes': notes
            }
            
            result = supabase.table('financial_transactions').insert(transaction).execute()
            
            if result.data:
                # Trigger P&L recalculation for the period
                await self._recalculate_pl_summary(transaction_date or datetime.utcnow().date())
                
                logger.info(f"Recorded {transaction_type} transaction: ${amount}")
                return result.data[0]
            
            return None
        
        except Exception as e:
            logger.error(f"Error recording transaction: {e}", exc_info=True)
            raise
    
    async def record_supplier_order_purchase(
        self,
        supplier_order_id: str,
        total_cost: float,
        items: List[Dict[str, Any]]
    ):
        """Record a supplier order as a purchase transaction."""
        try:
            # Main purchase transaction
            await self.record_transaction(
                transaction_type='purchase',
                amount=-abs(total_cost),  # Negative for expense
                description=f'Purchase order from supplier',
                supplier_order_id=supplier_order_id,
                category='product_cost',
                transaction_date=datetime.utcnow().date()
            )
            
            # Optionally record individual line items
            for item in items:
                product_id = item.get('product_id')
                quantity = item.get('quantity', 0)
                unit_cost = item.get('unit_cost', 0)
                
                if product_id:
                    await self.record_transaction(
                        transaction_type='purchase',
                        amount=-abs(unit_cost * quantity),
                        description=f'Purchase: {item.get("product_title", "Product")}',
                        quantity=quantity,
                        unit_price=unit_cost,
                        product_id=product_id,
                        supplier_order_id=supplier_order_id,
                        category='product_cost'
                    )
            
            logger.info(f"Recorded purchase transaction for order {supplier_order_id}: ${total_cost}")
        
        except Exception as e:
            logger.error(f"Error recording purchase: {e}", exc_info=True)
            raise
    
    async def record_amazon_sale(
        self,
        sale_id: str,
        product_id: str,
        quantity: int,
        sale_price: float,
        fees: float,
        transaction_date: date = None
    ):
        """Record an Amazon sale transaction."""
        try:
            # Record sale (revenue)
            await self.record_transaction(
                transaction_type='sale',
                amount=sale_price * quantity,
                description=f'Amazon sale: {sale_id}',
                quantity=quantity,
                unit_price=sale_price,
                product_id=product_id,
                sale_id=sale_id,
                category='revenue',
                transaction_date=transaction_date
            )
            
            # Record fees (expense)
            if fees > 0:
                await self.record_transaction(
                    transaction_type='fee',
                    amount=-abs(fees),
                    description=f'Amazon fees for sale: {sale_id}',
                    product_id=product_id,
                    sale_id=sale_id,
                    category='amazon_fee',
                    transaction_date=transaction_date
                )
            
            logger.info(f"Recorded sale transaction {sale_id}: ${sale_price * quantity} (fees: ${fees})")
        
        except Exception as e:
            logger.error(f"Error recording sale: {e}", exc_info=True)
            raise
    
    async def record_shipping_cost(
        self,
        supplier_order_id: str,
        shipping_cost: float,
        transaction_date: date = None
    ):
        """Record shipping cost."""
        await self.record_transaction(
            transaction_type='shipping',
            amount=-abs(shipping_cost),
            description='Shipping cost',
            supplier_order_id=supplier_order_id,
            category='shipping_cost',
            transaction_date=transaction_date
        )
    
    async def record_tpl_fee(
        self,
        amount: float,
        description: str,
        product_id: str = None,
        transaction_date: date = None
    ):
        """Record 3PL/prep center fee."""
        await self.record_transaction(
            transaction_type='tpl_fee',
            amount=-abs(amount),
            description=description,
            product_id=product_id,
            category='prep_cost',
            transaction_date=transaction_date
        )
    
    async def record_refund(
        self,
        sale_id: str,
        refund_amount: float,
        reason: str = None,
        transaction_date: date = None
    ):
        """Record a customer refund."""
        await self.record_transaction(
            transaction_type='refund',
            amount=-abs(refund_amount),
            description=f'Customer refund{": " + reason if reason else ""}',
            sale_id=sale_id,
            category='refund',
            transaction_date=transaction_date
        )
    
    async def record_reimbursement(
        self,
        amount: float,
        description: str,
        product_id: str = None,
        transaction_date: date = None
    ):
        """Record Amazon reimbursement."""
        await self.record_transaction(
            transaction_type='reimbursement',
            amount=abs(amount),
            description=description,
            product_id=product_id,
            category='reimbursement',
            transaction_date=transaction_date
        )
    
    async def _recalculate_pl_summary(self, transaction_date: date):
        """Recalculate P&L summary for the period containing this transaction."""
        try:
            # Determine period (month)
            period_start = date(transaction_date.year, transaction_date.month, 1)
            period_end = date(transaction_date.year, transaction_date.month, 28) + datetime.timedelta(days=4)
            period_end = period_end.replace(day=1) - datetime.timedelta(days=1)  # Last day of month
            
            # Call database function to calculate P&L
            result = supabase.rpc('calculate_pl_summary', {
                'p_user_id': self.user_id,
                'p_start_date': period_start.isoformat(),
                'p_end_date': period_end.isoformat()
            }).execute()
            
            if result.data:
                pl_data = result.data[0]
                
                # Upsert P&L summary
                pl_summary = {
                    'user_id': self.user_id,
                    'period_start': period_start.isoformat(),
                    'period_end': period_end.isoformat(),
                    'period_type': 'month',
                    'total_revenue': float(pl_data.get('total_revenue', 0)),
                    'total_cogs': float(pl_data.get('total_cogs', 0)),
                    'total_amazon_fees': float(pl_data.get('total_fees', 0)),
                    'total_shipping_costs': float(pl_data.get('total_shipping', 0)),
                    'total_tpl_fees': float(pl_data.get('total_tpl', 0)),
                    'total_refunds': float(pl_data.get('total_refunds', 0)),
                    'total_reimbursements': float(pl_data.get('total_reimbursements', 0)),
                    'net_profit': float(pl_data.get('net_profit', 0)),
                    'profit_margin': float(pl_data.get('profit_margin', 0))
                }
                
                supabase.table('pl_summaries').upsert(
                    pl_summary,
                    on_conflict='user_id,period_start,period_end,period_type'
                ).execute()
        
        except Exception as e:
            logger.error(f"Error recalculating P&L summary: {e}", exc_info=True)
    
    async def get_pl_summary(
        self,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get P&L summary for date range."""
        try:
            result = supabase.rpc('calculate_pl_summary', {
                'p_user_id': self.user_id,
                'p_start_date': start_date.isoformat(),
                'p_end_date': end_date.isoformat()
            }).execute()
            
            if result.data:
                return result.data[0]
            return {}
        
        except Exception as e:
            logger.error(f"Error getting P&L summary: {e}", exc_info=True)
            return {}

