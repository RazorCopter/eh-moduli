# 🎨 UI Implementation Guide - etichub Style

**Design System Version**: 1.0  
**Based On**: etichub.it cosmetics branding  
**Last Updated**: September 2026

---

## Quick Start

### 1. Template Head (base.html)

Include these in your template's `<head>`:

```html
<!-- Google Fonts -->
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">

<!-- Design System CSS -->
<link rel="stylesheet" href="{% static 'css/design-system.css' %}">
```

### 2. Color Palette Quick Reference

```
Primary (CTA):     #E8847D (Rosa/Coral)
Background:        #F5F3F0 (Cream/Beige)
Text:              #1A1A1A (Black)
Secondary Text:    #9A9A9A (Gray)
Success:           #10B981 (Green)
Error:             #EF4444 (Red)
```

---

## Component Usage

### Buttons

**Primary Button** (transparent with border)
```html
<button class="btn btn-primary">Inizia</button>
<a href="#" class="btn btn-primary">Learn More</a>
```

**Secondary Button** (filled)
```html
<button class="btn btn-secondary">Submit</button>
```

**Ghost Button** (minimal style)
```html
<button class="btn btn-ghost">Cancel</button>
```

**Success Button**
```html
<button class="btn btn-success">Upload Riuscito</button>
```

**Danger Button**
```html
<button class="btn btn-danger">Delete</button>
```

**Button Sizes**
```html
<button class="btn btn-sm btn-primary">Small</button>
<button class="btn btn-primary">Normal</button>
<button class="btn btn-lg btn-primary">Large</button>
```

**Disabled State**
```html
<button class="btn btn-primary" disabled>Disabled</button>
```

---

### Forms

**Basic Form**
```html
<div class="form-group">
    <label for="email" class="form-label">Email</label>
    <input type="email" id="email" class="form-control" placeholder="your@email.com">
</div>
```

**Required Field**
```html
<label class="form-label required">Full Name</label>
```

**Text Area**
```html
<textarea class="form-control" placeholder="Enter your message..."></textarea>
```

**Select Dropdown**
```html
<select class="form-control">
    <option value="">Choose option...</option>
    <option value="1">Option 1</option>
    <option value="2">Option 2</option>
</select>
```

**Form Validation**
```html
<!-- Valid state -->
<input type="text" class="form-control is-valid">
<div class="form-feedback valid">✓ Looks good!</div>

<!-- Invalid state -->
<input type="text" class="form-control is-invalid">
<div class="form-feedback invalid">❌ Please fix this error</div>
```

**Checkbox**
```html
<div class="form-check">
    <input type="checkbox" id="agree" class="form-check-input">
    <label for="agree" class="form-check-label">I agree to terms</label>
</div>
```

---

### Cards

**Basic Card**
```html
<div class="card">
    <h3 class="card-title">Card Title</h3>
    <p>Card content goes here</p>
</div>
```

**Card with Header**
```html
<div class="card">
    <div class="card-header">
        <h3 class="card-title">Form Title</h3>
        <p class="card-subtitle">Additional info</p>
    </div>
    <div class="card-body">
        <!-- Form content -->
    </div>
</div>
```

**Card with Footer**
```html
<div class="card">
    <div class="card-body">
        <!-- Main content -->
    </div>
    <div class="card-footer">
        <button class="btn btn-primary">Submit</button>
    </div>
</div>
```

---

### Alerts

**Success Alert**
```html
<div class="alert alert-success alert-dismissible">
    ✓ File uploaded successfully!
    <button class="btn-close">×</button>
</div>
```

**Error Alert**
```html
<div class="alert alert-error">
    ❌ File type not allowed. Please use PDF or JPG.
</div>
```

**Info Alert**
```html
<div class="alert alert-info">
    ℹ️ This document is optional. You can skip it if needed.
</div>
```

**Warning Alert**
```html
<div class="alert alert-warning">
    ⚠️ Your form will expire in 5 days.
</div>
```

---

### Progress

**Progress Bar**
```html
<div class="progress">
    <div class="progress-bar" style="width: 65%"></div>
</div>

<p>65% Complete</p>
```

**Dynamic Progress (HTMX)**
```html
<div class="progress">
    <div class="progress-bar" 
         hx-get="/api/progress/"
         hx-trigger="every 1s"
         hx-swap="outerHTML">
    </div>
</div>
```

---

### Typography

**Headings**
```html
<h1>Main Title</h1>           <!-- Light (300), 2.5rem -->
<h2>Section Heading</h2>      <!-- Light (300), 2rem -->
<h3>Subsection</h3>           <!-- Regular (400), 1.5rem -->
<h4>Minor Heading</h4>        <!-- Regular (400), 1.25rem -->
```

**Text Variants**
```html
<p>Body text (regular)</p>
<p class="text-muted">Secondary text (gray)</p>
<p class="text-primary">Accent text (coral)</p>
<p class="text-center">Centered text</p>
```

---

## Layout & Utilities

### Spacing

**Margin**
```html
<div class="mt-3">Top margin</div>         <!-- 1rem -->
<div class="mb-4">Bottom margin</div>      <!-- 1.5rem -->
<div class="mb-5">Larger margin</div>      <!-- 2rem -->
```

**Padding**
```html
<div class="p-2">Padded container</div>    <!-- 0.75rem padding -->
<div class="p-4">More padding</div>        <!-- 1rem padding -->
```

### Flexbox

```html
<div class="flex justify-between items-center gap-3">
    <div>Left item</div>
    <div>Right item</div>
</div>

<div class="flex flex-col gap-2">
    <div>Stack vertically</div>
    <div>With gap</div>
</div>
```

### Container

```html
<div class="container">
    <!-- Max width 1200px, centered, horizontal padding -->
</div>

<div class="container-lg">
    <!-- Max width 1400px -->
</div>

<div class="container-sm">
    <!-- Max width 900px -->
</div>
```

---

## Real-World Examples

### Document Upload Card

```html
<div class="card">
    <div class="card-header">
        <h4 class="card-title">📄 Copia Fronte Documento</h4>
        <p class="card-subtitle">File obbligatorio</p>
    </div>

    <div class="card-body">
        <div class="form-group">
            <label for="upload1" class="form-label">
                Seleziona file (PDF, JPG, PNG)
            </label>
            <input type="file"
                   id="upload1"
                   class="form-control"
                   accept=".pdf,.jpg,.png"
                   hx-post="/modules/upload/"
                   hx-target="#upload-status"
                   hx-include="[name='requirement_id']">
            <input type="hidden" name="requirement_id" value="abc123">
        </div>

        <div id="upload-status"></div>

        <div class="mt-3">
            <p class="text-sm text-muted">Dimensione massima: 5MB</p>
        </div>
    </div>

    <div class="card-footer">
        <button type="button" class="btn btn-ghost btn-sm">
            Salta documento
        </button>
    </div>
</div>
```

### Admin Dashboard Card

```html
<div class="card">
    <div class="card-header">
        <h3 class="card-title">Modulistiche Totali</h3>
    </div>
    <div class="card-body flex justify-between items-center">
        <div>
            <h2 style="font-size: 2.5rem; color: var(--color-primary);">
                127
            </h2>
            <p class="text-muted">Assegnazioni attive</p>
        </div>
        <div style="font-size: 3rem;">📋</div>
    </div>
</div>
```

### Form with Validation

```html
<form method="post" class="card">
    {% csrf_token %}

    <div class="card-header">
        <h3 class="card-title">Dati Personali</h3>
    </div>

    <div class="card-body">
        <div class="form-group">
            <label for="name" class="form-label required">Nome</label>
            <input type="text" id="name" name="name" class="form-control">
            {% if form.name.errors %}
                <div class="form-feedback invalid">
                    {{ form.name.errors.0 }}
                </div>
            {% endif %}
        </div>

        <div class="form-group">
            <label for="email" class="form-label required">Email</label>
            <input type="email" id="email" name="email" class="form-control">
            {% if form.email.errors %}
                <div class="form-feedback invalid">
                    {{ form.email.errors.0 }}
                </div>
            {% endif %}
        </div>

        <div class="form-check">
            <input type="checkbox" id="agree" name="agree" class="form-check-input">
            <label for="agree" class="form-check-label required">
                Dichiaro di aver letto l'informativa privacy
            </label>
        </div>
    </div>

    <div class="card-footer">
        <button type="submit" class="btn btn-primary">Invia</button>
        <button type="reset" class="btn btn-ghost ms-2">Cancella</button>
    </div>
</form>
```

---

## HTMX Integration

### File Upload with Progress

```html
<form>
    <input type="file"
           class="form-control"
           hx-post="/modules/upload/"
           hx-target="#result"
           hx-indicator="#loading"
           hx-on="htmx:xhr:progress(loaded,total) 
                  document.querySelector('#progress-bar').style.width = (loaded/total)*100 + '%'">

    <div id="loading" class="htmx-indicator progress mt-3">
        <div id="progress-bar" class="progress-bar" style="width: 0%"></div>
    </div>

    <div id="result" class="mt-3"></div>
</form>
```

### Dynamic Form Validation

```html
<input type="email"
       class="form-control"
       hx-post="/validate/email/"
       hx-trigger="blur change"
       hx-target="#email-feedback">

<div id="email-feedback"></div>
```

### Server Response (Validation)

```html
<!-- Success -->
<div class="form-feedback valid">✓ Email is available</div>

<!-- Error -->
<div class="form-feedback invalid">❌ Email already registered</div>
```

---

## CSS Variables (For Custom Styling)

If you need to use colors or spacing in custom styles:

```css
:root {
    /* Colors */
    --color-primary: #E8847D;
    --color-bg: #F5F3F0;
    --color-text: #1A1A1A;
    --color-text-light: #9A9A9A;
    
    /* Typography */
    --font-primary: 'Poppins', sans-serif;
    --font-secondary: 'Inter', sans-serif;
    
    /* Spacing */
    --space-lg: 1rem;
    --space-xl: 1.5rem;
    --space-2xl: 2rem;
    
    /* Shadows */
    --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
    
    /* Radius */
    --radius-md: 8px;
    --radius-full: 9999px;
}
```

Usage in custom styles:

```css
.my-custom-element {
    color: var(--color-primary);
    background: var(--color-bg);
    padding: var(--space-xl);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
    font-family: var(--font-primary);
}
```

---

## Responsive Behavior

All components are mobile-first and responsive by default:

```html
<!-- This will work on mobile and desktop -->
<div class="container">
    <div class="flex flex-col gap-3">
        <div class="card">Mobile friendly</div>
        <div class="card">Responsive design</div>
    </div>
</div>
```

---

## Best Practices

### ✅ Do

- Use semantic HTML (`<button>` not `<a>` for buttons that submit)
- Use the design system classes instead of custom styles
- Keep spacing consistent (use spacing utilities)
- Use color variables for themability
- Test on mobile devices
- Use meaningful form labels

### ❌ Don't

- Don't hardcode colors (use CSS variables)
- Don't add inline styles (use classes)
- Don't create new button styles (use existing ones)
- Don't forget `required` attribute on required fields
- Don't use generic names like "Click Here" for links

---

## File Structure

```
modules/
├── static/
│   └── css/
│       ├── design-system.css    ← etichub palette & components
│       ├── components.css       ← (optional) extra components
│       └── style.css            ← app-specific overrides
│
└── templates/
    ├── accounts/
    │   └── base.html            ← included in all pages
    ├── modules/
    │   ├── form_detail.html      ← uses design system
    │   ├── form_step.html        ← uses design system
    │   └── form_summary.html     ← uses design system
    └── admin/
        ├── dashboard.html       ← uses design system
        └── ...
```

---

## Troubleshooting

**Fonts not loading?**
- Check Google Fonts link is in `<head>`
- Clear browser cache
- Verify in DevTools → Network tab

**Colors look different?**
- Check CSS variables are declared in `:root`
- Verify `design-system.css` is loaded first
- No custom styles should override system colors

**Buttons not styled?**
- Use both `btn` and `btn-primary` classes
- Check for conflicting CSS rules
- Verify form-control is used for inputs, not button

---

## Support

For design questions or issues:
1. Check `DESIGN_SYSTEM.md` for palette details
2. Review this guide for component usage
3. See `accounts/templates/accounts/base.html` for real example
4. Check `accounts/templates/accounts/login.html` for form example

---

**Last Updated**: September 2026  
**Design System Version**: 1.0  
**Status**: ✅ Production Ready
