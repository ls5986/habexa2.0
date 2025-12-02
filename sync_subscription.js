/**
 * Script to sync subscription from browser console
 * 
 * Usage:
 * 1. Open your browser console (F12 or Cmd+Option+I)
 * 2. Copy and paste this entire script
 * 3. Or just run: syncSubscription()
 */

async function syncSubscription() {
  try {
    // Get auth token from localStorage
    const token = localStorage.getItem('auth_token');
    
    if (!token) {
      console.error('❌ Not logged in. Please log in first.');
      return;
    }
    
    console.log('🔄 Syncing subscription...');
    
    const response = await fetch('http://localhost:8020/api/v1/billing/sync', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    console.log('✅ Subscription synced successfully!');
    console.log('📊 Subscription data:', data);
    
    if (data.tier && data.tier !== 'free') {
      console.log(`🎉 You're on the ${data.tier} plan!`);
    } else {
      console.log('⚠️  You appear to be on the free plan. Check Stripe for your subscription.');
    }
    
    return data;
  } catch (error) {
    console.error('❌ Failed to sync subscription:', error.message);
    console.error('Full error:', error);
    throw error;
  }
}

// Auto-run if in browser console
if (typeof window !== 'undefined') {
  console.log('📝 Run syncSubscription() to sync your subscription');
  console.log('   Or just call: await syncSubscription()');
}

