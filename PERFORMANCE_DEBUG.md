# Performance Debugging Guide

## Quick Steps to Capture Performance Data

### 1. Browser DevTools Network Tab

1. Open your browser DevTools (F12 or Cmd+Option+I)
2. Go to **Network** tab
3. **Clear** the network log (trash icon)
4. **Check "Preserve log"** checkbox
5. Navigate to the Deal Feed page
6. Wait for it to load (or timeout)
7. **Right-click** in the Network tab → **Save all as HAR**
8. Share the HAR file

### 2. Backend Query Logging

I've added detailed logging. Check backend logs:

```bash
tail -f /tmp/backend.log | grep -E "deals|query|GET /deals"
```

### 3. Database Query Analysis

Run this in Supabase SQL Editor to see slow queries:

```sql
-- Enable query logging (if available)
-- Then check pg_stat_statements for slow queries

SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
WHERE query LIKE '%telegram_deals%'
   OR query LIKE '%analyses%'
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### 4. Frontend Performance

Add this to browser console on the Deal Feed page:

```javascript
// Performance timing
performance.mark('deals-page-start');

// After page loads
window.addEventListener('load', () => {
    performance.mark('deals-page-end');
    performance.measure('deals-page-load', 'deals-page-start', 'deals-page-end');
    
    const measure = performance.getEntriesByName('deals-page-load')[0];
    console.log('Page Load Time:', measure.duration, 'ms');
    
    // Get all API calls
    const apiCalls = performance.getEntriesByType('resource')
        .filter(r => r.name.includes('/api/'))
        .map(r => ({
            url: r.name,
            duration: r.duration,
            size: r.transferSize
        }));
    
    console.table(apiCalls);
});
```

### 5. API Response Times

Check the actual API response time:

```bash
# Time the deals endpoint
time curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8020/api/v1/deals?limit=50
```

