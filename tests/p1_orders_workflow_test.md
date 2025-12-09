# P1 TEST: ORDERS WORKFLOW END-TO-END

**Priority:** P1 - HIGH  
**Estimated Time:** 15 minutes  
**Status:** ⏳ Pending

---

## TEST ENVIRONMENT

- **URL:** https://habexa.onrender.com
- **Test User:** lindsey@letsclink.com
- **Date:** _______________
- **Tester:** _______________

---

## PART 1: CREATE ORDER FROM PRODUCTS

### Step 1: Login
- [ ] Navigate to: https://habexa.onrender.com/login
- [ ] Enter email: lindsey@letsclink.com
- [ ] Enter password
- [ ] Click "Sign In"
- [ ] Verify redirect to dashboard

**Result:** ✅ PASS / ❌ FAIL  
**Notes:** _________________________________

---

### Step 2: Navigate to Products
- [ ] Click "Products" in navigation
- [ ] Verify URL: /products
- [ ] Verify products list loads

**Result:** ✅ PASS / ❌ FAIL  
**Notes:** _________________________________

---

### Step 3: Select Products
- [ ] Find 3 products with SAME supplier (e.g., KEHE)
- [ ] Click checkboxes next to 3 products
- [ ] Verify "3 selected" shown in header
- [ ] Verify selected products highlighted

**Selected Products:**
1. Product ID: ___________ Supplier: ___________
2. Product ID: ___________ Supplier: ___________
3. Product ID: ___________ Supplier: ___________

**Result:** ✅ PASS / ❌ FAIL  
**Notes:** _________________________________

---

### Step 4: Bulk Action → Create Order
- [ ] Click "Actions" dropdown (or bulk actions button)
- [ ] Click "Move to Orders" or "Create Order"
- [ ] Verify success message/toast shown
- [ ] Verify redirected to /orders

**Result:** ✅ PASS / ❌ FAIL  
**Notes:** _________________________________

---

### Step 5: Verify Order Created
- [ ] Check orders list shows new order
- [ ] Verify supplier name correct: ___________
- [ ] Verify order status = "Draft"
- [ ] Verify order total > $0: $___________
- [ ] Verify created date shown

**Order ID:** ___________  
**Result:** ✅ PASS / ❌ FAIL  
**Notes:** _________________________________

---

## PART 2: VIEW ORDER DETAILS

### Step 6: Click on Order
- [ ] Click order from list
- [ ] Verify redirected to /orders/{id}
- [ ] Verify order details page loads

**Result:** ✅ PASS / ❌ FAIL  
**Notes:** _________________________________

---

### Step 7: Verify Order Details Page

**Order Header:**
- [ ] Supplier name displayed: ___________
- [ ] Status badge shown ("Draft")
- [ ] Created date shown: ___________
- [ ] Total amount shown: $___________

**Line Items Table:**
- [ ] All 3 products listed
- [ ] Product names shown
- [ ] Quantity shown (default 1)
- [ ] Unit cost shown
- [ ] Total cost shown (quantity × unit cost)
- [ ] Remove buttons visible

**Line Items:**
1. Product: ___________ Qty: ___ Cost: $___ Total: $___
2. Product: ___________ Qty: ___ Cost: $___ Total: $___
3. Product: ___________ Qty: ___ Cost: $___ Total: $___

**Result:** ✅ PASS / ❌ FAIL  
**Notes:** _________________________________

---

## PART 3: EDIT ORDER

### Step 8: Change Quantity
- [ ] Change quantity of first product to 5
- [ ] Verify total updates immediately
- [ ] Verify order total recalculates
- [ ] Verify new total: $___________

**Before:** Qty: ___ Total: $___  
**After:** Qty: 5 Total: $___

**Result:** ✅ PASS / ❌ FAIL  
**Notes:** _________________________________

---

### Step 9: Remove Line Item
- [ ] Click remove/delete on one product
- [ ] Verify confirmation dialog appears
- [ ] Confirm removal
- [ ] Verify product removed from list
- [ ] Verify order total updated: $___________

**Removed Product:** ___________  
**Result:** ✅ PASS / ❌ FAIL  
**Notes:** _________________________________

---

## PART 4: SEND ORDER

### Step 10: Send to Supplier
- [ ] Click "Send to Supplier" button
- [ ] Verify confirmation dialog appears
- [ ] Confirm send
- [ ] Verify status changes to "Sent"
- [ ] Verify sent timestamp shown: ___________
- [ ] Verify button changes to "Resend"
- [ ] Check email inbox for order email

**Email Sent:** ✅ YES / ❌ NO  
**Email To:** ___________  
**Result:** ✅ PASS / ❌ FAIL  
**Notes:** _________________________________

---

## PART 5: TRACK STATUS

### Step 11: Update Order Status
- [ ] Click status dropdown/button
- [ ] Change to "Confirmed"
- [ ] Verify status updates in UI
- [ ] Change to "Delivered"
- [ ] Verify final status shown

**Status History:**
- Draft → ___________
- Sent → ___________
- Confirmed → ___________
- Delivered → ___________

**Result:** ✅ PASS / ❌ FAIL  
**Notes:** _________________________________

---

## PART 6: DATABASE VERIFICATION

### Run in Supabase SQL Editor

```sql
-- Replace YOUR_USER_ID with actual user ID
-- Replace ORDER_ID with order ID from Step 5

-- 1. Check order was created
SELECT * FROM orders 
WHERE user_id = 'YOUR_USER_ID' 
ORDER BY created_at DESC 
LIMIT 1;

-- 2. Check line items exist
SELECT oi.*, p.title 
FROM order_items oi
JOIN products p ON oi.product_id = p.id
WHERE oi.order_id = 'ORDER_ID_FROM_ABOVE';

-- 3. Check order total matches line items
SELECT 
  o.id,
  o.total_amount as order_total,
  SUM(oi.quantity * oi.unit_cost) as calculated_total,
  ABS(o.total_amount - SUM(oi.quantity * oi.unit_cost)) as difference
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
WHERE o.id = 'ORDER_ID_FROM_ABOVE'
GROUP BY o.id, o.total_amount;

-- Difference should be < $0.01
```

**Database Results:**
- [ ] Order exists in database
- [ ] Line items exist (3 items)
- [ ] Order total matches calculated total (difference < $0.01)

**Order ID from DB:** ___________  
**Calculated Total:** $___________  
**Order Total:** $___________  
**Difference:** $___________

**Result:** ✅ PASS / ❌ FAIL  
**Notes:** _________________________________

---

## FINAL RESULTS

### Test Summary

| Test Section | Status | Notes |
|-------------|--------|-------|
| Create Order | ⬜ PASS / ⬜ FAIL | |
| View Details | ⬜ PASS / ⬜ FAIL | |
| Edit Order | ⬜ PASS / ⬜ FAIL | |
| Send Order | ⬜ PASS / ⬜ FAIL | |
| Track Status | ⬜ PASS / ⬜ FAIL | |
| Database Check | ⬜ PASS / ⬜ FAIL | |

### Overall Result

**✅ PASS** - All tests passed, Orders workflow is production-ready  
**❌ FAIL** - Issues found, see notes above

### Issues Found

1. _________________________________
2. _________________________________
3. _________________________________

### Recommendations

_________________________________
_________________________________
_________________________________

---

**Test Completed:** _______________  
**Tester Signature:** _______________

