# Icon Standardization System

**Last Updated:** 2026-09-08  
**Version:** 1.0  
**Status:** Production Ready

## Overview

This document establishes standardized icon sizing and color conventions across the etichub Document Collector application. All icons use **Bootstrap Icons (bi)** library and follow a consistent scale and color palette.

## Icon Size Standards

### Size Scale

| Class | Size | Usage | Example |
|-------|------|-------|---------|
| `.icon-xs` | 16px | Inline icons, badges, small indicators | `<i class="bi bi-check icon-xs"></i>` |
| `.icon-sm` | 20px | Small buttons, list items, secondary elements | `<i class="bi bi-arrow-left icon-sm"></i>` |
| `.icon-md` | 24px | **Default** - Button icons, list items, normal actions | `<i class="bi bi-upload icon-md"></i>` |
| `.icon-lg` | 32px | Section headers, feature cards | `<i class="bi bi-folder-check icon-lg"></i>` |
| `.icon-xl` | 48px | Modal headers, hero sections | `<i class="bi bi-exclamation-circle icon-xl"></i>` |
| `.icon-2xl` | 64px | Error pages, empty states, major sections | `<i class="bi bi-search icon-2xl"></i>` |

### Size Selection Guide

- **16px (xs)**: Badges, status indicators next to text, small inline icons
- **20px (sm)**: Secondary buttons, small form icons, compact lists
- **24px (md)**: Primary buttons, list items, standard UI elements (MOST COMMON)
- **32px (lg)**: Section headers, medium cards, section transitions
- **48px (xl)**: Modal headers, feature highlights, prominent alerts
- **64px (2xl)**: Full-page states (404, 500), empty states, hero sections

## Icon Color Standards

### Primary Colors

| Class | Color | Usage | Hex Value |
|-------|-------|-------|-----------|
| `.icon-primary` | Primary Brand | Primary buttons, main CTAs | `#E8847D` |
| `.icon-success` | Success Green | Confirmations, checkmarks, success states | `#10B981` |
| `.icon-warning` | Warning Amber | Alerts, cautions, warnings | `#F59E0B` |
| `.icon-error` / `.icon-danger` | Error Red | Errors, delete actions, critical alerts | `#EF4444` |
| `.icon-gray` | Neutral Gray | Navigation, disabled state, secondary info | `#6b7280` |
| `.icon-muted` | Light Gray | Placeholder icons, very secondary info | `#C0C0C0` |
| `.icon-info` | Info Blue | Information alerts, help text | `#3B82F6` |
| `.icon-secondary` | Text Light | Less important actions, secondary items | `#9A9A9A` |

### Color Selection Guide

- **Primary**: Main action icons (upload, send, create)
- **Success**: Checkmarks, confirmations, success alerts
- **Warning**: Cautions, alerts, things needing attention
- **Error/Danger**: Delete buttons, error states, critical issues
- **Gray**: Navigation items, disabled buttons
- **Muted**: Placeholder content, very secondary info
- **Info**: Information boxes, help icons

## Icon Combinations (Size + Color)

For convenience, combined classes are available:

```html
<!-- Combinations available for md/sm/xs/lg sizes -->
.icon-md-primary     /* 24px, primary color */
.icon-md-success     /* 24px, success color */
.icon-md-warning     /* 24px, warning color */
.icon-md-error       /* 24px, error color */

.icon-lg-primary     /* 32px, primary color */
.icon-lg-success     /* 32px, success color */
.icon-lg-warning     /* 32px, warning color */
.icon-lg-error       /* 32px, error color */

.icon-sm-primary     /* 20px, primary color */
.icon-xs-primary     /* 16px, primary color */
```

## Usage Examples

### 1. Button Icons

```html
<!-- Primary button with icon -->
<button class="btn btn-primary">
  <i class="bi bi-plus-lg icon-md"></i> Nuovo Modulo
</button>

<!-- Small button -->
<button class="btn btn-sm btn-outline-secondary">
  <i class="bi bi-arrow-left icon-sm me-1"></i> Indietro
</button>

<!-- Large button -->
<button class="btn btn-lg btn-success">
  <i class="bi bi-check-circle icon-lg me-2"></i> Salva Documento
</button>
```

### 2. Status Indicators

```html
<!-- Success status -->
<span class="badge bg-success">
  <i class="bi bi-check-circle-fill icon-xs"></i> Completato
</span>

<!-- Warning status -->
<span class="badge bg-warning text-dark">
  <i class="bi bi-exclamation-triangle-fill icon-xs"></i> Da Rivedere
</span>

<!-- Error status -->
<span class="badge bg-danger">
  <i class="bi bi-exclamation-octagon-fill icon-xs"></i> Errore
</span>
```

### 3. Alert Icons

```html
<!-- Info alert -->
<div class="alert alert-info d-flex align-items-center gap-2">
  <i class="bi bi-info-circle-fill icon-md-info flex-shrink-0"></i>
  <div>Questo è un messaggio informativo.</div>
</div>

<!-- Success alert -->
<div class="alert alert-success d-flex align-items-center gap-2">
  <i class="bi bi-check-circle-fill icon-md-success flex-shrink-0"></i>
  <div>Operazione completata con successo!</div>
</div>

<!-- Warning alert -->
<div class="alert alert-warning d-flex align-items-center gap-2">
  <i class="bi bi-exclamation-triangle-fill icon-md-warning flex-shrink-0"></i>
  <div>Attenzione: leggere attentamente.</div>
</div>

<!-- Error alert -->
<div class="alert alert-danger d-flex align-items-center gap-2">
  <i class="bi bi-exclamation-circle-fill icon-md-error flex-shrink-0"></i>
  <div>Si è verificato un errore.</div>
</div>
```

### 4. List Items

```html
<!-- Document list item -->
<div class="d-flex align-items-center gap-2">
  <i class="bi bi-file-earmark-pdf icon-md icon-error"></i>
  <div>
    <h6>Report.pdf</h6>
    <small class="text-muted">2.5 MB</small>
  </div>
</div>

<!-- Customer list item -->
<div class="d-flex align-items-center gap-2">
  <i class="bi bi-person-circle icon-lg icon-primary"></i>
  <div>
    <h6>Giovanni Rossi</h6>
    <small>Premium Customer</small>
  </div>
</div>
```

### 5. Form Elements

```html
<!-- Input with icon -->
<div class="input-group">
  <span class="input-group-text">
    <i class="bi bi-search icon-md icon-gray"></i>
  </span>
  <input type="text" class="form-control" placeholder="Cerca...">
</div>

<!-- Icon in label -->
<label class="form-label">
  <i class="bi bi-file-earmark icon-sm icon-primary me-1"></i>
  Carica Documento
</label>
```

### 6. Empty States

```html
<!-- Empty state with large icon -->
<div class="text-center py-5">
  <i class="bi bi-inbox icon-2xl icon-gray mb-3 d-block"></i>
  <h5>Nessun documento</h5>
  <p class="text-muted">Carica il tuo primo documento per iniziare</p>
</div>
```

### 7. Navigation Icons

```html
<!-- Navigation menu -->
<nav class="navbar">
  <a href="/">
    <i class="bi bi-house icon-md icon-gray"></i>
    Dashboard
  </a>
  <a href="/customers">
    <i class="bi bi-people icon-md icon-gray"></i>
    Clienti
  </a>
</nav>
```

### 8. Badge Icons

```html
<!-- Required field indicator -->
<span class="text-danger ms-1">
  <i class="bi bi-asterisk icon-xs"></i>
</span>

<!-- Info badge -->
<button type="button" class="btn-close" title="Information">
  <i class="bi bi-info-circle icon-sm icon-gray"></i>
</button>
```

### 9. Status Circles

```html
<!-- Completed status -->
<div class="d-inline-flex align-items-center justify-content-center rounded-circle" 
     style="width: 32px; height: 32px; background: #ecfdf5;">
  <i class="bi bi-check-circle-fill icon-md-success"></i>
</div>

<!-- Processing status -->
<div class="d-inline-flex align-items-center justify-content-center rounded-circle" 
     style="width: 32px; height: 32px; background: #eff6ff;">
  <i class="bi bi-gear-wide-connected icon-md-info"></i>
</div>

<!-- Error status -->
<div class="d-inline-flex align-items-center justify-content-center rounded-circle" 
     style="width: 32px; height: 32px; background: #fef2f2;">
  <i class="bi bi-exclamation-circle-fill icon-md-error"></i>
</div>
```

### 10. Table Icons

```html
<!-- Status column -->
<td>
  <span class="d-flex align-items-center gap-2">
    <i class="bi bi-check-circle-fill icon-md-success"></i>
    Completato
  </span>
</td>

<!-- Action column -->
<td>
  <button class="btn btn-sm btn-outline-primary">
    <i class="bi bi-eye icon-sm"></i>
  </button>
  <button class="btn btn-sm btn-outline-danger">
    <i class="bi bi-trash icon-sm"></i>
  </button>
</td>
```

## Current Implementation Map

### Files Using Icons

**Admin Templates:**
- `modules/templates/modules/admin/dashboard.html` ✓ (Icons present)
- `modules/templates/modules/admin/customer_list.html` ✓ (Icons present)
- `modules/templates/modules/admin/customer_form.html` ✓ (Icons present)
- `modules/templates/modules/admin/assignment_detail.html` ✓ (Icons present)
- `modules/templates/modules/admin/builder.html` ✓ (Icons present)
- `modules/templates/modules/admin/operational_guide.html` ✓ (Icons present)

**Client Templates:**
- `modules/templates/modules/client/login.html` ✓ (Icons present)
- `modules/templates/modules/client/dashboard.html` ✓ (Icons present)
- `modules/templates/modules/client/base_client.html` ✓ (Icons present)
- `modules/templates/modules/client/upload_guide_modal.html` ✓ (Icons present)

**Form Templates:**
- `modules/templates/modules/form_step.html` ✓ (Icons present)
- `modules/templates/modules/form_summary.html` ✓ (Icons present)
- `modules/templates/modules/form_success.html` ✓ (Icons present)
- `modules/templates/modules/form_already_submitted.html` ✓ (Icons present)

**Error/Info Pages:**
- `modules/templates/404.html` ✓ (Icons present)
- `modules/templates/403.html` ✓ (Icons present)
- `modules/templates/500.html` ✓ (Icons present)

## Migration Guide

### Current Bootstrap Classes (OLD) → New Standard Classes (NEW)

```html
<!-- OLD: Using Bootstrap font-size utilities -->
<i class="bi bi-upload fs-3"></i>  <!-- ~2rem size -->

<!-- NEW: Using standardized icon classes -->
<i class="bi bi-upload icon-lg"></i>  <!-- 32px, consistent -->

<!-- OLD: Inline color styles -->
<i class="bi bi-check" style="color: #10b981;"></i>

<!-- NEW: Using color classes -->
<i class="bi bi-check icon-md-success"></i>

<!-- OLD: No sizing or color consistency -->
<i class="bi bi-exclamation-circle"></i>

<!-- NEW: Explicit size and color -->
<i class="bi bi-exclamation-circle icon-lg icon-warning"></i>
```

## Naming Convention

### Icon Class Structure

```
.icon-[SIZE]-[COLOR]

Where:
  SIZE: xs | sm | md | lg | xl | 2xl
  COLOR: primary | success | warning | error | gray | muted | info | secondary
```

### Examples

```
.icon-md              /* 24px, inherit color */
.icon-success         /* inherit size, green */
.icon-md-success      /* 24px, green */
.icon-lg-error        /* 32px, red */
.icon-xs-warning      /* 16px, amber */
```

## Best Practices

### 1. Always Specify Size

```html
<!-- Good -->
<i class="bi bi-check icon-md"></i>

<!-- Avoid -->
<i class="bi bi-check"></i>
```

### 2. Use Color Classes Instead of Inline Styles

```html
<!-- Good -->
<i class="bi bi-alert-circle icon-md icon-warning"></i>

<!-- Avoid -->
<i class="bi bi-alert-circle" style="font-size: 24px; color: #f59e0b;"></i>
```

### 3. Pair with Flexbox for Alignment

```html
<!-- Good -->
<div class="d-flex align-items-center gap-2">
  <i class="bi bi-upload icon-md icon-primary"></i>
  <span>Upload Document</span>
</div>

<!-- Less ideal -->
<span>Upload <i class="bi bi-upload"></i> Document</span>
```

### 4. Use Semantic Color Meanings

- Green (success) = Completed, confirmed, positive
- Red (error) = Errors, failures, delete actions
- Amber (warning) = Cautions, alerts, needs attention
- Blue (info) = Information, help, explanations
- Gray = Secondary, disabled, navigation

### 5. Context Matters

**Buttons**: Primary or secondary color based on action type
```html
<button class="btn btn-primary">
  <i class="bi bi-download icon-md-primary"></i> Download
</button>

<button class="btn btn-danger">
  <i class="bi bi-trash icon-md-error"></i> Delete
</button>
```

**Lists**: Gray or primary depending on importance
```html
<li><i class="bi bi-file icon-md icon-gray"></i> Document.pdf</li>
<li><i class="bi bi-star-fill icon-md icon-primary"></i> Favorite.pdf</li>
```

**Alerts**: Color matches alert type
```html
<div class="alert alert-success">
  <i class="bi bi-check-circle icon-md-success"></i> Success!
</div>
```

## CSS Variables Used

```css
--color-primary: #E8847D      /* Brand coral/rose */
--color-success: #10B981      /* Success green */
--color-warning: #F59E0B      /* Warning amber */
--color-error: #EF4444        /* Error red */
--color-info: #3B82F6         /* Info blue */
--color-text-light: #9A9A9A   /* Secondary gray */
--color-text-lighter: #C0C0C0 /* Muted gray */
```

## Accessibility Considerations

### 1. Semantic Meaning

Icons should reinforce meaning, not replace text:

```html
<!-- Good: Icon + text -->
<button class="btn btn-primary">
  <i class="bi bi-check-circle icon-md"></i> Confirm
</button>

<!-- Bad: Icon only, no context -->
<button class="btn btn-primary" title="Confirm">
  <i class="bi bi-check-circle icon-md"></i>
</button>
```

### 2. Color Not Alone

Don't rely on color alone to convey information:

```html
<!-- Good: Icon + color + text -->
<span class="badge bg-success">
  <i class="bi bi-check-circle-fill icon-xs"></i> Complete
</span>

<!-- Bad: Color only -->
<span class="badge bg-success">Complete</span>
```

### 3. Icon Contrast

Ensure sufficient contrast between icon color and background:

```html
<!-- Good: High contrast -->
<div style="background: white;">
  <i class="bi bi-check-circle icon-lg icon-success"></i>
</div>

<!-- Check: May have contrast issues -->
<div style="background: #ecfdf5;">
  <i class="bi bi-check-circle icon-lg icon-success"></i>
</div>
```

## Performance Considerations

- Bootstrap Icons are loaded from CDN
- Icon files are already optimized SVGs
- Use CSS classes (no inline styles) for better caching
- Limit to necessary icon sizes for performance

## Testing Checklist

- [ ] All icons have explicit size class
- [ ] Icons use semantic colors
- [ ] Contrast meets WCAG AA standards
- [ ] Icons display correctly on mobile
- [ ] Icons print correctly
- [ ] No broken icon references
- [ ] Color-blind users can understand meaning
- [ ] Screen readers get necessary context

## Icon Library Reference

### Common Bootstrap Icons Used

```
Navigation:
- bi-home, bi-search, bi-menu, bi-chevron-down, bi-arrow-left, bi-arrow-right

Actions:
- bi-plus-lg, bi-trash, bi-pencil, bi-eye, bi-download, bi-upload, bi-save

Status:
- bi-check-circle-fill, bi-exclamation-circle-fill, bi-info-circle-fill
- bi-question-circle-fill, bi-x-circle-fill

Documents:
- bi-file-earmark-pdf, bi-file-earmark-check, bi-file-earmark-arrow-up
- bi-folder-check, bi-box-seam

People:
- bi-person, bi-people, bi-person-circle, bi-person-plus-fill

Alert/Warning:
- bi-exclamation-triangle-fill, bi-bell-fill, bi-patch-exclamation

Utility:
- bi-calendar, bi-clock-history, bi-envelope, bi-phone, bi-at

See: https://icons.getbootstrap.com/
```

## Future Enhancements

- [ ] SVG icon system as alternative to Bootstrap Icons
- [ ] Icon animation utilities
- [ ] RTL (right-to-left) icon positioning
- [ ] Dark mode icon color adjustments
- [ ] Icon animation library integration

---

**Questions or Updates?** Contact the development team or create an issue in the project repository.
