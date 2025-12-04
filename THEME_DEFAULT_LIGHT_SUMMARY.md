# Default Theme Changed to Light Mode

## Summary

Changed the default theme from dark to light mode to fix logo visibility issues. Dark mode toggle remains functional.

## Changes Made

### 1. **ThemeContext.jsx** - Default Theme
   - **Before:** Defaulted to `'dark'` if no preference saved
   - **After:** Defaults to `'light'` if no preference saved
   - **Line:** 19-21
   - Dark mode toggle still works and saves preference

### 2. **Login.jsx** - Background Color
   - **Before:** Hardcoded `backgroundColor: habexa.navy.dark`
   - **After:** Theme-aware `backgroundColor: 'background.default'`
   - **Line:** 37

### 3. **Register.jsx** - Background Color
   - **Before:** Hardcoded `backgroundColor: habexa.navy.dark`
   - **After:** Theme-aware `backgroundColor: 'background.default'`
   - **Line:** 67

### 4. **Sidebar.jsx** - Multiple Hardcoded Colors
   - **Background gradient:** Now theme-aware (white/light gray in light mode)
   - **Borders:** Changed from `habexa.gray[300]` to `theme.palette.divider`
   - **Text colors:** Changed from hardcoded grays to `theme.palette.text.primary/secondary`
   - **Badge border:** Changed from `habexa.navy.dark` to `theme.palette.background.default`
   - **Lines:** 39, 48, 64, 92, 93, 100, 197, 214

### 5. **DealCard.jsx** - Placeholder Background
   - **Before:** Hardcoded `bgcolor: '#252540'`
   - **After:** Theme-aware `bgcolor: 'background.paper'`
   - **Line:** 30

### 6. **Deals.jsx** - Placeholder Background
   - **Before:** Hardcoded `bgcolor: '#252540'`
   - **After:** Theme-aware `bgcolor: 'background.paper'`
   - **Line:** 161

### 7. **BuyList.jsx** - Placeholder Background
   - **Before:** Hardcoded `bgcolor: '#252540'`
   - **After:** Theme-aware `bgcolor: 'background.paper'`
   - **Line:** 208

### 8. **TelegramConnect.jsx** - Selected Channel Background
   - **Before:** Hardcoded `bgcolor: '#252540'`
   - **After:** Theme-aware `bgcolor: 'background.paper'`
   - **Line:** 607

## Files Modified

1. `frontend/src/context/ThemeContext.jsx`
2. `frontend/src/pages/Login.jsx`
3. `frontend/src/pages/Register.jsx`
4. `frontend/src/components/layout/Sidebar.jsx`
5. `frontend/src/components/common/DealCard.jsx`
6. `frontend/src/pages/Deals.jsx`
7. `frontend/src/pages/BuyList.jsx`
8. `frontend/src/components/features/settings/TelegramConnect.jsx`

## What Still Works

✅ **Dark mode toggle** - Users can still switch to dark mode
✅ **Preference saving** - Theme preference saved to localStorage
✅ **Purple accent color** - Unchanged (#7C3AED)
✅ **All functionality** - No behavior changes, only colors

## Expected Result

- ✅ App loads in **light mode by default**
- ✅ Logo is **visible** on light backgrounds
- ✅ User can **toggle to dark mode** (even if it needs refinement later)
- ✅ Purple accent color **stays the same**
- ✅ All hardcoded dark colors **replaced with theme-aware values**

## Testing

After deployment, verify:
1. App loads in light mode on first visit
2. Logo is visible on login/register pages
3. Theme toggle works and saves preference
4. Switching to dark mode still works
5. All pages use theme colors, not hardcoded values

## Commit

```
22dcf046 - feat: Change default theme to light mode
```

