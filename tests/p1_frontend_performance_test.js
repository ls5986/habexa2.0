/**
 * P1 Frontend Performance Test
 * Run this in browser console on production site
 * 
 * Usage:
 *   1. Open https://habexa.onrender.com
 *   2. Login
 *   3. Open browser console (F12)
 *   4. Copy and paste this entire script
 *   5. Press Enter
 */

async function measurePageLoad(url, name) {
    console.log(`\n📊 Testing: ${name}`);
    console.log(`   URL: ${url}`);
    
    const startTime = performance.now();
    
    // Navigate to page
    window.location.href = url;
    
    // Wait for page load
    await new Promise(resolve => {
        if (document.readyState === 'complete') {
            resolve();
        } else {
            window.addEventListener('load', resolve, { once: true });
        }
    });
    
    const endTime = performance.now();
    const loadTime = endTime - startTime;
    
    // Get performance metrics
    const perfData = performance.getEntriesByType('navigation')[0];
    const paintMetrics = performance.getEntriesByType('paint');
    
    const firstPaint = paintMetrics.find(m => m.name === 'first-paint')?.startTime || 0;
    const firstContentfulPaint = paintMetrics.find(m => m.name === 'first-contentful-paint')?.startTime || 0;
    
    console.log(`\n   Results:`);
    console.log(`   Total Load Time: ${loadTime.toFixed(0)}ms`);
    console.log(`   DOM Content Loaded: ${perfData.domContentLoadedEventEnd.toFixed(0)}ms`);
    console.log(`   First Paint: ${firstPaint.toFixed(0)}ms`);
    console.log(`   First Contentful Paint: ${firstContentfulPaint.toFixed(0)}ms`);
    console.log(`   Response Start: ${perfData.responseStart.toFixed(0)}ms`);
    
    return {
        total: loadTime,
        domContentLoaded: perfData.domContentLoadedEventEnd,
        firstPaint: firstPaint,
        firstContentfulPaint: firstContentfulPaint
    };
}

async function runFrontendBenchmarks() {
    console.log("=".repeat(60));
    console.log("FRONTEND PERFORMANCE BENCHMARKS");
    console.log("=".repeat(60));
    
    const results = {};
    const baseUrl = window.location.origin;
    
    // Test Dashboard
    console.log("\n⏳ Loading Dashboard...");
    results.dashboard = await measurePageLoad(`${baseUrl}/dashboard`, 'Dashboard');
    
    // Wait a bit before next test
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Test Products
    console.log("\n⏳ Loading Products...");
    results.products = await measurePageLoad(`${baseUrl}/products`, 'Products');
    
    // Wait a bit before next test
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Test Analyze
    console.log("\n⏳ Loading Analyze...");
    results.analyze = await measurePageLoad(`${baseUrl}/analyze`, 'Analyze');
    
    // Print summary
    console.log("\n" + "=".repeat(60));
    console.log("BENCHMARK RESULTS SUMMARY");
    console.log("=".repeat(60));
    
    const targets = {
        dashboard: 2000,
        products: 3000,
        analyze: 2000
    };
    
    let passed = 0;
    let total = 0;
    
    for (const [page, metrics] of Object.entries(results)) {
        const target = targets[page];
        const passedTest = metrics.total < target;
        const status = passedTest ? "✅ PASS" : "❌ FAIL";
        
        console.log(`\n${page.toUpperCase()}:`);
        console.log(`  Total Load: ${metrics.total.toFixed(0)}ms`);
        console.log(`  Target: <${target}ms`);
        console.log(`  Status: ${status}`);
        console.log(`  First Paint: ${metrics.firstPaint.toFixed(0)}ms`);
        console.log(`  FCP: ${metrics.firstContentfulPaint.toFixed(0)}ms`);
        
        if (passedTest) {
            passed++;
        }
        total++;
    }
    
    console.log("\n" + "=".repeat(60));
    console.log(`Overall: ${passed}/${total} tests passed (${(passed/total*100).toFixed(0)}%)`);
    console.log("=".repeat(60));
    
    if (passed === total) {
        console.log("\n✅ ALL FRONTEND PERFORMANCE TESTS PASSED!");
    } else {
        console.log(`\n❌ ${total - passed} FRONTEND PERFORMANCE TEST(S) FAILED`);
        console.log("   Review results above and optimize slow pages");
    }
    
    // Save results to localStorage for later reference
    localStorage.setItem('performance_test_results', JSON.stringify({
        timestamp: new Date().toISOString(),
        results: results
    }));
    
    console.log("\n📄 Results saved to localStorage");
    console.log("   Access with: JSON.parse(localStorage.getItem('performance_test_results'))");
    
    return results;
}

// Alternative: Test current page without navigation
function testCurrentPage() {
    console.log("\n📊 Testing Current Page Performance");
    
    const perfData = performance.getEntriesByType('navigation')[0];
    const paintMetrics = performance.getEntriesByType('paint');
    
    const firstPaint = paintMetrics.find(m => m.name === 'first-paint')?.startTime || 0;
    const firstContentfulPaint = paintMetrics.find(m => m.name === 'first-contentful-paint')?.startTime || 0;
    
    console.log(`\n   Page: ${window.location.pathname}`);
    console.log(`   Total Load Time: ${perfData.loadEventEnd.toFixed(0)}ms`);
    console.log(`   DOM Content Loaded: ${perfData.domContentLoadedEventEnd.toFixed(0)}ms`);
    console.log(`   First Paint: ${firstPaint.toFixed(0)}ms`);
    console.log(`   First Contentful Paint: ${firstContentfulPaint.toFixed(0)}ms`);
    console.log(`   Time to Interactive: ${perfData.domInteractive.toFixed(0)}ms`);
    
    // Check for slow resources
    const resources = performance.getEntriesByType('resource');
    const slowResources = resources
        .filter(r => r.duration > 1000)
        .sort((a, b) => b.duration - a.duration)
        .slice(0, 5);
    
    if (slowResources.length > 0) {
        console.log(`\n   ⚠️  Slow Resources (>1s):`);
        slowResources.forEach(r => {
            console.log(`   - ${r.name.split('/').pop()}: ${r.duration.toFixed(0)}ms`);
        });
    }
}

// Run tests
console.log("🚀 Frontend Performance Test Ready!");
console.log("\nTo test all pages (will navigate):");
console.log("  runFrontendBenchmarks()");
console.log("\nTo test current page only:");
console.log("  testCurrentPage()");
console.log("\nStarting full benchmark in 2 seconds...");

setTimeout(() => {
    runFrontendBenchmarks().catch(err => {
        console.error("❌ Test failed:", err);
    });
}, 2000);

