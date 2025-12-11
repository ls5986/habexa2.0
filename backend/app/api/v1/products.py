# Add this new endpoint after the select-asin endpoint

@router.patch("/{product_id}/fields")
async def update_product_fields(
    product_id: str,
    request: Dict[str, Any] = Body(...),
    current_user = Depends(get_current_user)
):
    """
    Update product fields (ASIN, UPC, title, etc.) and product_source fields (buy_cost, pack_size, etc.).
    
    Body can include:
    - Product fields: asin, upc, title, brand, supplier_title
    - Product source fields: buy_cost, moq, pack_size, wholesale_cost
    """
    user_id = str(current_user.id)
    
    try:
        # Verify ownership
        product_check = supabase.table("products")\
            .select("id, user_id")\
            .eq("id", product_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not product_check.data:
            raise HTTPException(404, "Product not found")
        
        # Separate product fields from product_source fields
        product_fields = {}
        product_source_fields = {}
        
        # Product table fields
        product_allowed = ['asin', 'upc', 'title', 'brand', 'supplier_title', 'image_url']
        for field in product_allowed:
            if field in request:
                product_fields[field] = request[field]
        
        # Product source fields (deal fields)
        source_allowed = ['buy_cost', 'moq', 'pack_size', 'wholesale_cost', 'percent_off', 'promo_qty']
        for field in source_allowed:
            if field in request:
                product_source_fields[field] = request[field]
        
        # Validate ASIN if provided
        if 'asin' in product_fields:
            asin = product_fields['asin'].strip().upper()
            if asin.startswith('PENDING_') or asin.startswith('Unknown'):
                raise HTTPException(400, "Invalid ASIN format")
            if len(asin) != 10:
                raise HTTPException(400, "ASIN must be 10 characters")
            product_fields['asin'] = asin
            product_fields['asin_status'] = 'found' if asin else None
        
        # Validate UPC if provided
        if 'upc' in product_fields:
            upc = str(product_fields['upc']).strip()
            # Remove leading/trailing zeros if user wants to fix it
            if upc:
                product_fields['upc'] = upc
        
        # Update product if there are product fields
        if product_fields:
            product_fields['updated_at'] = datetime.utcnow().isoformat()
            supabase.table("products")\
                .update(product_fields)\
                .eq("id", product_id)\
                .eq("user_id", user_id)\
                .execute()
        
        # Update product_source if there are source fields
        if product_source_fields:
            product_source_fields['updated_at'] = datetime.utcnow().isoformat()
            supabase.table("product_sources")\
                .update(product_source_fields)\
                .eq("product_id", product_id)\
                .execute()
        
        # If ASIN was updated, trigger API data fetch
        if 'asin' in product_fields and product_fields['asin']:
            try:
                from app.services.api_batch_fetcher import fetch_api_data_for_asins
                await fetch_api_data_for_asins(
                    asins=[product_fields['asin']],
                    user_id=user_id,
                    force_refetch=True
                )
            except Exception as e:
                logger.warning(f"Could not fetch API data after ASIN update: {e}")
        
        return {
            "success": True,
            "message": "Product fields updated successfully",
            "product_id": product_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product fields: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to update product: {str(e)}")
