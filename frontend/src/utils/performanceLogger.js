/**
 * Performance logging utility for debugging slow page loads
 */
export function logPagePerformance() {
  if (typeof window === 'undefined') return;
  
  // Mark start
  performance.mark('page-start');
  
  // Log when page is fully loaded
  window.addEventListener('load', () => {
    performance.mark('page-end');
    performance.measure('page-load', 'page-start', 'page-end');
    
    const measure = performance.getEntriesByName('page-load')[0];
    console.log('📊 PAGE LOAD TIME:', measure.duration.toFixed(0), 'ms');
    
    // Get all API calls
    const apiCalls = performance.getEntriesByType('resource')
      .filter(r => r.name.includes('/api/'))
      .map(r => ({
        url: r.name.split('/api/')[1] || r.name,
        duration: Math.round(r.duration),
        size: r.transferSize ? `${(r.transferSize / 1024).toFixed(1)} KB` : 'N/A',
        cached: r.transferSize === 0 ? '✅' : '❌'
      }));
    
    if (apiCalls.length > 0) {
      console.table(apiCalls);
      
      const totalTime = apiCalls.reduce((sum, call) => sum + call.duration, 0);
      const slowCalls = apiCalls.filter(call => call.duration > 500);
      
      console.log('📈 API CALLS SUMMARY:');
      console.log(`  Total calls: ${apiCalls.length}`);
      console.log(`  Total time: ${totalTime}ms`);
      console.log(`  Average: ${Math.round(totalTime / apiCalls.length)}ms`);
      console.log(`  Slow calls (>500ms): ${slowCalls.length}`);
      
      if (slowCalls.length > 0) {
        console.warn('⚠️  SLOW API CALLS:');
        slowCalls.forEach(call => {
          console.warn(`  - ${call.url}: ${call.duration}ms`);
        });
      }
    }
    
    // Navigation timing
    const navTiming = performance.getEntriesByType('navigation')[0];
    if (navTiming) {
      console.log('🌐 NAVIGATION TIMING:');
      console.log(`  DNS: ${navTiming.domainLookupEnd - navTiming.domainLookupStart}ms`);
      console.log(`  Connect: ${navTiming.connectEnd - navTiming.connectStart}ms`);
      console.log(`  Request: ${navTiming.responseStart - navTiming.requestStart}ms`);
      console.log(`  Response: ${navTiming.responseEnd - navTiming.responseStart}ms`);
      console.log(`  DOM Load: ${navTiming.domContentLoadedEventEnd - navTiming.domContentLoadedEventStart}ms`);
      console.log(`  Page Load: ${navTiming.loadEventEnd - navTiming.loadEventStart}ms`);
    }
  });
}

/**
 * Log API call performance
 */
export function logApiCall(url, startTime, endTime, success = true) {
  const duration = endTime - startTime;
  const emoji = success ? '✅' : '❌';
  
  if (duration > 500) {
    console.warn(`${emoji} SLOW API: ${url} took ${duration.toFixed(0)}ms`);
  } else {
    console.log(`${emoji} API: ${url} took ${duration.toFixed(0)}ms`);
  }
  
  return duration;
}

/**
 * Export performance data as JSON
 */
export function exportPerformanceData() {
  const apiCalls = performance.getEntriesByType('resource')
    .filter(r => r.name.includes('/api/'))
    .map(r => ({
      url: r.name,
      duration: r.duration,
      size: r.transferSize,
      cached: r.transferSize === 0,
      startTime: r.startTime,
      endTime: r.startTime + r.duration
    }));
  
  const navTiming = performance.getEntriesByType('navigation')[0];
  
  return {
    timestamp: new Date().toISOString(),
    apiCalls,
    navigation: navTiming ? {
      dns: navTiming.domainLookupEnd - navTiming.domainLookupStart,
      connect: navTiming.connectEnd - navTiming.connectStart,
      request: navTiming.responseStart - navTiming.requestStart,
      response: navTiming.responseEnd - navTiming.responseStart,
      domLoad: navTiming.domContentLoadedEventEnd - navTiming.domContentLoadedEventStart,
      pageLoad: navTiming.loadEventEnd - navTiming.loadEventStart,
      total: navTiming.loadEventEnd - navTiming.fetchStart
    } : null
  };
}

