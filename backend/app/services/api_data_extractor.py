"""
API Data Extraction Service

Extracts structured data from SP-API and Keepa responses.
Stores both raw JSON responses AND extracted structured fields.
"""
import json
import logging
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def extract_sp_api_structured_data(sp_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured fields from SP-API response.
    Maps SP-API fields to our database columns.
    
    Returns dict with both structured fields AND raw response.
    """
    structured = {}
    
    # Store the complete raw response
    structured['sp_api_raw_response'] = sp_response
    structured['sp_api_last_fetched'] = datetime.utcnow().isoformat()
    
    # Extract from summaries if present
    if 'summaries' in sp_response and len(sp_response['summaries']) > 0:
        summary = sp_response['summaries'][0]
        
        # Basic info
        if summary.get('itemName'):
            structured['title'] = summary['itemName']
        if summary.get('brandName'):
            structured['brand'] = summary['brandName']
        if summary.get('manufacturer'):
            structured['manufacturer'] = summary['manufacturer']
        if summary.get('modelNumber'):
            structured['model_number'] = summary['modelNumber']
        if summary.get('partNumber'):
            structured['part_number'] = summary['partNumber']
        if summary.get('productGroup'):
            structured['product_group'] = summary['productGroup']
        if summary.get('productType'):
            structured['product_type'] = summary['productType']
        if summary.get('binding'):
            structured['binding'] = summary['binding']
        if summary.get('color'):
            structured['color'] = summary['color']
        if summary.get('size'):
            structured['size'] = summary['size']
        
        # Main image
        if 'mainImage' in summary and summary['mainImage']:
            structured['image_url'] = summary['mainImage'].get('link')
        
        # Categories
        if 'browseClassification' in summary and summary['browseClassification']:
            browse = summary['browseClassification']
            if browse.get('displayName'):
                structured['category'] = browse['displayName']
            if browse.get('classificationRank'):
                structured['category_rank'] = browse['classificationRank']
    
    # Extract from attributes
    if 'attributes' in sp_response:
        attrs = sp_response['attributes']
        
        # Identifiers
        if 'externally_assigned_product_identifier' in attrs:
            ids = attrs['externally_assigned_product_identifier']
            if isinstance(ids, list):
                for id_obj in ids:
                    id_type = id_obj.get('type', '').upper()
                    id_value = id_obj.get('value')
                    if id_type == 'EAN' and id_value:
                        structured['ean'] = id_value
                    elif id_type == 'UPC' and id_value:
                        structured['upc'] = id_value
                    elif id_type == 'ISBN' and id_value:
                        structured['isbn'] = id_value
        
        # Package dimensions
        if 'item_package_dimensions' in attrs:
            dims = attrs['item_package_dimensions']
            if isinstance(dims, list) and len(dims) > 0:
                dim = dims[0]
                if 'length' in dim and dim['length']:
                    structured['package_length'] = dim['length'].get('value')
                    structured['dimension_unit'] = dim['length'].get('unit')
                if 'width' in dim and dim['width']:
                    structured['package_width'] = dim['width'].get('value')
                if 'height' in dim and dim['height']:
                    structured['package_height'] = dim['height'].get('value')
                if 'weight' in dim and dim['weight']:
                    structured['package_weight'] = dim['weight'].get('value')
                    structured['weight_unit'] = dim['weight'].get('unit')
        
        # Item dimensions
        if 'item_dimensions' in attrs:
            dims = attrs['item_dimensions']
            if isinstance(dims, list) and len(dims) > 0:
                dim = dims[0]
                if 'length' in dim and dim['length']:
                    structured['item_length'] = dim['length'].get('value')
                if 'width' in dim and dim['width']:
                    structured['item_width'] = dim['width'].get('value')
                if 'height' in dim and dim['height']:
                    structured['item_height'] = dim['height'].get('value')
                if 'weight' in dim and dim['weight']:
                    structured['item_weight'] = dim['weight'].get('value')
        
        # Package quantity
        if 'item_package_quantity' in attrs:
            pkg_qty = attrs['item_package_quantity']
            if isinstance(pkg_qty, list) and len(pkg_qty) > 0:
                structured['package_quantity'] = pkg_qty[0].get('value')
        
        # Features & description
        if 'bullet_point' in attrs:
            bullet_points = attrs['bullet_point']
            if isinstance(bullet_points, list):
                structured['bullet_points'] = [bp.get('value') for bp in bullet_points if bp.get('value')]
        
        if 'product_description' in attrs:
            desc = attrs['product_description']
            if isinstance(desc, list) and len(desc) > 0:
                structured['description'] = desc[0].get('value')
    
    # Extract images
    if 'images' in sp_response:
        image_data = []
        for img in sp_response['images']:
            image_data.append({
                'variant': img.get('variant'),
                'link': img.get('link'),
                'height': img.get('height'),
                'width': img.get('width')
            })
        structured['images'] = image_data
    
    # Extract sales rank
    if 'salesRanks' in sp_response:
        ranks = sp_response['salesRanks']
        if len(ranks) > 0:
            # Get primary rank
            primary = next((r for r in ranks if r.get('displayGroupRanks')), None)
            if primary and 'displayGroupRanks' in primary:
                display_ranks = primary['displayGroupRanks']
                if len(display_ranks) > 0:
                    structured['bsr'] = display_ranks[0].get('rank')
    
    # Extract browse nodes
    if 'browseNodes' in sp_response:
        structured['browse_nodes'] = sp_response['browseNodes']
    
    return structured


def extract_keepa_structured_data(keepa_response: Dict[str, Any], asin: str) -> Dict[str, Any]:
    """
    Extract structured fields from Keepa response.
    Keepa has TONS of valuable data - pricing history, sales rank trends, etc.
    
    Returns dict with both structured fields AND raw response.
    """
    structured = {}
    
    # Store the complete raw response
    structured['keepa_raw_response'] = keepa_response
    structured['keepa_last_fetched'] = datetime.utcnow().isoformat()
    
    # Get product from response
    products = keepa_response.get('products', [])
    if not products or len(products) == 0:
        return structured
    
    product = products[0]
    
    # Basic info
    if product.get('title'):
        structured['title'] = product['title']
    if product.get('brand'):
        structured['brand'] = product['brand']
    if product.get('manufacturer'):
        structured['manufacturer'] = product['manufacturer']
    if product.get('productGroup'):
        structured['product_group'] = product['productGroup']
    if product.get('partNumber'):
        structured['part_number'] = product['partNumber']
    if product.get('model'):
        structured['model_number'] = product['model']
    if product.get('color'):
        structured['color'] = product['color']
    if product.get('size'):
        structured['size'] = product['size']
    
    # Identifiers
    ean_list = product.get('eanList', [])
    if ean_list:
        structured['ean'] = ','.join(str(e) for e in ean_list)
    upc_list = product.get('upcList', [])
    if upc_list:
        structured['upc'] = ','.join(str(u) for u in upc_list)
    
    # Images
    images_csv = product.get('imagesCSV')
    if images_csv:
        image_ids = [img_id.strip() for img_id in images_csv.split(',') if img_id.strip()]
        structured['images'] = [
            {'url': f"https://images-na.ssl-images-amazon.com/images/I/{img_id}", 'source': 'keepa'}
            for img_id in image_ids
        ]
        if image_ids:
            structured['image_url'] = f"https://images-na.ssl-images-amazon.com/images/I/{image_ids[0]}"
    
    # Sales rank from CSV data
    csv_data = product.get('csv', [])
    if csv_data and len(csv_data) > 3:
        rank_csv = csv_data[3]  # Index 3 = sales rank
        if rank_csv and len(rank_csv) >= 2:
            # Last rank value
            structured['current_sales_rank'] = rank_csv[-1] if rank_csv[-1] > 0 else None
            
            # Calculate averages
            structured['sales_rank_30_day_avg'] = calculate_rank_average(rank_csv, days=30)
            structured['sales_rank_90_day_avg'] = calculate_rank_average(rank_csv, days=90)
            structured['sales_rank_180_day_avg'] = calculate_rank_average(rank_csv, days=180)
            
            # Calculate drops
            structured['sales_rank_drops_30_day'] = calculate_rank_drops(rank_csv, days=30)
            structured['sales_rank_drops_90_day'] = calculate_rank_drops(rank_csv, days=90)
    
    # Pricing data from CSV
    if csv_data and len(csv_data) > 0:
        # Amazon price (index 0)
        amazon_prices = csv_data[0]
        if amazon_prices and len(amazon_prices) >= 2:
            structured['amazon_price_current'] = keepa_price_to_dollars(amazon_prices[-1])
            structured['amazon_price_30_day_avg'] = calculate_price_average(amazon_prices, days=30)
            structured['amazon_price_90_day_avg'] = calculate_price_average(amazon_prices, days=90)
        
        # New price (index 1)
        if len(csv_data) > 1:
            new_prices = csv_data[1]
            if new_prices and len(new_prices) >= 2:
                structured['new_price_current'] = keepa_price_to_dollars(new_prices[-1])
                structured['new_price_30_day_avg'] = calculate_price_average(new_prices, days=30)
                structured['new_price_90_day_avg'] = calculate_price_average(new_prices, days=90)
        
        # Buy Box price (index 18)
        if len(csv_data) > 18:
            buybox_prices = csv_data[18]
            if buybox_prices and len(buybox_prices) >= 2:
                structured['buybox_price_current'] = keepa_price_to_dollars(buybox_prices[-1])
        
        # Availability (index 2)
        if len(csv_data) > 2:
            availability = csv_data[2]
            if availability and len(availability) >= 2:
                structured['in_stock'] = availability[-1] == 0  # 0 = in stock
                structured['out_of_stock_percentage'] = calculate_oos_percentage(availability, days=90)
    
    # Stats data
    stats = product.get('stats', {})
    
    # Ratings & reviews
    rating = stats.get('rating')
    if rating:
        structured['rating_average'] = round(rating / 10.0, 2)  # Keepa stores 0-100, convert to 0-10
    structured['review_count'] = stats.get('reviewsTotal', 0)
    
    # Seller counts
    structured['seller_count'] = stats.get('offerCount', 0)
    structured['fba_seller_count'] = stats.get('offerCountFBA', 0)
    
    # Package dimensions
    if product.get('packageLength'):
        structured['package_length'] = product['packageLength'] / 100  # cm to meters
    if product.get('packageWidth'):
        structured['package_width'] = product['packageWidth'] / 100
    if product.get('packageHeight'):
        structured['package_height'] = product['packageHeight'] / 100
    if product.get('packageWeight'):
        structured['package_weight'] = product['packageWeight']  # Already in kg
    
    # Item weight
    if product.get('itemWeight'):
        structured['item_weight'] = product['itemWeight']
    
    # Hazmat
    structured['is_hazmat'] = product.get('isHazmat', False) or product.get('hazmatType', 0) > 0
    
    # Product age
    listed_since = product.get('listedSince')
    if listed_since:
        first_available = keepa_time_to_date(listed_since)
        structured['first_available_date'] = first_available.isoformat()
        structured['age_in_days'] = (date.today() - first_available).days
    
    return structured


def keepa_price_to_dollars(keepa_price: int) -> Optional[float]:
    """Convert Keepa price format (negative = unavailable) to dollars."""
    if keepa_price is None or keepa_price < 0:
        return None
    return round(keepa_price / 100.0, 2)


def keepa_time_to_date(keepa_time: int) -> date:
    """Convert Keepa time (minutes since Jan 1, 2011) to date."""
    base = datetime(2011, 1, 1)
    return (base + timedelta(minutes=keepa_time)).date()


def calculate_rank_average(rank_history: List[int], days: int) -> Optional[int]:
    """Calculate average sales rank over last N days."""
    if not rank_history or len(rank_history) < 2:
        return None
    
    # Keepa time is minutes since Jan 1, 2011
    cutoff_time = int((datetime.now() - timedelta(days=days) - datetime(2011, 1, 1)).total_seconds() / 60)
    
    recent_ranks = []
    for i in range(0, len(rank_history) - 1, 2):
        timestamp = rank_history[i]
        rank = rank_history[i + 1]
        if timestamp >= cutoff_time and rank > 0:
            recent_ranks.append(rank)
    
    return int(sum(recent_ranks) / len(recent_ranks)) if recent_ranks else None


def calculate_rank_drops(rank_history: List[int], days: int) -> Optional[int]:
    """
    Count significant rank improvements (drops in number = more sales).
    Rough indicator of sales velocity.
    """
    if not rank_history or len(rank_history) < 4:
        return None
    
    cutoff_time = int((datetime.now() - timedelta(days=days) - datetime(2011, 1, 1)).total_seconds() / 60)
    
    drops = 0
    for i in range(2, len(rank_history) - 1, 2):
        if rank_history[i] < cutoff_time:
            continue
        
        current_rank = rank_history[i + 1]
        prev_rank = rank_history[i - 1]
        
        # Drop of 10000+ in rank = likely a sale
        if prev_rank > 0 and current_rank > 0 and (prev_rank - current_rank) > 10000:
            drops += 1
    
    return drops


def calculate_price_average(price_history: List[int], days: int) -> Optional[float]:
    """Calculate average price over last N days."""
    if not price_history or len(price_history) < 2:
        return None
    
    cutoff_time = int((datetime.now() - timedelta(days=days) - datetime(2011, 1, 1)).total_seconds() / 60)
    
    recent_prices = []
    for i in range(0, len(price_history) - 1, 2):
        timestamp = price_history[i]
        price = price_history[i + 1]
        if timestamp >= cutoff_time and price >= 0:
            recent_prices.append(price)
    
    if not recent_prices:
        return None
    
    avg_cents = sum(recent_prices) / len(recent_prices)
    return round(avg_cents / 100.0, 2)


def calculate_oos_percentage(availability_history: List[int], days: int) -> Optional[int]:
    """Calculate what % of time product was out of stock."""
    if not availability_history or len(availability_history) < 4:
        return None
    
    cutoff_time = int((datetime.now() - timedelta(days=days) - datetime(2011, 1, 1)).total_seconds() / 60)
    
    total_minutes = 0
    oos_minutes = 0
    
    for i in range(2, len(availability_history) - 1, 2):
        if availability_history[i] < cutoff_time:
            continue
        
        duration = availability_history[i] - availability_history[i - 2]
        total_minutes += duration
        
        if availability_history[i - 1] > 0:  # 0 = in stock, >0 = out of stock
            oos_minutes += duration
    
    return int((oos_minutes / total_minutes) * 100) if total_minutes > 0 else 0


def should_refresh_sp_data(product: Dict[str, Any], max_age_hours: int = 24) -> bool:
    """Check if we should make a new SP-API call or use cached data."""
    if not product.get('sp_api_last_fetched'):
        return True
    
    try:
        last_fetched_str = product['sp_api_last_fetched']
        if isinstance(last_fetched_str, str):
            last_fetched_str = last_fetched_str.replace('Z', '+00:00')
        last_fetched = datetime.fromisoformat(last_fetched_str)
        age_hours = (datetime.utcnow() - last_fetched.replace(tzinfo=None)).total_seconds() / 3600
        return age_hours > max_age_hours
    except Exception as e:
        logger.warning(f"Error checking SP-API data age: {e}")
        return True


def should_refresh_keepa_data(product: Dict[str, Any], max_age_hours: int = 24) -> bool:
    """Check if we should make a new Keepa call or use cached data."""
    if not product.get('keepa_last_fetched'):
        return True
    
    try:
        last_fetched_str = product['keepa_last_fetched']
        if isinstance(last_fetched_str, str):
            last_fetched_str = last_fetched_str.replace('Z', '+00:00')
        last_fetched = datetime.fromisoformat(last_fetched_str)
        age_hours = (datetime.utcnow() - last_fetched.replace(tzinfo=None)).total_seconds() / 3600
        return age_hours > max_age_hours
    except Exception as e:
        logger.warning(f"Error checking Keepa data age: {e}")
        return True

