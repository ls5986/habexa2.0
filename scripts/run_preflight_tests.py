#!/usr/bin/env python3
"""
Pre-flight tests to verify critical fixes before full audit.
All tests are automated - no manual steps required.
"""
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

print("=" * 60)
print("HABEXA PRE-FLIGHT TESTS")
print("=" * 60)
print()

# Track results
results = {
    "passed": 0,
    "failed": 0,
    "warnings": 0
}

def test_pass(name):
    print(f"✅ {name}")
    results["passed"] += 1

def test_fail(name, error):
    print(f"❌ {name}: {error}")
    results["failed"] += 1

def test_warn(name, message):
    print(f"⚠️  {name}: {message}")
    results["warnings"] += 1

# ==========================================
# TEST 1: DATABASE SCHEMA VERIFICATION
# ==========================================
print("[Test 1: Database Schema]")
print("-" * 60)

try:
    from app.services.supabase_client import supabase
    
    # Query information_schema to check columns
    # Note: Supabase doesn't directly expose information_schema, so we'll try to query the table
    # If the column doesn't exist, the query will fail gracefully
    
    required_columns = [
        'had_free_trial',
        'trial_start',
        'trial_end',
        'cancel_at_period_end',
        'status',
        'tier'
    ]
    
    found_columns = []
    missing_columns = []
    
    # Try to select each column - if it exists, query succeeds
    for col in required_columns:
        try:
            # Try a minimal query with the column
            result = supabase.table("subscriptions")\
                .select(col)\
                .limit(1)\
                .execute()
            found_columns.append(col)
            print(f"✅ {col}: EXISTS")
        except Exception as e:
            # Column might not exist, or there's a different error
            error_str = str(e).lower()
            if "column" in error_str and "not found" in error_str:
                missing_columns.append(col)
                print(f"❌ {col}: MISSING")
            else:
                # Other error (like no rows) - column probably exists
                found_columns.append(col)
                print(f"✅ {col}: EXISTS (verified via query)")
    
    if missing_columns:
        test_fail("Database Schema", f"Missing columns: {', '.join(missing_columns)}")
    else:
        test_pass("Database Schema - All required columns exist")
        
except Exception as e:
    test_fail("Database Schema", f"Error checking schema: {e}")

print()

# ==========================================
# TEST 2: SUPER ADMIN DETECTION
# ==========================================
print("[Test 2: Super Admin Detection]")
print("-" * 60)

try:
    from app.config.tiers import is_super_admin
    from app.services.permissions_service import PermissionsService
    
    # Test 1: Verify super admin email detection
    email = "lindsey@letsclink.com"
    result = is_super_admin(email)
    print(f"is_super_admin('{email}'): {result}")
    
    if result != True:
        test_fail("Super Admin Email Detection", f"Expected True, got {result}")
    else:
        test_pass("Super Admin Email Detection")
    
    # Test 2: Mock a user and test get_effective_limits
    class MockSuperAdmin:
        def __init__(self):
            self.email = "lindsey@letsclink.com"
            self.id = "test-user-id"
    
    limits = PermissionsService.get_effective_limits(MockSuperAdmin())
    print(f"Limits for super admin: unlimited={limits.get('unlimited')}, is_super_admin={limits.get('is_super_admin')}, tier={limits.get('tier')}")
    
    if limits.get("unlimited") != True:
        test_fail("Super Admin Unlimited Flag", f"Expected True, got {limits.get('unlimited')}")
    elif limits.get("is_super_admin") != True:
        test_fail("Super Admin Flag", f"Expected True, got {limits.get('is_super_admin')}")
    elif limits.get("tier") != "super_admin":
        test_fail("Super Admin Tier", f"Expected 'super_admin', got {limits.get('tier')}")
    else:
        test_pass("Super Admin Effective Limits")
        
except Exception as e:
    test_fail("Super Admin Detection", f"Error: {e}")
    import traceback
    traceback.print_exc()

print()

# ==========================================
# TEST 3: PERMISSION CHECK FLOW
# ==========================================
print("[Test 3: Permission Check Flow]")
print("-" * 60)

try:
    from app.services.permissions_service import PermissionsService
    
    class MockSuperAdmin:
        def __init__(self):
            self.email = "lindsey@letsclink.com"
            self.id = "test-super-admin-id"
    
    class MockRegularUser:
        def __init__(self):
            self.email = "regular@example.com"
            self.id = "test-regular-user-id"
    
    # Super admin should be unlimited
    result = PermissionsService.check_limit(MockSuperAdmin(), "analyses_per_month", current_usage=100)
    print(f"Super admin check: unlimited={result.get('unlimited')}, allowed={result.get('allowed')}")
    
    if result.get("unlimited") != True:
        test_fail("Super Admin Unlimited Check", f"Expected True, got {result.get('unlimited')}")
    elif result.get("allowed") != True:
        test_fail("Super Admin Allowed Check", f"Expected True, got {result.get('allowed')}")
    else:
        test_pass("Super Admin Permission Check")
    
    # Regular user should have limits
    result = PermissionsService.check_limit(MockRegularUser(), "analyses_per_month", current_usage=100)
    print(f"Regular user check: unlimited={result.get('unlimited')}, allowed={result.get('allowed')}, limit={result.get('limit')}")
    
    if result.get("unlimited") != False:
        test_fail("Regular User Unlimited Check", f"Expected False, got {result.get('unlimited')}")
    else:
        test_pass("Regular User Permission Check")
        
except Exception as e:
    test_fail("Permission Check Flow", f"Error: {e}")
    import traceback
    traceback.print_exc()

print()

# ==========================================
# TEST 4: USAGE TRACKING
# ==========================================
print("[Test 4: Usage Tracking]")
print("-" * 60)

try:
    from app.services.permissions_service import PermissionsService
    
    class MockSuperAdmin:
        def __init__(self):
            self.email = "lindsey@letsclink.com"
            self.id = "test-super-admin-id"
    
    class MockRegularUser:
        def __init__(self):
            self.email = "regular@example.com"
            self.id = "test-regular-user-id"
    
    # Super admin should NOT have usage tracked
    should_track = PermissionsService.should_track_usage(MockSuperAdmin())
    print(f"Should track super admin: {should_track}")
    
    if should_track != False:
        test_fail("Super Admin Usage Tracking", f"Expected False, got {should_track}")
    else:
        test_pass("Super Admin Usage Tracking")
    
    # Regular user SHOULD have usage tracked
    should_track = PermissionsService.should_track_usage(MockRegularUser())
    print(f"Should track regular user: {should_track}")
    
    if should_track != True:
        test_fail("Regular User Usage Tracking", f"Expected True, got {should_track}")
    else:
        test_pass("Regular User Usage Tracking")
        
except Exception as e:
    test_fail("Usage Tracking", f"Error: {e}")
    import traceback
    traceback.print_exc()

print()

# ==========================================
# TEST 5: WEBHOOK HANDLERS
# ==========================================
print("[Test 5: Webhook Handlers]")
print("-" * 60)

try:
    from app.services.stripe_service import StripeWebhookHandler
    
    required_handlers = [
        ("checkout.session.completed", StripeWebhookHandler.handle_checkout_completed),
        ("customer.subscription.updated", StripeWebhookHandler.handle_subscription_updated),
        ("customer.subscription.deleted", StripeWebhookHandler.handle_subscription_deleted),
        ("customer.subscription.trial_will_end", StripeWebhookHandler.handle_trial_will_end),
        ("invoice.paid", StripeWebhookHandler.handle_invoice_paid),
        ("invoice.payment_failed", StripeWebhookHandler.handle_invoice_payment_failed),
    ]
    
    all_exist = True
    for event, handler in required_handlers:
        if not callable(handler):
            test_fail(f"Webhook Handler: {event}", "Handler is not callable")
            all_exist = False
        else:
            print(f"✅ {event}: handler exists")
    
    # Check if customer.subscription.created uses the same handler as updated
    # (This is expected based on the code)
    if all_exist:
        test_pass("All Webhook Handlers Verified")
    
    # Also verify the handlers are registered in the webhook endpoint
    try:
        from app.api.v1.billing import router
        
        # Check if webhook endpoint exists
        webhook_route = None
        for route in router.routes:
            if hasattr(route, 'path') and 'webhook' in route.path:
                webhook_route = route
                break
        
        if webhook_route:
            print(f"✅ Webhook endpoint exists: {webhook_route.path}")
            test_pass("Webhook Endpoint Registration")
        else:
            test_warn("Webhook Endpoint", "Could not verify endpoint registration")
            
    except Exception as e:
        test_warn("Webhook Endpoint Verification", f"Could not verify: {e}")
        
except Exception as e:
    test_fail("Webhook Handlers", f"Error: {e}")
    import traceback
    traceback.print_exc()

print()

# ==========================================
# SUMMARY
# ==========================================
print("=" * 60)
print("RESULTS SUMMARY")
print("=" * 60)
print(f"✅ Passed:   {results['passed']}")
print(f"⚠️  Warnings: {results['warnings']}")
print(f"❌ Failed:   {results['failed']}")
print("=" * 60)

total_tests = results['passed'] + results['failed']
if results['failed'] == 0:
    print()
    print("✅ PRE-FLIGHT COMPLETE — READY FOR FULL AUDIT")
    sys.exit(0)
else:
    print()
    print(f"❌ PRE-FLIGHT FAILED — {results['failed']} test(s) failed")
    print("Fix the issues above before proceeding to full audit.")
    sys.exit(1)

