# Icon Standardization - Quick Reference (Cheat Sheet)

## Size Classes (Pick One)

```
icon-xs   → 16px  (badges, tiny indicators)
icon-sm   → 20px  (small buttons, secondary)
icon-md   → 24px  ⭐ DEFAULT (most common)
icon-lg   → 32px  (headers, medium cards)
icon-xl   → 48px  (modal headers, hero)
icon-2xl  → 64px  (error pages, empty states)
```

## Color Classes (Optional)

```
icon-primary   → #0284c7  (brand blue, main actions)
icon-success   → #10b981  (green, confirmations)
icon-warning   → #f59e0b  (amber, alerts)
icon-error     → #ef4444  (red, errors)
icon-info      → #3b82f6  (blue, information)
icon-gray      → #6b7280  (gray, navigation)
icon-muted     → #9ca3af  (light gray, secondary)
```

## Common Patterns

### Button
```html
<button class="btn btn-primary">
  <i class="bi bi-plus-lg icon-md"></i> New
</button>
```

### Badge
```html
<span class="badge bg-success">
  <i class="bi bi-check-circle-fill icon-xs"></i> Done
</span>
```

### Alert
```html
<div class="alert alert-warning d-flex align-items-center gap-2">
  <i class="bi bi-exclamation-triangle-fill icon-md-warning flex-shrink-0"></i>
  Message
</div>
```

### List Item
```html
<li class="d-flex align-items-center gap-2">
  <i class="bi bi-file-earmark icon-md-primary"></i>
  Document
</li>
```

### Empty State
```html
<div class="text-center py-5">
  <i class="bi bi-inbox icon-2xl icon-gray mb-3 d-block"></i>
  <h5>No items</h5>
</div>
```

## Combined Classes (Size + Color)

```
.icon-xs-primary   .icon-xs-success   .icon-xs-warning   .icon-xs-error
.icon-sm-primary   .icon-sm-success   .icon-sm-warning   .icon-sm-error
.icon-md-primary   .icon-md-success   .icon-md-warning   .icon-md-error
.icon-lg-primary   .icon-lg-success   .icon-lg-warning   .icon-lg-error
```

### Example
```html
<i class="bi bi-check icon-md-success"></i>  ← 24px green check
```

## Bootstrap Icons Reference

```
Navigation:     bi-home  bi-search  bi-menu  bi-chevron-down
Actions:        bi-plus-lg  bi-trash  bi-pencil  bi-eye  bi-download  bi-upload
Status:         bi-check-circle-fill  bi-exclamation-circle-fill
Documents:      bi-file-earmark  bi-folder-check  bi-box-seam
People:         bi-person  bi-people  bi-person-circle
Alerts:         bi-info-circle-fill  bi-exclamation-triangle-fill  bi-bell-fill
Utility:        bi-calendar  bi-clock-history  bi-envelope  bi-phone

See: https://icons.getbootstrap.com/
```

## DO & DON'T

| ✓ DO | ✗ DON'T |
|------|---------|
| `<i class="bi bi-check icon-md"></i>` | `<i class="bi bi-check"></i>` |
| `<i class="bi bi-alert icon-md-warning"></i>` | `<i class="bi bi-alert" style="color: #f59e0b;">` |
| Pair with text | Use icon alone |
| Use semantic colors | Use arbitrary colors |
| Consistent sizing | Mix sizing approaches |
| Align with flexbox | Don't align |

## Context Examples

### Buttons (all sizes)
```html
<button class="btn btn-sm"><i class="bi bi-check"></i></button>
<button class="btn"><i class="bi bi-check icon-md"></i></button>
<button class="btn btn-lg"><i class="bi bi-check"></i></button>
```

### Statuses (always xs)
```html
<span class="badge bg-success"><i class="bi bi-check icon-xs"></i> OK</span>
<span class="badge bg-danger"><i class="bi bi-x icon-xs"></i> Error</span>
```

### Headers (lg or xl)
```html
<h3><i class="bi bi-folder icon-lg"></i> Folder</h3>
<h2><i class="bi bi-people icon-lg"></i> Users</h2>
```

### Alerts (always md)
```html
<div class="alert alert-success">
  <i class="bi bi-check icon-md-success"></i> Success
</div>
```

### Lists (always md)
```html
<li><i class="bi bi-file icon-md"></i> File</li>
<li><i class="bi bi-folder icon-md"></i> Folder</li>
```

## Migration Checklist

- [ ] Add size class to icon
- [ ] Replace inline styles with color classes
- [ ] Use flexbox for alignment
- [ ] Pair with text for context
- [ ] Test on mobile
- [ ] Verify accessibility

## One-Liner Template

```html
<!-- Size + Color in one class -->
<i class="bi bi-ICON-NAME icon-SIZE-COLOR"></i>

<!-- Or separate if needed -->
<i class="bi bi-ICON-NAME icon-SIZE icon-COLOR"></i>
```

## Most Used Combinations

```
• icon-md-primary      (24px blue) - DEFAULT for buttons
• icon-md-success      (24px green) - Success states
• icon-md-warning      (24px amber) - Warnings
• icon-md-error        (24px red) - Errors
• icon-xs              (16px) - Badge labels
• icon-2xl             (64px) - Empty states
```

## Accessibility Tips

1. **Always add context** - Never icon alone
2. **Use semantic colors** - Don't use warning color for success
3. **Sufficient contrast** - All colors pass WCAG AA
4. **Meaningful positioning** - Place before or after text logically

## CSS Location

**File:** `modules/static/css/design-system.css`  
**Lines:** ~700-950  
**Classes:** 35+ total

## Full Documentation

See:
- **Complete Guide:** `ICON_STANDARDS.md`
- **Live Examples:** `ICON_EXAMPLES.html`
- **Full Report:** `ICON_STANDARDIZATION_REPORT.md`

---

**Print this page and keep it handy!** ✨
