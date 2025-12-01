# Chrome Extension Errors - How to Fix

## The Error

You're seeing errors like:
```
inject.bundle.js:1 GET chrome-extension://invalid/ net::ERR_FAILED
```

## What This Is

These errors are **NOT from your code**. They're from a browser extension (likely a password manager, ad blocker, or similar) that's trying to inject scripts into your page.

## Solutions

### Option 1: Disable the Extension (Recommended for Development)

1. Go to `chrome://extensions/`
2. Find the extension causing issues (look for ones that inject scripts)
3. Toggle it off for local development
4. Refresh your page

### Option 2: Use Incognito Mode

1. Open Chrome in Incognito mode (Cmd+Shift+N on Mac, Ctrl+Shift+N on Windows)
2. Extensions are disabled by default in incognito
3. Navigate to `http://localhost:5189`

### Option 3: Ignore the Errors

These errors are **harmless** and don't affect your application. You can:
- Filter them out in Chrome DevTools console (right-click → "Hide messages from extensions")
- Or just ignore them - they won't break your app

### Option 4: Identify the Extension

1. Open Chrome DevTools (F12)
2. Go to Sources tab
3. Look for `inject.bundle.js` in the file tree
4. Check which extension it belongs to
5. Disable that specific extension

## Common Culprits

- Password managers (LastPass, 1Password, etc.)
- Ad blockers
- Privacy extensions
- Developer tools extensions

## Note

These errors **cannot be fixed in your code** because they're injected by browser extensions after your page loads. They're completely harmless and don't affect functionality.

