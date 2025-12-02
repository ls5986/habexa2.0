/**
 * PERFORMANCE CAPTURE SCRIPT
 * 
 * Copy and paste this into your browser console on the Deal Feed page
 * Then navigate to the page and wait for it to load
 * 
 * This will capture all performance data and log it to console
 */

(function() {
  console.log('🔍 Performance monitoring started...');
  
  // Mark start
  performance.mark('page-load-start');
  
  // Wait for page to fully load
  window.addEventListener('load', () => {
    setTimeout(() => {
      // Get all API calls
      const apiCalls = performance.getEntriesByType('resource')
        .filter(r => r.name.includes('/api/'))
        .map(r => {
          const url = r.name.split('/api/')[1] || r.name;
          return {
            endpoint: url.split('?')[0],
            fullUrl: url,
            duration: Math.round(r.duration),
            size: r.transferSize ? `${(r.transferSize / 1024).toFixed(1)} KB` : '0 KB',
            cached: r.transferSize === 0,
            startTime: Math.round(r.startTime),
            endTime: Math.round(r.startTime + r.duration)
          };
        });
      
      // Navigation timing
      const navTiming = performance.getEntriesByType('navigation')[0];
      
      // Get all measures
      const measures = performance.getEntriesByType('measure');
      
      // Build report
      const report = {
        timestamp: new Date().toISOString(),
        url: window.location.href,
        apiCalls: apiCalls,
        summary: {
          totalApiCalls: apiCalls.length,
          totalApiTime: apiCalls.reduce((sum, call) => sum + call.duration, 0),
          averageApiTime: apiCalls.length > 0 ? Math.round(apiCalls.reduce((sum, call) => sum + call.duration, 0) / apiCalls.length) : 0,
          slowestCall: apiCalls.length > 0 ? apiCalls.reduce((max, call) => call.duration > max.duration ? call : max, apiCalls[0]) : null,
          slowCalls: apiCalls.filter(call => call.duration > 500).length
        },
        navigation: navTiming ? {
          dns: Math.round(navTiming.domainLookupEnd - navTiming.domainLookupStart),
          connect: Math.round(navTiming.connectEnd - navTiming.connectStart),
          request: Math.round(navTiming.responseStart - navTiming.requestStart),
          response: Math.round(navTiming.responseEnd - navTiming.responseStart),
          domLoad: Math.round(navTiming.domContentLoadedEventEnd - navTiming.domContentLoadedEventStart),
          pageLoad: Math.round(navTiming.loadEventEnd - navTiming.loadEventStart),
          total: Math.round(navTiming.loadEventEnd - navTiming.fetchStart)
        } : null,
        measures: measures.map(m => ({
          name: m.name,
          duration: Math.round(m.duration)
        }))
      };
      
      // Log to console
      console.log('📊 PERFORMANCE REPORT:');
      console.log('====================');
      console.log('API Calls:', report.summary.totalApiCalls);
      console.log('Total API Time:', report.summary.totalApiTime + 'ms');
      console.log('Average API Time:', report.summary.averageApiTime + 'ms');
      console.log('Slow Calls (>500ms):', report.summary.slowCalls);
      
      if (report.summary.slowestCall) {
        console.log('🐌 Slowest Call:', report.summary.slowestCall.endpoint, '-', report.summary.slowestCall.duration + 'ms');
      }
      
      console.log('\n📋 All API Calls:');
      console.table(apiCalls);
      
      if (report.navigation) {
        console.log('\n🌐 Navigation Timing:');
        console.log('  DNS:', report.navigation.dns + 'ms');
        console.log('  Connect:', report.navigation.connect + 'ms');
        console.log('  Request:', report.navigation.request + 'ms');
        console.log('  Response:', report.navigation.response + 'ms');
        console.log('  DOM Load:', report.navigation.domLoad + 'ms');
        console.log('  Page Load:', report.navigation.pageLoad + 'ms');
        console.log('  TOTAL:', report.navigation.total + 'ms');
      }
      
      // Export as JSON
      console.log('\n💾 Copy this JSON to share:');
      console.log(JSON.stringify(report, null, 2));
      
      // Store in window for easy access
      window.performanceReport = report;
      console.log('\n✅ Report saved to window.performanceReport');
      console.log('   Run: copy(JSON.stringify(window.performanceReport, null, 2))');
      
    }, 1000); // Wait 1 second after load
  });
})();

