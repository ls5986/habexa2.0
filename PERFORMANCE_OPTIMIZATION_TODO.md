# Performance Optimization - TODO (Low Priority)

## Code Splitting for Better Performance

**Status:** ⏸️ Deferred - Focus on app stability first

### Current Large Chunks:
- `DealDetail` - 426 KB
- `index` (main bundle) - 710 KB

### Solution: Add to `vite.config.js`

```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3002,
    proxy: {
      '/api': {
        target: 'http://localhost:8020',
        changeOrigin: true,
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Vendor chunks
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'mui-vendor': ['@mui/material', '@mui/icons-material'],
          'chart-vendor': ['recharts'],
          // Heavy features as separate chunks
          'deal-detail': ['./src/pages/DealDetail.jsx'],
        },
      },
    },
    chunkSizeWarningLimit: 600, // Or just increase the warning limit
  },
});
```

### Benefits:
- Users don't download everything upfront
- Pages load faster
- Better caching (vendor chunks change less frequently)

### When to Implement:
- ✅ After app is stable
- ✅ After all critical bugs are fixed
- ✅ After API URL issues are resolved

