# Error Pages - Design Specifications

## Design System Overview

All error pages follow a consistent premium design system aligned with your Etichub brand, using:
- **Typography**: Poppins font (300, 400, 500, 600, 700 weights)
- **Theme**: Light, modern, professional
- **Framework**: Bootstrap 5.3.0 + Custom CSS
- **Responsiveness**: Mobile-first approach

---

## 404 - Page Not Found

### Visual Hierarchy
```
╔═══════════════════════════════════════╗
║      Full-width Gradient Background   ║
║  (Light Blue: #F0F9FF → #E0F2FE)     ║
║                                       ║
║    ┌─────────────────────────────┐   ║
║    │   White Content Card         │   ║
║    │   (Shadow + rounded corners) │   ║
║    │                             │   ║
║    │  🔍 (Exclamation Icon)     │   ║
║    │   Floating animation        │   ║
║    │                             │   ║
║    │   404                       │   ║
║    │   (Code badge)              │   ║
║    │                             │   ║
║    │  Pagina Non Trovata         │   ║
║    │  (Large, bold heading)      │   ║
║    │                             │   ║
║    │  La pagina che stai         │   ║
║    │  cercando non esiste...     │   ║
║    │  (Description paragraph)    │   ║
║    │                             │   ║
║    │  [Torna alla Home]  [Cont.] │   ║
║    │   Primary Button | Secondary │   ║
║    │                             │   ║
║    │  ─────────────────────────  │   ║
║    │  Footer with links          │   ║
║    └─────────────────────────────┘   ║
║                                       ║
╚═══════════════════════════════════════╝
```

### Color Palette
| Element | Color | Usage |
|---------|-------|-------|
| Background | `#F0F9FF` | Primary background |
| Gradient | `#E0F2FE` | Secondary gradient |
| Icon | `#0284c7` | Cyan-600 icon color |
| Title | `#0c4a6e` | Dark slate blue |
| Description | `#475569` | Medium gray |
| Primary Button | `#0284c7 → #0369a1` | Gradient button |
| Secondary Button | White with `#0284c7` border | Outlined button |
| Link | `#0284c7` | Footer links |

### Typography Sizes
| Element | Size | Weight | Line Height |
|---------|------|--------|------------|
| Title | 2.5rem (40px) | 700 | 1.2 |
| Code Badge | 1.2rem (19px) | 600 | 1.0 |
| Description | 1.1rem (18px) | 400 | 1.8 |
| Button | 1rem (16px) | 600 | 1.0 |
| Footer | 0.95rem (15px) | 400 | 1.6 |

### Spacing Measurements
```
Desktop Layout (768px+):
┌─────────────────────────────┐
│ Container: max-width 600px  │
│ Padding: 60px horizontal,   │
│          40px vertical      │
│                             │
│ Icon: 96px size             │
│ Margin bottom: 30px         │
│                             │
│ Badge margin: 20px bottom   │
│ Title margin: 20px bottom   │
│                             │
│ Description margin: 40px    │
│ button                      │
│                             │
│ Button gap: 15px            │
│ Button padding: 14px 32px   │
│                             │
│ Footer margin-top: 50px     │
│ Footer padding-top: 30px    │
│ Border-top: 1px solid       │
└─────────────────────────────┘

Mobile Layout (≤480px):
┌──────────────────┐
│ Padding: 30px    │
│ Title: 1.5rem    │
│ Icon: 64px       │
│ Description:     │
│  margin 30px     │
│                  │
│ Buttons:         │
│ Stack vertical   │
│ Width: 100%      │
│ gap: 10px        │
└──────────────────┘
```

### Icon Specifications
- **Icon Library**: Bootstrap Icons
- **Icon**: `bi bi-exclamation-circle`
- **Size**: 96px (desktop), 64px (mobile)
- **Color**: #0284c7 (Cyan)
- **Animation**: Float (0-15px vertical, 3s loop)

### Button States

#### Primary Button
```
Normal State:
  Background: Linear gradient #0284c7 → #0369a1
  Color: White
  Padding: 14px 32px
  Border-radius: 12px
  Box-shadow: 0 8px 20px rgba(2, 132, 199, 0.3)

Hover State:
  Transform: translateY(-3px)
  Box-shadow: 0 12px 30px rgba(2, 132, 199, 0.4)
  Gradient: #0369a1 → #0c4a6e

Active State:
  Transform: none
  Box-shadow: reduced
```

#### Secondary Button
```
Normal State:
  Background: White
  Color: #0284c7
  Border: 2px solid #0284c7
  Padding: 14px 32px

Hover State:
  Background: #f0f9ff
  Border-color: #0369a1
  Color: #0369a1
  Box-shadow: 0 8px 20px rgba(2, 132, 199, 0.15)
  Transform: translateY(-3px)
```

---

## 403 - Access Forbidden

### Visual Hierarchy
```
╔═══════════════════════════════════════╗
║    Full-width Gradient Background     ║
║ (Light Amber: #FEF3C7 → #FED7AA)    ║
║                                       ║
║    ┌─────────────────────────────┐   ║
║    │   White Content Card         │   ║
║    │                             │   ║
║    │  🔒 (Lock Icon - Filled)   │   ║
║    │   Floating animation        │   ║
║    │                             │   ║
║    │   403                       │   ║
║    │   (Warning badge)           │   ║
║    │                             │   ║
║    │  Accesso Negato             │   ║
║    │  (Large, bold heading)      │   ║
║    │                             │   ║
║    │  Non hai i permessi...      │   ║
║    │  (Description paragraph)    │   ║
║    │                             │   ║
║    │  [Torna alla Home] [Richiedi] │   ║
║    │   Primary Button | Secondary │   ║
║    │                             │   ║
║    │  ╭─────────────────────╮   │   ║
║    │  │ Permission Info Box  │   │   ║
║    │  ╰─────────────────────╯   │   ║
║    │                             │   ║
║    │  ─────────────────────────  │   ║
║    │  Footer with support link   │   ║
║    └─────────────────────────────┘   ║
║                                       ║
╚═══════════════════════════════════════╝
```

### Color Palette
| Element | Color | Usage |
|---------|-------|-------|
| Background | `#FEF3C7` | Primary light amber |
| Gradient | `#FED7AA` | Secondary amber |
| Icon | `#d97706` | Amber-600 |
| Title | `#92400e` | Dark amber |
| Description | `#75570a` | Warm brown |
| Code Badge | `#d97706` bg with 0.1 opacity | Warning badge |
| Primary Button | `#d97706 → #b45309` | Amber gradient |
| Secondary Button | White with `#d97706` border | Outlined |
| Info Box | `rgba(217, 119, 6, 0.05)` | Light background |
| Border (Info) | `#d97706` | 4px left border |

### Typography Sizes
| Element | Size | Weight | Line Height |
|---------|------|--------|------------|
| Title | 2.5rem (40px) | 700 | 1.2 |
| Code Badge | 1.2rem (19px) | 600 | 1.0 |
| Description | 1.1rem (18px) | 400 | 1.8 |
| Info Box Text | 0.95rem (15px) | 400 | 1.6 |
| Button | 1rem (16px) | 600 | 1.0 |

### Icon Specifications
- **Icon Library**: Bootstrap Icons
- **Icon**: `bi bi-lock-fill` (solid lock)
- **Size**: 96px (desktop), 64px (mobile)
- **Color**: #d97706 (Amber)
- **Animation**: Float (0-15px vertical, 3s loop)

### Unique Elements

#### Permission Info Box
```
┌─────────────────────────────┐
│ ▮ Nota: (left border accent) │
│                             │
│ Se credi di avere diritto  │
│ a questa risorsa,          │
│ contatta l'amministratore  │
│ con il tuo ID utente.      │
└─────────────────────────────┘

Styles:
  Background: rgba(217, 119, 6, 0.05)
  Border-left: 4px solid #d97706
  Padding: 15px
  Border-radius: 8px
  Margin: 30px 0 0 0
  Font-size: 0.95rem
  Color: #75570a
```

---

## 500 - Server Error

### Visual Hierarchy
```
╔═══════════════════════════════════════╗
║    Full-width Gradient Background     ║
║  (Light Red: #FEE2E2 → #FECACA)     ║
║                                       ║
║    ┌─────────────────────────────┐   ║
║    │   White Content Card         │   ║
║    │                             │   ║
║    │  ⚠️ (Triangle Exclamation) │   ║
║    │   Floating animation        │   ║
║    │                             │   ║
║    │   500                       │   ║
║    │   (Error badge)             │   ║
║    │                             │   ║
║    │  Errore del Server          │   ║
║    │  (Large, bold heading)      │   ║
║    │                             │   ║
║    │  Siamo spiacenti...         │   ║
║    │  (Description paragraph)    │   ║
║    │                             │   ║
║    │  [Riprova] [Contatta Supp.] │   ║
║    │   Primary | Secondary        │   ║
║    │                             │   ║
║    │  ✓ Status message            │   ║
║    │  (System is tracking)       │   ║
║    │                             │   ║
║    │  ╭─────────────────────╮   │   ║
║    │  │ Error Tracking ID    │   │   ║
║    │  │ ERR-20260908095300   │   │   ║
║    │  ╰─────────────────────╯   │   ║
║    │                             │   ║
║    │  Status | FAQ | Contact     │   ║
║    └─────────────────────────────┘   ║
║                                       ║
╚═══════════════════════════════════════╝
```

### Color Palette
| Element | Color | Usage |
|---------|-------|-------|
| Background | `#FEE2E2` | Primary light red |
| Gradient | `#FECACA` | Secondary red |
| Icon | `#ef4444` | Red-500 |
| Title | `#7f1d1d` | Dark red |
| Description | `#991b1b` | Maroon |
| Primary Button | `#ef4444 → #dc2626` | Red gradient |
| Secondary Button | White with `#ef4444` border | Outlined |
| Error Box | `rgba(239, 68, 68, 0.05)` | Light red bg |
| Error Border | `rgba(239, 68, 68, 0.2)` | Error box border |
| Status Box | `rgba(34, 197, 94, 0.08)` | Success green (positive) |
| Status Border | `#22c55e` | Green (tracking OK) |

### Typography Sizes
| Element | Size | Weight | Line Height |
|---------|------|--------|------------|
| Title | 2.5rem (40px) | 700 | 1.2 |
| Code Badge | 1.2rem (19px) | 600 | 1.0 |
| Description | 1.1rem (18px) | 400 | 1.8 |
| Tracking Label | 0.9rem (14px) | 600 | 1.4 |
| Tracking ID | 0.9rem (14px) | 400 | 1.5 |
| Status Message | 0.95rem (15px) | 400 | 1.6 |

### Icon Specifications
- **Icon Library**: Bootstrap Icons
- **Icon**: `bi bi-exclamation-triangle-fill` (solid triangle)
- **Size**: 96px (desktop), 64px (mobile)
- **Color**: #ef4444 (Red)
- **Animation**: Float (0-15px vertical, 3s loop)

### Unique Elements

#### Status Message
```
┌─────────────────────────────┐
│ ✓ Siamo spiacenti...        │
│   System is tracking        │
│   error, working to fix     │
└─────────────────────────────┘

Styles:
  Background: rgba(34, 197, 94, 0.08)
  Border-left: 4px solid #22c55e
  Color: #166534
  Padding: 12px 15px
  Border-radius: 6px
  Font-size: 0.95rem
```

#### Error Tracking Box
```
┌─────────────────────────────┐
│ ID Tracciamento Errore      │
│ (share with support)        │
│                             │
│ ┌────────────────────────┐ │
│ │ ERR-20260908095300     │ │
│ │ (Courier New monospace)│ │
│ └────────────────────────┘ │
└─────────────────────────────┘

Styles:
  Background: rgba(239, 68, 68, 0.05)
  Border: 1px solid rgba(239, 68, 68, 0.2)
  Padding: 15px
  Border-radius: 8px
  Margin: 30px 0 0 0
  Font-size: 0.9rem

ID Format:
  ERR-[YYYYMMDDHHmmss]
  Example: ERR-20260908095300
  (Generated via Django template tag)
```

---

## Shared Design Principles

### Animations

#### Slide-Up (Entry Animation)
```
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);  /* 30px below */
  }
  to {
    opacity: 1;
    transform: translateY(0);     /* final position */
  }
  Duration: 0.6s
  Easing: ease-out
}
```

#### Float (Icon Animation)
```
@keyframes float {
  0%, 100% {
    transform: translateY(0px);   /* baseline */
  }
  50% {
    transform: translateY(-15px); /* 15px up */
  }
  Duration: 3s (infinite)
  Easing: ease-in-out
}
```

### Transitions

All interactive elements use:
```css
transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
/* 
  0.3s = moderate, not rushed
  cubic-bezier = professional easing
  "all" = smooth across all properties
*/
```

### Shadow Hierarchy

| Level | CSS | Use Case |
|-------|-----|----------|
| Light | `0 1px 3px rgba(0,0,0,0.05)` | Cards at rest |
| Medium | `0 4px 12px rgba(0,0,0,0.1)` | Hover state |
| Dark | `0 10px 40px rgba(0,0,0,0.15)` | Container shadow |
| Button | Varies by color (20-30px spread) | Primary buttons |

### Focus States

```css
/* Keyboard accessibility */
.error-btn:focus {
  outline: 2px solid [COLOR];       /* color matches theme */
  outline-offset: 2px;              /* visible gap */
}
```

### Accessibility Standards

1. **Color Contrast**: All text ≥ 4.5:1 (WCAG AA)
2. **Font Size**: Minimum 16px (mobile friendly)
3. **Touch Target**: Minimum 48x48px buttons
4. **Focus Indicators**: Visible on all interactive elements
5. **Semantic HTML**: Proper heading hierarchy
6. **Icon Labels**: Descriptive text always present

---

## Responsive Breakpoints

### Desktop (768px+)
```
Full design with:
- 2.5rem headings
- 96px icons
- 60px horizontal padding
- Horizontal button layout
```

### Tablet (481-767px)
```
Adjusted layout:
- 1.8rem headings
- 72px icons
- 40px padding
- Flexible button layout
```

### Mobile (≤480px)
```
Optimized mobile:
- 1.5rem headings
- 64px icons
- 30px padding
- Vertical button stacking
- 100% width buttons
```

---

## Browser Support

| Browser | Desktop | Mobile | Notes |
|---------|---------|--------|-------|
| Chrome | 90+ | 70+ | Full support |
| Firefox | 88+ | 68+ | Full support |
| Safari | 14+ | 12+ | Full support |
| Edge | 90+ | N/A | Full support |
| IE 11 | ✗ | N/A | Graceful degradation (no animations) |

### Graceful Degradation
- No CSS animations = static, still readable
- Gradients = fallback solid colors
- Flexbox = flex-direction, flex-wrap work on older browsers
- Content is always accessible
