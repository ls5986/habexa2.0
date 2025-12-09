# P1 TESTING SCRIPTS - Complete Guide

**Priority:** P1 - HIGH  
**Estimated Time:** 40 minutes total  
**Status:** ⏳ Ready to Execute

---

## OVERVIEW

These scripts test the HIGH PRIORITY (P1) items identified in the production audit:

1. ✅ **Orders Workflow** - End-to-end manual testing (15 min)
2. ✅ **Performance Benchmarks** - API and frontend performance (15 min)
3. ✅ **Data Integrity** - Database consistency checks (10 min)

---

## QUICK START

### 1. Orders Workflow Test

**File:** `tests/p1_orders_workflow_test.md`

**How to Run:**
1. Open the markdown file
2. Follow each step manually
3. Check off items as you complete them
4. Document any failures

**Time:** 15 minutes

---

### 2. Performance Benchmarks

**Files:**
- `tests/p1_performance_test.py` - API performance
- `tests/p1_frontend_performance_test.js` - Frontend performance

**How to Run API Test:**
```bash
# Install dependencies
pip install requests

# Set token (get from browser localStorage after login)
export HABEXA_TOKEN="your_jwt_token_here"

# Run test
python tests/p1_performance_test.py
```

**How to Run Frontend Test:**
1. Open https://habexa.onrender.com
2. Login
3. Open browser console (F12)
4. Copy contents of `tests/p1_frontend_performance_test.js`
5. Paste and press Enter

**Time:** 15 minutes

---

### 3. Data Integrity Checks

**File:** `tests/p1_data_integrity_check.sql`

**How to Run:**
1. Open Supabase Dashboard
2. Go to SQL Editor
3. Copy entire SQL file
4. Paste and run
5. Review results

**Time:** 10 minutes

---

## EXPECTED RESULTS

### Orders Workflow
- ✅ Order created successfully
- ✅ All products in order
- ✅ Order total calculated correctly
- ✅ Status updates work
- ✅ Email sent to supplier

### Performance
- ✅ GET /products < 500ms
- ✅ GET /stats < 20ms
- ✅ Dashboard < 2 seconds
- ✅ Products page < 3 seconds

### Data Integrity
- ✅ Zero orphaned products
- ✅ Zero calculation errors
- ✅ Zero foreign key violations
- ✅ All indexes being used

---

## INTERPRETING RESULTS

### ✅ PASS
All tests pass → **Production Ready**

### ❌ FAIL
Any test fails → **Fix Issues Before Launch**

Document failures:
1. Which test failed
2. What the expected result was
3. What the actual result was
4. Steps to reproduce

---

## FIXING ISSUES

### If Orders Workflow Fails:
1. Check backend logs for errors
2. Verify database records
3. Test individual endpoints
4. Check email service configuration

### If Performance Fails:
1. Check database query performance
2. Verify indexes are being used
3. Review API response times
4. Optimize slow endpoints

### If Data Integrity Fails:
1. Run SQL fixes for corrupted data
2. Fix calculation logic bugs
3. Add missing indexes
4. Clean up duplicate records

---

## TEST EXECUTION CHECKLIST

- [ ] **Orders Workflow** (15 min)
  - [ ] Create order from products
  - [ ] View order details
  - [ ] Edit quantities
  - [ ] Remove line items
  - [ ] Send to supplier
  - [ ] Update status
  - [ ] Verify database records

- [ ] **API Performance** (5 min)
  - [ ] Run Python script
  - [ ] Review results
  - [ ] Document any failures

- [ ] **Frontend Performance** (5 min)
  - [ ] Run JavaScript in browser
  - [ ] Review results
  - [ ] Document any failures

- [ ] **Database Performance** (5 min)
  - [ ] Run SQL EXPLAIN ANALYZE queries
  - [ ] Check index usage
  - [ ] Document any slow queries

- [ ] **Data Integrity** (10 min)
  - [ ] Run all SQL checks
  - [ ] Review results
  - [ ] Fix any issues found

---

## AFTER TESTING

1. **Document Results**
   - Save test results
   - Note any failures
   - Create issues for bugs found

2. **Fix Issues**
   - Prioritize critical bugs
   - Fix calculation errors
   - Optimize slow endpoints

3. **Re-test**
   - Re-run failed tests
   - Verify fixes work
   - Update production readiness score

---

## PRODUCTION READINESS SCORE

**Current Score:** 82/120 (68%)

**After P1 Tests Pass:**
- Orders: +8 points → 90/120 (75%)
- Performance: +6 points → 96/120 (80%)
- Data Integrity: +4 points → 100/120 (83%)

**Target:** ≥ 100/120 (83%) for production launch

---

## SUPPORT

If you encounter issues:
1. Check test logs
2. Review error messages
3. Verify environment setup
4. Check database connectivity

---

**Last Updated:** 2025-12-06  
**Version:** 1.0

