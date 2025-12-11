"""
Complete field extraction from SP-API and Keepa responses.

Maps API fields to products table columns.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SPAPIExtractor:
    """Extract and map SP-API Catalog fields to database columns."""
    
    @staticmethod
    def extract_all(sp_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract ALL useful fields from SP-API catalog response.
        
        SP-API Response Structure:
        {
          "asin": "B01GHFBKKA",
          "summaries": [{...}],
          "attributes": {...},
          "images": [{...}],
          "salesRanks": [{...}]
        }
        """
        extracted = {}
        
        try:
            # ===== BASIC INFO FROM SUMMARIES =====
            if 'summaries' in sp_response and sp_response['summaries']:
                summary = sp_response['summaries'][0]
                
                # Core product info
                extracted['title'] = summary.get('itemName')
                extracted['brand'] = summary.get('brandName')
                extracted['brand_name'] = summary.get('brandName')
                extracted['manufacturer'] = summary.get('manufacturer')
                extracted['model_number'] = summary.get('modelNumber')
                extracted['part_number'] = summary.get('partNumber')
                extracted['product_group'] = summary.get('productGroup')
                extracted['product_type'] = summary.get('productType')
                extracted['binding'] = summary.get('binding')
                extracted['color'] = summary.get('color')
                extracted['size'] = summary.get('size')
                extracted['style'] = summary.get('style')
                
                # Main image
                if 'mainImage' in summary:
                    extracted['image_url'] = summary['mainImage'].get('link')
                
                # Browse classification
                if 'browseClassification' in summary:
                    browse = summary['browseClassification']
                    extracted['category'] = browse.get('displayName')
                    extracted['category_rank'] = browse.get('classificationRank')
            
            # ===== IDENTIFIERS FROM ATTRIBUTES =====
            if 'attributes' in sp_response:
                attrs = sp_response['attributes']
                
                # External IDs
                if 'externally_assigned_product_identifier' in attrs:
                    for id_obj in attrs['externally_assigned_product_identifier']:
                        id_type = id_obj.get('type', '').upper()
                        id_value = id_obj.get('value')
                        
                        if id_type == 'EAN':
                            extracted['ean'] = id_value
                        elif id_type == 'UPC':
                            if not extracted.get('upc'):  # Don't overwrite existing
                                extracted['upc'] = id_value
                        elif id_type == 'ISBN':
                            extracted['isbn'] = id_value
                
                # ===== ITEM DIMENSIONS =====
                if 'item_dimensions' in attrs:
                    dims = attrs['item_dimensions']
                    if isinstance(dims, list) and len(dims) > 0:
                        dim = dims[0]
                        
                        if 'length' in dim:
                            extracted['item_length'] = dim['length'].get('value')
                            extracted['dimension_unit'] = dim['length'].get('unit')
                        
                        if 'width' in dim:
                            extracted['item_width'] = dim['width'].get('value')
                        
                        if 'height' in dim:
                            extracted['item_height'] = dim['height'].get('value')
                        
                        if 'weight' in dim:
                            extracted['item_weight'] = dim['weight'].get('value')
                            extracted['weight_unit'] = dim['weight'].get('unit')
                
                # ===== PACKAGE DIMENSIONS =====
                if 'item_package_dimensions' in attrs:
                    pkg_dims = attrs['item_package_dimensions']
                    if isinstance(pkg_dims, list) and len(pkg_dims) > 0:
                        pkg = pkg_dims[0]
                        
                        if 'length' in pkg:
                            extracted['package_length'] = pkg['length'].get('value')
                        
                        if 'width' in pkg:
                            extracted['package_width'] = pkg['width'].get('value')
                        
                        if 'height' in pkg:
                            extracted['package_height'] = pkg['height'].get('value')
                        
                        if 'weight' in pkg:
                            extracted['package_weight'] = pkg['weight'].get('value')
                
                # Package quantity
                if 'item_package_quantity' in attrs:
                    pkg_qty = attrs['item_package_quantity']
                    if isinstance(pkg_qty, list) and len(pkg_qty) > 0:
                        extracted['package_quantity'] = pkg_qty[0].get('value')
                
                # ===== PRODUCT FEATURES =====
                if 'bullet_point' in attrs:
                    extracted['bullet_points'] = [
                        bp.get('value') for bp in attrs['bullet_point']
                        if bp.get('value')
                    ]
                
                if 'product_description' in attrs:
                    desc = attrs['product_description']
                    if isinstance(desc, list) and len(desc) > 0:
                        extracted['description'] = desc[0].get('value')
                
                # Features list
                if 'feature' in attrs:
                    extracted['features'] = [
                        f.get('value') for f in attrs['feature']
                        if f.get('value')
                    ]
            
            # ===== IMAGES =====
            if 'images' in sp_response:
                image_data = []
                for img in sp_response['images']:
                    image_data.append({
                        'variant': img.get('variant'),
                        'link': img.get('link'),
                        'height': img.get('height'),
                        'width': img.get('width')
                    })
                extracted['images'] = image_data
            
            # ===== SALES RANK =====
            if 'salesRanks' in sp_response:
                ranks = sp_response['salesRanks']
                if ranks:
                    # Get primary rank
                    for rank_obj in ranks:
                        if 'displayGroupRanks' in rank_obj:
                            display_ranks = rank_obj['displayGroupRanks']
                            if display_ranks:
                                extracted['bsr'] = display_ranks[0].get('rank')
                                extracted['current_sales_rank'] = display_ranks[0].get('rank')
                                break
            
            # ===== BROWSE NODES =====
            if 'browseNodes' in sp_response:
                extracted['browse_nodes'] = sp_response['browseNodes']
            
            logger.debug(f"✅ Extracted {len(extracted)} fields from SP-API response")
            
        except Exception as e:
            logger.error(f"Error extracting SP-API fields: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return extracted


class SPAPIPricingExtractor:
    """Extract pricing data from SP-API Pricing endpoint."""
    
    @staticmethod
    def extract_all(pricing_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract pricing fields from SP-API Competitive Pricing response.
        
        Response Structure:
        {
          "Product": {
            "CompetitivePricing": {...},
            "Offers": [...]
          }
        }
        """
        extracted = {}
        
        try:
            if 'Product' not in pricing_response:
                return extracted
            
            product = pricing_response['Product']
            
            # ===== COMPETITIVE PRICING =====
            if 'CompetitivePricing' in product:
                comp = product['CompetitivePricing']
                
                # Buy Box price
                for price in comp.get('CompetitivePrices', []):
                    if price.get('condition') == 'New':
                        landed = price.get('Price', {}).get('LandedPrice', {})
                        extracted['buy_box_price'] = landed.get('Amount')
                        extracted['buybox_price_current'] = landed.get('Amount')
                        break
                
                # Number of offers
                offer_listings = comp.get('NumberOfOfferListings', [])
                if offer_listings:
                    for offer in offer_listings:
                        if offer.get('condition') == 'New':
                            extracted['seller_count'] = offer.get('Count', 0)
                            break
            
            # ===== OFFERS =====
            if 'Offers' in product:
                offers = product['Offers']
                if offers:
                    # Get lowest price
                    new_offers = [o for o in offers if o.get('ItemCondition') == 'New']
                    if new_offers:
                        prices = [
                            o.get('ListingPrice', {}).get('Amount') 
                            for o in new_offers 
                            if o.get('ListingPrice', {}).get('Amount')
                        ]
                        if prices:
                            extracted['lowest_price'] = min(prices)
                            extracted['new_price_current'] = min(prices)
                    
                    # Count FBA sellers
                    fba_count = sum(
                        1 for o in offers 
                        if o.get('IsFulfilledByAmazon') and o.get('ItemCondition') == 'New'
                    )
                    extracted['fba_seller_count'] = fba_count
                    
                    # Check if Amazon sells
                    amazon_sells = any(
                        o.get('SellerFeedbackRating', {}).get('SellerPositiveFeedbackRating') == 100
                        and o.get('SellerFeedbackRating', {}).get('FeedbackCount', 0) > 1000
                        for o in offers
                    )
                    extracted['amazon_sells'] = amazon_sells
            
            logger.debug(f"✅ Extracted {len(extracted)} pricing fields")
            
        except Exception as e:
            logger.error(f"Error extracting pricing data: {e}")
        
        return extracted


class SPAPIFeesExtractor:
    """Extract fee data from SP-API Fees endpoint."""
    
    @staticmethod
    def extract_all(fees_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract fee fields from SP-API My Fees Estimate response.
        
        Response Structure:
        {
          "FeesEstimate": {
            "TotalFeesEstimate": {...},
            "FeeDetailList": [...]
          }
        }
        """
        extracted = {}
        
        try:
            if 'FeesEstimate' not in fees_response:
                return extracted
            
            fees = fees_response['FeesEstimate']
            
            # Total fees
            total = fees.get('TotalFeesEstimate', {})
            extracted['fees_total'] = total.get('Amount')
            
            # Break down fees
            for fee_detail in fees.get('FeeDetailList', []):
                fee_type = fee_detail.get('FeeType')
                fee_amount = fee_detail.get('FinalFee', {}).get('Amount', 0)
                
                if fee_type == 'ReferralFee':
                    # Calculate percentage (if we have sell price)
                    pass  # Store raw amount for now
                
                elif fee_type == 'FBAFees':
                    extracted['fba_fees'] = fee_amount
            
            logger.debug(f"✅ Extracted fee data: total={extracted.get('fees_total')}, fba={extracted.get('fba_fees')}")
            
        except Exception as e:
            logger.error(f"Error extracting fees: {e}")
        
        return extracted


class KeepaExtractor:
    """Extract and map Keepa fields to database columns."""
    
    @staticmethod
    def extract_all(keepa_response: Dict[str, Any], asin: str = None) -> Dict[str, Any]:
        """
        Extract ALL useful fields from Keepa response.
        
        Keepa Response Structure:
        {
          "products": [{
            "asin": "B01GHFBKKA",
            "title": "...",
            "salesRanks": {category_id: [timestamp, rank, ...]},
            "csv": [[prices], [new_prices], ...],
            ...
          }]
        }
        """
        extracted = {}
        
        try:
            if 'products' not in keepa_response or not keepa_response['products']:
                return extracted
            
            product = keepa_response['products'][0]
            
            # ===== BASIC INFO =====
            if not extracted.get('title'):
                extracted['title'] = product.get('title')
            if not extracted.get('brand'):
                extracted['brand'] = product.get('brand')
            extracted['manufacturer'] = product.get('manufacturer')
            extracted['product_group'] = product.get('productGroup')
            extracted['part_number'] = product.get('partNumber')
            extracted['model_number'] = product.get('model')
            extracted['color'] = product.get('color')
            extracted['size'] = product.get('size')
            
            # ===== IDENTIFIERS =====
            if product.get('eanList'):
                extracted['ean'] = ','.join(str(e) for e in product['eanList'])
            
            if product.get('upcList'):
                if not extracted.get('upc'):
                    extracted['upc'] = ','.join(str(u) for u in product['upcList'])
            
            # ===== IMAGES =====
            if product.get('imagesCSV'):
                image_ids = product['imagesCSV'].split(',')
                extracted['images'] = [
                    {
                        'url': f"https://images-na.ssl-images-amazon.com/images/I/{img_id}",
                        'source': 'keepa'
                    }
                    for img_id in image_ids if img_id
                ]
            
            # ===== SALES RANK =====
            if product.get('salesRanks'):
                for category_id, rank_history in product['salesRanks'].items():
                    if rank_history and len(rank_history) >= 2:
                        # Current rank (last value)
                        extracted['current_sales_rank'] = rank_history[-1]
                        extracted['bsr'] = rank_history[-1]
                        
                        # Calculate averages
                        extracted['sales_rank_30_day_avg'] = KeepaExtractor._calc_rank_avg(
                            rank_history, days=30
                        )
                        extracted['sales_rank_90_day_avg'] = KeepaExtractor._calc_rank_avg(
                            rank_history, days=90
                        )
                        extracted['sales_rank_180_day_avg'] = KeepaExtractor._calc_rank_avg(
                            rank_history, days=180
                        )
                        
                        # Estimate sales from rank drops
                        extracted['sales_rank_drops_30_day'] = KeepaExtractor._calc_rank_drops(
                            rank_history, days=30
                        )
                        extracted['sales_rank_drops_90_day'] = KeepaExtractor._calc_rank_drops(
                            rank_history, days=90
                        )
                        
                        break  # Use first category
            
            # ===== PRICING FROM CSV =====
            if 'csv' in product:
                csv = product['csv']
                
                # Amazon price (index 0)
                if len(csv) > 0 and csv[0]:
                    amazon_prices = csv[0]
                    if amazon_prices and len(amazon_prices) >= 2:
                        last_price = amazon_prices[-1]
                        if last_price >= 0:
                            extracted['amazon_price_current'] = last_price / 100
                            extracted['amazon_price_30_day_avg'] = KeepaExtractor._calc_price_avg(
                                amazon_prices, days=30
                            )
                            extracted['amazon_price_90_day_avg'] = KeepaExtractor._calc_price_avg(
                                amazon_prices, days=90
                            )
                
                # New price (index 1)
                if len(csv) > 1 and csv[1]:
                    new_prices = csv[1]
                    if new_prices and len(new_prices) >= 2:
                        last_price = new_prices[-1]
                        if last_price >= 0:
                            extracted['new_price_current'] = last_price / 100
                            extracted['lowest_price'] = last_price / 100
                            extracted['new_price_30_day_avg'] = KeepaExtractor._calc_price_avg(
                                new_prices, days=30
                            )
                            extracted['new_price_90_day_avg'] = KeepaExtractor._calc_price_avg(
                                new_prices, days=90
                            )
                
                # Buy Box price (index 18)
                if len(csv) > 18 and csv[18]:
                    bb_prices = csv[18]
                    if bb_prices and len(bb_prices) >= 2:
                        last_price = bb_prices[-1]
                        if last_price >= 0:
                            extracted['buybox_price_current'] = last_price / 100
                            extracted['buy_box_price'] = last_price / 100
                
                # Availability (index 2)
                if len(csv) > 2 and csv[2]:
                    availability = csv[2]
                    if availability and len(availability) >= 2:
                        extracted['in_stock'] = availability[-1] == 0
                        extracted['out_of_stock_percentage'] = KeepaExtractor._calc_oos_pct(
                            availability, days=90
                        )
            
            # ===== RATINGS & REVIEWS =====
            # FIX: rating is already a number, not a dict
            rating = product.get('rating')
            if rating is not None:
                # Keepa returns rating * 10 (e.g., 45 = 4.5 stars)
                extracted['rating_average'] = rating / 10.0 if rating > 10 else rating
            
            review_count = product.get('reviewCount')
            if review_count is not None:
                extracted['review_count'] = review_count
            
            if product.get('reviews'):
                extracted['review_velocity'] = KeepaExtractor._calc_review_velocity(
                    product['reviews'], days=30
                )
            
            # ===== FEES =====
            # FIX: fbaFees can be dict or number
            fba_fees = product.get('fbaFees')
            if fba_fees is not None:
                if isinstance(fba_fees, dict):
                    # If it's a dict, try to get 'pickAndPackFee' or similar
                    pick_pack = fba_fees.get('pickAndPackFee', 0)
                    if isinstance(pick_pack, (int, float)):
                        extracted['fba_fees'] = pick_pack / 100
                    else:
                        # Try to get total or first numeric value
                        total = fba_fees.get('total', 0)
                        if isinstance(total, (int, float)):
                            extracted['fba_fees'] = total / 100
                elif isinstance(fba_fees, (int, float)):
                    extracted['fba_fees'] = fba_fees / 100
            
            # ===== SELLER COUNTS =====
            extracted['seller_count'] = product.get('offerCount', 0)
            extracted['fba_seller_count'] = product.get('fbaOfferCount', 0)
            
            # ===== DIMENSIONS (from Keepa, in cm/g) =====
            if product.get('packageLength'):
                extracted['package_length'] = product['packageLength'] / 10  # mm to cm
            if product.get('packageWidth'):
                extracted['package_width'] = product['packageWidth'] / 10
            if product.get('packageHeight'):
                extracted['package_height'] = product['packageHeight'] / 10
            if product.get('packageWeight'):
                extracted['package_weight'] = product['packageWeight']  # already in grams
            
            if product.get('itemWeight'):
                extracted['item_weight'] = product['itemWeight']
            
            # ===== PRODUCT AGE =====
            if product.get('listedSince'):
                # Keepa time = minutes since Jan 1, 2011
                base_date = datetime(2011, 1, 1)
                first_available = base_date + timedelta(minutes=product['listedSince'])
                extracted['first_available_date'] = first_available.date().isoformat()
                extracted['age_in_days'] = (datetime.now() - first_available).days
            
            # ===== HAZMAT =====
            extracted['is_hazmat'] = product.get('hazmatType', 0) > 0
            
            logger.debug(f"✅ Extracted {len(extracted)} fields from Keepa response")
            
        except Exception as e:
            logger.error(f"Error extracting Keepa fields: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return extracted
    
    # ===== HELPER METHODS =====
    
    @staticmethod
    def _calc_rank_avg(rank_history: List, days: int) -> Optional[int]:
        """Calculate average sales rank over last N days."""
        if not rank_history or len(rank_history) < 2:
            return None
        
        try:
            # Keepa time = minutes since Jan 1, 2011
            base_date = datetime(2011, 1, 1)
            now = datetime.now()
            cutoff_time = (now - timedelta(days=days) - base_date).total_seconds() / 60
            
            recent_ranks = []
            for i in range(0, len(rank_history) - 1, 2):
                timestamp = rank_history[i]
                rank = rank_history[i + 1]
                
                if timestamp >= cutoff_time and rank > 0:
                    recent_ranks.append(rank)
            
            if recent_ranks:
                return int(sum(recent_ranks) / len(recent_ranks))
        except Exception as e:
            logger.debug(f"Error calculating rank avg: {e}")
        
        return None
    
    @staticmethod
    def _calc_rank_drops(rank_history: List, days: int) -> Optional[int]:
        """Count significant rank improvements (sales)."""
        if not rank_history or len(rank_history) < 4:
            return None
        
        try:
            base_date = datetime(2011, 1, 1)
            now = datetime.now()
            cutoff_time = (now - timedelta(days=days) - base_date).total_seconds() / 60
            
            drops = 0
            for i in range(2, len(rank_history) - 1, 2):
                timestamp = rank_history[i]
                if timestamp < cutoff_time:
                    continue
                
                current_rank = rank_history[i + 1]
                prev_rank = rank_history[i - 1]
                
                # Drop of 10000+ in rank = likely a sale
                if prev_rank > 0 and current_rank > 0 and (prev_rank - current_rank) > 10000:
                    drops += 1
            
            return drops
        except Exception as e:
            logger.debug(f"Error calculating rank drops: {e}")
        
        return None
    
    @staticmethod
    def _calc_price_avg(price_history: List, days: int) -> Optional[float]:
        """Calculate average price over last N days."""
        if not price_history or len(price_history) < 2:
            return None
        
        try:
            base_date = datetime(2011, 1, 1)
            now = datetime.now()
            cutoff_time = (now - timedelta(days=days) - base_date).total_seconds() / 60
            
            recent_prices = []
            for i in range(0, len(price_history) - 1, 2):
                timestamp = price_history[i]
                price = price_history[i + 1]
                
                if timestamp >= cutoff_time and price >= 0:
                    recent_prices.append(price)
            
            if recent_prices:
                return round(sum(recent_prices) / len(recent_prices) / 100, 2)
        except Exception as e:
            logger.debug(f"Error calculating price avg: {e}")
        
        return None
    
    @staticmethod
    def _calc_oos_pct(availability_history: List, days: int) -> Optional[int]:
        """Calculate out-of-stock percentage."""
        if not availability_history or len(availability_history) < 4:
            return None
        
        try:
            base_date = datetime(2011, 1, 1)
            now = datetime.now()
            cutoff_time = (now - timedelta(days=days) - base_date).total_seconds() / 60
            
            total_minutes = 0
            oos_minutes = 0
            
            for i in range(2, len(availability_history) - 1, 2):
                timestamp = availability_history[i]
                if timestamp < cutoff_time:
                    continue
                
                duration = availability_history[i] - availability_history[i - 2]
                total_minutes += duration
                
                if availability_history[i - 1] > 0:  # 0 = in stock, >0 = OOS
                    oos_minutes += duration
            
            if total_minutes > 0:
                return int((oos_minutes / total_minutes) * 100)
        except Exception as e:
            logger.debug(f"Error calculating OOS percentage: {e}")
        
        return None
    
    @staticmethod
    def _calc_review_velocity(review_history: List, days: int) -> Optional[int]:
        """Calculate reviews per month."""
        if not review_history or len(review_history) < 2:
            return None
        
        try:
            base_date = datetime(2011, 1, 1)
            now = datetime.now()
            cutoff_time = (now - timedelta(days=days) - base_date).total_seconds() / 60
            
            recent_reviews = 0
            for i in range(0, len(review_history) - 1, 2):
                if review_history[i] >= cutoff_time:
                    recent_reviews += 1
            
            # Convert to per-month rate
            return int(recent_reviews * 30 / days)
        except Exception as e:
            logger.debug(f"Error calculating review velocity: {e}")
        
        return None

