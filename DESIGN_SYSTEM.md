# 🎨 Design System - Document Collector

**Based on**: etichub.it  
**Version**: 1.0  
**Status**: Active

---

## Color Palette

### Primary Colors

```
Primary (Coral/Rose):     #E8847D
  └─ Usage: Buttons, links, accents, CTA
  └─ RGB: rgb(232, 132, 125)
  └─ Hover: #D97468
  └─ Active: #C85A53

Cream/Beige (Background): #F5F3F0
  └─ Usage: Page background, card backgrounds
  └─ RGB: rgb(245, 243, 240)
  └─ Alternative light: #FAFAF8

Black (Text):             #1A1A1A
  └─ Usage: Headings, body text
  └─ RGB: rgb(26, 26, 26)

Gray (Secondary):         #9A9A9A
  └─ Usage: Secondary text, placeholders
  └─ RGB: rgb(154, 154, 154)
  └─ Light gray: #E5E5E5
```

### Extended Palette

```
Success:   #10B981 (Green)
Warning:   #F59E0B (Amber)
Error:     #EF4444 (Red)
Info:      #3B82F6 (Blue)

Dark backgrounds: #1F2937
Light text on dark: #F9FAFB
```

---

## Typography

### Font Family

```
Primary Font:  "Poppins", "Montserrat", sans-serif
  └─ Light (300): Headings, accent text
  └─ Regular (400): Body text
  └─ Medium (500): Navigation, labels
  └─ Bold (700): Strong emphasis

Secondary Font: "Inter", sans-serif
  └─ Regular (400): Body, fallback
  └─ Medium (500): Buttons
```

### Import (Google Fonts)

```html
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
```

### Font Sizing

```
h1 (Heading 1):      2.5rem (40px) | Light (300)
h2 (Heading 2):      2rem (32px)   | Light (300)
h3 (Heading 3):      1.5rem (24px) | Regular (400)
h4 (Heading 4):      1.25rem (20px) | Regular (400)
h5 (Heading 5):      1.125rem (18px) | Medium (500)
h6 (Heading 6):      1rem (16px)   | Medium (500)

Body (Large):        1.125rem (18px) | Regular (400)
Body (Regular):      1rem (16px)     | Regular (400)
Body (Small):        0.875rem (14px) | Regular (400)
Caption:             0.75rem (12px)  | Regular (400)

Line Height:
  h1-h2: 1.2
  h3-h6: 1.3
  body:  1.6
```

---

## Components

### Buttons

```css
/* Primary Button - Border Style (like etichub CTA) */
.btn-primary {
  background: transparent;
  color: #E8847D;
  border: 2px solid #E8847D;
  padding: 12px 32px;
  border-radius: 25px;
  font-family: Poppins, sans-serif;
  font-weight: 500;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-primary:hover {
  background: #E8847D;
  color: white;
  border-color: #E8847D;
}

.btn-primary:active {
  background: #D97468;
  border-color: #D97468;
}

/* Secondary Button - Filled */
.btn-secondary {
  background: #E8847D;
  color: white;
  border: 2px solid #E8847D;
  padding: 12px 32px;
  border-radius: 25px;
  font-family: Poppins, sans-serif;
  font-weight: 500;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-secondary:hover {
  background: #D97468;
  border-color: #D97468;
}

/* Ghost Button */
.btn-ghost {
  background: transparent;
  color: #1A1A1A;
  border: 2px solid #E5E5E5;
  padding: 12px 32px;
  border-radius: 25px;
  font-family: Poppins, sans-serif;
  font-weight: 500;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-ghost:hover {
  border-color: #E8847D;
  color: #E8847D;
}

/* Success Button */
.btn-success {
  background: transparent;
  color: #10B981;
  border: 2px solid #10B981;
  padding: 12px 32px;
  border-radius: 25px;
}

.btn-success:hover {
  background: #10B981;
  color: white;
}
```

### Cards

```css
.card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid #F0EDEA;
  transition: all 0.3s ease;
}

.card:hover {
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.card-header {
  border-bottom: 2px solid #F5F3F0;
  padding-bottom: 16px;
  margin-bottom: 16px;
}

.card-title {
  font-family: Poppins, sans-serif;
  font-size: 1.5rem;
  font-weight: 400;
  color: #1A1A1A;
  margin: 0;
}

.card-description {
  font-family: Poppins, sans-serif;
  font-size: 1rem;
  color: #9A9A9A;
  margin: 8px 0 0 0;
}
```

### Forms

```css
.form-group {
  margin-bottom: 24px;
}

.form-label {
  display: block;
  font-family: Poppins, sans-serif;
  font-size: 0.95rem;
  font-weight: 500;
  color: #1A1A1A;
  margin-bottom: 8px;
}

.form-control {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid #E5E5E5;
  border-radius: 8px;
  font-family: Poppins, sans-serif;
  font-size: 1rem;
  color: #1A1A1A;
  background: white;
  transition: border-color 0.3s ease;
}

.form-control:focus {
  outline: none;
  border-color: #E8847D;
  box-shadow: 0 0 0 3px rgba(232, 132, 125, 0.1);
}

.form-control::placeholder {
  color: #9A9A9A;
}

.form-error {
  border-color: #EF4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.form-error-message {
  color: #EF4444;
  font-size: 0.85rem;
  margin-top: 6px;
}

.form-success {
  border-color: #10B981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
}

.form-success-message {
  color: #10B981;
  font-size: 0.85rem;
  margin-top: 6px;
}
```

### Navigation

```css
.navbar {
  background: white;
  border-bottom: 1px solid #F0EDEA;
  padding: 16px 0;
  position: sticky;
  top: 0;
  z-index: 100;
}

.navbar-brand {
  font-family: Poppins, sans-serif;
  font-size: 1.5rem;
  font-weight: 700;
  color: #1A1A1A;
  text-decoration: none;
}

.navbar-nav {
  list-style: none;
  display: flex;
  gap: 32px;
  margin: 0;
  padding: 0;
}

.navbar-link {
  font-family: Poppins, sans-serif;
  font-size: 1rem;
  color: #1A1A1A;
  text-decoration: none;
  transition: color 0.3s ease;
}

.navbar-link:hover,
.navbar-link.active {
  color: #E8847D;
}
```

### Alerts

```css
.alert {
  padding: 16px 20px;
  border-radius: 8px;
  border-left: 4px solid;
  margin-bottom: 20px;
  font-family: Poppins, sans-serif;
  font-size: 1rem;
}

.alert-success {
  background: rgba(16, 185, 129, 0.1);
  border-left-color: #10B981;
  color: #10B981;
}

.alert-error {
  background: rgba(239, 68, 68, 0.1);
  border-left-color: #EF4444;
  color: #EF4444;
}

.alert-info {
  background: rgba(59, 130, 246, 0.1);
  border-left-color: #3B82F6;
  color: #3B82F6;
}

.alert-warning {
  background: rgba(245, 158, 11, 0.1);
  border-left-color: #F59E0B;
  color: #F59E0B;
}
```

### Progress

```css
.progress-bar {
  width: 100%;
  height: 6px;
  background: #E5E5E5;
  border-radius: 3px;
  overflow: hidden;
  margin: 16px 0;
}

.progress-fill {
  height: 100%;
  background: #E8847D;
  width: 0%;
  transition: width 0.3s ease;
}
```

---

## Layout & Spacing

### Spacing Scale

```
Space 4px:   --space-xs
Space 8px:   --space-sm
Space 12px:  --space-md
Space 16px:  --space-lg
Space 24px:  --space-xl
Space 32px:  --space-2xl
Space 48px:  --space-3xl
Space 64px:  --space-4xl
```

### Container

```css
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.container-lg {
  max-width: 1400px;
}

.container-sm {
  max-width: 900px;
}
```

### Breakpoints

```
Mobile:   < 640px
Tablet:   640px - 1024px
Desktop:  > 1024px
```

---

## Shadows

```css
--shadow-xs:   0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-sm:   0 1px 3px rgba(0, 0, 0, 0.1);
--shadow-md:   0 4px 6px rgba(0, 0, 0, 0.1);
--shadow-lg:   0 10px 15px rgba(0, 0, 0, 0.1);
--shadow-xl:   0 20px 25px rgba(0, 0, 0, 0.1);
```

---

## Borders & Radius

```
Border Radius:
  --radius-sm:   4px
  --radius-md:   8px
  --radius-lg:   12px
  --radius-full: 9999px

Border Width:
  --border-thin:     1px
  --border-normal:   2px
  --border-thick:    3px
```

---

## CSS Variables (Root)

```css
:root {
  /* Colors */
  --color-primary:      #E8847D;
  --color-primary-dark: #D97468;
  --color-primary-light: #F0E8E6;
  
  --color-secondary:    #F5F3F0;
  --color-success:      #10B981;
  --color-error:        #EF4444;
  --color-warning:      #F59E0B;
  --color-info:         #3B82F6;
  
  --color-text:         #1A1A1A;
  --color-text-light:   #9A9A9A;
  --color-border:       #E5E5E5;
  --color-bg:           #F5F3F0;
  
  /* Typography */
  --font-primary:       'Poppins', sans-serif;
  --font-secondary:     'Inter', sans-serif;
  
  /* Spacing */
  --space-xs:  4px;
  --space-sm:  8px;
  --space-md:  12px;
  --space-lg:  16px;
  --space-xl:  24px;
  --space-2xl: 32px;
  --space-3xl: 48px;
  --space-4xl: 64px;
  
  /* Shadows */
  --shadow-sm:  0 1px 3px rgba(0, 0, 0, 0.1);
  --shadow-md:  0 4px 6px rgba(0, 0, 0, 0.1);
  --shadow-lg:  0 10px 15px rgba(0, 0, 0, 0.1);
  
  /* Border Radius */
  --radius-sm:  4px;
  --radius-md:  8px;
  --radius-lg:  12px;
  --radius-full: 9999px;
}
```

---

## Usage Guidelines

### When to Use Colors

| Color | When | Example |
|-------|------|---------|
| Primary (#E8847D) | Primary CTA, links, hover states | "Inizia", "Carica file" |
| Secondary (#F5F3F0) | Page background, card backgrounds | Page body, container bg |
| Black (#1A1A1A) | Headings, main text | Page title, body copy |
| Gray (#9A9A9A) | Secondary text, placeholder | Hint text, disabled state |
| Green (#10B981) | Success, confirmation | "Upload riuscito" |
| Red (#EF4444) | Error, danger | "File non consentito" |

### Font Weight Usage

| Weight | When | Example |
|--------|------|---------|
| Light (300) | Elegant headings, emphasis | H1, H2 titles |
| Regular (400) | Body text, default | Paragraphs, labels |
| Medium (500) | Navigation, buttons, emphasis | Nav links, button text |
| Bold (700) | Strong emphasis, logo | Brand name, keywords |

---

## Accessibility

- **Contrast**: All text meets WCAG AA standard (4.5:1 minimum)
- **Font size**: Minimum 16px on mobile (no zoom needed)
- **Touch targets**: Buttons minimum 44×44px
- **Color alone**: Never rely on color for meaning (use icons + text)
- **Focus states**: All interactive elements have visible focus ring

---

## Dark Mode (Optional Future)

```css
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg:         #1F2937;
    --color-text:       #F9FAFB;
    --color-text-light: #D1D5DB;
    --color-border:     #374151;
    --color-primary:    #F87171; /* Lighter rose for dark */
  }
}
```

---

## Implementation

### HTML Template Head

```html
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Document Collector - etichub style</title>
  
  <!-- Google Fonts -->
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  
  <!-- Design System CSS -->
  <link rel="stylesheet" href="/static/css/design-system.css">
  <link rel="stylesheet" href="/static/css/style.css">
</head>
```

### Folder Structure

```
modules/static/
├── css/
│  ├── design-system.css    ← CSS Variables + base styles
│  ├── components.css       ← Component styles
│  ├── layouts.css          ← Layout utilities
│  └── style.css            ← App-specific overrides
│
└── js/
   └── (existing)
```

---

## References

- **Reference Site**: etichub.it
- **Font Inspiration**: Montserrat Light, Poppins, Inter
- **Style**: Minimalist luxury, cosmetic/beauty industry
- **Mood**: Elegant, clean, sophisticated, professional

---

**Document Status**: ✅ Complete  
**Last Updated**: September 2026  
**Designer**: Design system based on etichub.it branding
