"""
Celery tasks for CSV exports.
"""
import csv
import io
import base64
from app.core.celery_app import celery_app
from app.services.supabase_client import supabase
from app.tasks.base import JobManager
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def export_products_csv(self, job_id: str, user_id: str, filters: dict = None):
    """Export products to CSV."""
    job = JobManager(job_id)
    
    try:
        job.start()
        
        # Build query
        query = supabase.table("product_deals")\
            .select("*")\
            .eq("user_id", user_id)
        
        if filters:
            if filters.get("stage"):
                query = query.eq("stage", filters["stage"])
            if filters.get("source"):
                query = query.eq("source", filters["source"])
            if filters.get("supplier_id"):
                query = query.eq("supplier_id", filters["supplier_id"])
        
        result = query.order("deal_created_at", desc=True).execute()
        deals = result.data or []
        
        total = len(deals)
        job.update_progress(0, total)
        
        # Build CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "asin", "title", "supplier", "buy_cost", "moq", "total_investment",
            "sell_price", "fees", "profit", "roi", "stage", "source", "notes"
        ])
        writer.writeheader()
        
        for i, deal in enumerate(deals):
            writer.writerow({
                "asin": deal.get("asin"),
                "title": deal.get("title"),
                "supplier": deal.get("supplier_name", "Unknown"),
                "buy_cost": deal.get("buy_cost"),
                "moq": deal.get("moq"),
                "total_investment": deal.get("total_investment"),
                "sell_price": deal.get("sell_price"),
                "fees": deal.get("fees_total"),
                "profit": deal.get("profit"),
                "roi": deal.get("roi"),
                "stage": deal.get("stage"),
                "source": deal.get("source"),
                "notes": deal.get("notes")
            })
            
            if i % 100 == 0:
                job.update_progress(i, total)
        
        csv_content = output.getvalue()
        csv_b64 = base64.b64encode(csv_content.encode()).decode()
        
        job.complete({
            "total_rows": total,
            "csv_base64": csv_b64,
            "filename": "products_export.csv"
        }, success=total, errors=0)
        
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        job.fail(str(e))

