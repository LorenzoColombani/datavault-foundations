# Mobile Web UX Audit Checklist for Tutorial Sites

*Generated from research on mobile best practices. Used to audit datavault-foundations chapters.*

## Critical CSS Rules (apply globally via mobile-fab.js)

### Prevent horizontal overflow
```css
html { overflow-x: hidden; } /* last resort — prefer fixing root causes */
```
WARNING: `overflow-x: hidden` on `body` breaks `position: sticky`. Use on `html` only.

### iOS auto-zoom prevention
```css
input, select, textarea { font-size: 16px; } /* prevents Safari zoom on focus */
```

### Touch targets: 44x44px minimum (Apple HIG / WCAG AAA)
```css
button, a, select, [role="button"] { min-height: 44px; min-width: 44px; }
```

### Safe area insets (notched iPhones)
```css
.fixed-bottom-element { padding-bottom: env(safe-area-inset-bottom, 0); }
```

### Never use 100vh for full-height (iOS URL bar issue)
```css
.hero { min-height: 100vh; min-height: 100svh; } /* svh = safe viewport height */
```

### Never use 100vw (includes scrollbar width)
Use `width: 100%` instead.

## Per-Element Patterns

### Code blocks
```css
pre { overflow-x: auto; -webkit-overflow-scrolling: touch; max-width: 100%; }
```

### Tables (4+ columns): scrollable wrapper
```css
.table-wrapper { overflow-x: auto; -webkit-overflow-scrolling: touch; max-width: 100%; }
```

### Tab bars (4+ tabs): scrollable or shrink
```css
.tab-bar { overflow-x: auto; scrollbar-width: none; scroll-snap-type: x mandatory; }
.tab-bar::-webkit-scrollbar { display: none; }
.tab { flex-shrink: 0; white-space: nowrap; min-height: 44px; }
```

### SVGs: must have viewBox, scale with width: 100%
```css
svg { width: 100%; height: auto; max-width: 100%; }
```

### FAB (Material Design 3)
- Standard: 56x56dp, Mini: 40x40dp
- Position: fixed, bottom 16px, right 16px
- Clear safe-area-inset-bottom

### Toasts
- Full-width on mobile (left: 16px, right: 16px)
- Min-height: 48px (single-line), 80px (multi-line)
- Must not overlap FAB

## Debug: Find Overflowing Elements
```javascript
var docWidth = document.documentElement.offsetWidth;
document.querySelectorAll('*').forEach(function(el) {
  if (el.offsetWidth > docWidth) console.log(el.tagName, el.className, el.id);
});
```

## Common Pitfalls
| Pitfall | Fix |
|---------|-----|
| 100vw horizontal scroll | Use width: 100% |
| 100vh clips on iOS | Use 100svh with fallback |
| iOS zooms on input focus | font-size: 16px on inputs |
| sticky not working | Check ancestors for overflow: hidden/auto |
| Fixed elements don't zoom | Convert to absolute on mobile |
| Flex items overflow | Add min-width: 0 to flex children |
| Long words break layout | overflow-wrap: break-word |
