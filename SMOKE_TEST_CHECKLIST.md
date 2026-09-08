# EHModuli Manual Smoke Test Checklist
**Date**: 2026-09-08  
**Version**: Phase 3 - UI Polish & Design System  
**Status**: Ready for Production Verification

---

## CRITICAL PASS/FAIL ITEMS (Must ALL Pass)

- [ ] **CRITICAL 1**: Mandatory docs prevent "Avanti" button (disabled state)
- [ ] **CRITICAL 2**: Timeline modal opens as proper centered popup (not fullscreen)
- [ ] **CRITICAL 3**: Partial submission shows TWO buttons in summary
- [ ] **CRITICAL 4**: Upload Guide FAB visible on dashboard; modal can be suppressed
- [ ] **CRITICAL 5**: Error pages display (404, 403, 500) with correct themes
- [ ] **CRITICAL 6**: Focus indicators visible on all interactive elements (3px blue outline)
- [ ] **CRITICAL 7**: Tab navigation trapped within modals (doesn't escape)

---

## TEST 1: MANDATORY DOCUMENT VALIDATION

**Objective**: Verify that "Avanti" button is disabled until all required documents are uploaded or marked unavailable.

### Setup
- Access a form assignment with at least one mandatory document
- Ensure form has multiple steps (to have an "Avanti" button, not "Go to Summary")

### Step-by-Step Checks

**1.1 Button State on Page Load**
- [ ] Page loads with form step displayed
- [ ] "Avanti" button is DISABLED (grayed out, not clickable)
- [ ] Cursor changes to `not-allowed` when hovering over button
- [ ] Button has visual disabled state (opacity reduced or color dimmed)

**1.2 After Uploading ONE Required Document**
- [ ] Click on upload dropzone or drag-drop a file
- [ ] File upload completes successfully
- [ ] Success message appears (green alert with file name and size)
- [ ] Document status shows as "Salvato"
- [ ] "Avanti" button becomes ENABLED (no longer grayed out)
- [ ] Button cursor changes back to pointer
- [ ] Button can now be clicked

**1.3 After Removing Document (Optional)**
- [ ] If UI allows file removal, delete the uploaded document
- [ ] Button should return to DISABLED state

**1.4 With "Not Available" Declaration**
- [ ] Click "Non hai questo documento?" link
- [ ] Absence Declaration modal opens (see TEST 5 for modal verification)
- [ ] Upload formal declaration file (PDF, DOCX, etc.)
- [ ] Check "Dichiaro e attesto..." checkbox
- [ ] Click "Salva Dichiarazione Formale"
- [ ] Modal closes and document shows as "Dichiarazione Acquisita"
- [ ] "Avanti" button becomes ENABLED

**1.5 Multiple Required Documents**
- [ ] If form has multiple required docs in same step:
  - [ ] Button remains disabled while ANY required doc is missing
  - [ ] After uploading first doc, button still disabled
  - [ ] After uploading ALL required docs, button becomes enabled

**1.6 Clicking "Avanti" When Enabled**
- [ ] Navigate to next form step successfully
- [ ] No errors appear
- [ ] Progress bar updates correctly

---

## TEST 2: TIMELINE MODAL (POPUP BEHAVIOR)

**Objective**: Verify timeline modal displays as centered popup, not fullscreen or broken layout.

### Setup
- Go to client dashboard (logged in as customer/client)
- Find a product card with "Storico" badge visible

### Step-by-Step Checks

**2.1 Opening the Modal**
- [ ] "Storico" badge is visible on product card
- [ ] Click the badge
- [ ] Modal appears with smooth animation (fade-in)
- [ ] Modal is centered on screen (not fullscreen)
- [ ] Modal has visible backdrop (dark area behind modal)
- [ ] Modal is not confined to card boundaries (overlays entire viewport)

**2.2 Modal Content & Layout**
- [ ] Title is visible at top
- [ ] Timeline events are displayed in chronological order
- [ ] Each event has icon, title, and timestamp
- [ ] Event descriptions are readable
- [ ] Scrollbar appears if content exceeds modal height
- [ ] No text overflow or broken layout within modal

**2.3 Closing via Close Button**
- [ ] X button is visible in modal header
- [ ] Click X button
- [ ] Modal closes smoothly
- [ ] Backdrop disappears
- [ ] Focus returns to the product card that opened it

**2.4 Closing via Backdrop Click**
- [ ] Click on the dark area (backdrop) outside modal
- [ ] Modal closes immediately
- [ ] No action is triggered on card behind modal

**2.5 Closing via Escape Key**
- [ ] With modal open, press Escape key
- [ ] Modal closes without side effects
- [ ] Focus management works correctly

**2.6 Multiple Modals (Different Products)**
- [ ] Open timeline for one product
- [ ] Close it
- [ ] Open timeline for different product
- [ ] Verify new timeline displays correctly
- [ ] No data from previous timeline appears

**2.7 Modal Accessibility**
- [ ] Modal has proper z-index (appears above page content)
- [ ] Tab navigation within modal works
- [ ] Aria-labels and semantic HTML present
- [ ] Focus trap active (Tab doesn't escape to background)

---

## TEST 3: PARTIAL SUBMISSION (TWO-BUTTON SUMMARY)

**Objective**: Verify partial submission UI shows two distinct buttons and saves draft correctly.

### Setup
- Have an incomplete form (some but not all documents uploaded)
- Navigate to form summary page

### Step-by-Step Checks

**3.1 Summary Page Layout**
- [ ] Page title shows "Verifica e Conferma Invio"
- [ ] Uploaded documents list displays correctly
- [ ] Security notice visible (green box with shield icon)
- [ ] Awareness declaration checkbox visible (large yellow box)

**3.2 Two Buttons Present**
- [ ] LEFT button: "Salva Bozza / Invio Parziale" (outline style, gray)
- [ ] RIGHT button: "Invia Documenti" (solid green, right-aligned)
- [ ] Buttons are side-by-side (flex layout, responsive on mobile)
- [ ] Button spacing is consistent

**3.3 Salva Bozza Button Behavior**
- [ ] Button is always ENABLED (even without awareness checkbox)
- [ ] Click "Salva Bozza"
- [ ] Modal opens with title "Salva come Bozza?"
- [ ] Modal shows warning: "Questa non è una trasmissione completa..."
- [ ] Two buttons in modal: "Annulla" and "Conferma"

**3.4 Confirming Partial Submission**
- [ ] In modal, click "Conferma"
- [ ] Modal closes
- [ ] Redirect to success page
- [ ] Success page has BLUE theme (not green)
- [ ] Page title says "Bozza Salvata" (not "Modulo Inviato")
- [ ] Icon is blue/purple (not green checkmark)
- [ ] Message explains draft saved and can be resumed later

**3.5 Success Page for Partial Submission**
- [ ] Heading: "Bozza Salvata con Successo"
- [ ] Subtext: "La tua documentazione è stata salvata in bozza..."
- [ ] Background gradient includes blue tones
- [ ] CTA button text: "Torna al Dashboard" or "Accedi al Portal"

**3.6 Back Button Cancels Draft**
- [ ] From summary, click "Indietro"
- [ ] Return to previous form step
- [ ] No draft saved in this case

**3.7 Invia Documenti (Full Submission)**
- [ ] Leave Awareness checkbox UNCHECKED
- [ ] "Invia Documenti" button is DISABLED (opacity 0.5)
- [ ] Button title/tooltip shows: "Spunta la dichiarazione..."
- [ ] Click on checkbox
- [ ] Button becomes ENABLED (full opacity)
- [ ] Click "Invia Documenti"
- [ ] Confirmation modal appears
- [ ] After confirmation, redirect to success page with GREEN theme

---

## TEST 4: UPLOAD GUIDE MODAL (FAB & FIRST-VISIT)

**Objective**: Verify upload guide FAB and first-visit modal behavior.

### Setup
- Clear browser cache/localStorage (or use private/incognito window)
- Log into client portal as new customer

### Step-by-Step Checks

**4.1 FAB Visibility**
- [ ] FAB button visible in bottom-right corner
- [ ] FAB text: "Guida Upload" (or similar)
- [ ] FAB has icon (cloud, upload, or info icon)
- [ ] FAB has hover effect (slightly raises, changes color)
- [ ] FAB has focus indicator when tabbed to (blue 3px outline)

**4.2 First-Visit Automatic Modal**
- [ ] On first dashboard visit, modal auto-opens (no click needed)
- [ ] Modal title: "Guida al Caricamento dei Documenti"
- [ ] Modal has 5 sections visible in order:
  1. **Preparati** - Info about preparing documents
  2. **Carica** - How to upload files
  3. **Documenti Richiesti** - Which docs are required
  4. **Non Disponibile** - How to declare unavailable docs
  5. **Conclusione** - Final notes
- [ ] Each section is clearly separated
- [ ] Text is readable and well-formatted
- [ ] Icons accompany each section

**4.3 Modal Controls**
- [ ] X button visible in header
- [ ] "Non mostrare più" checkbox visible at bottom
- [ ] Checkbox is unchecked by default
- [ ] Close button text: "Ho Capito" or "Chiudi"

**4.4 Suppress Modal Checkbox**
- [ ] Check "Non mostrare più" checkbox
- [ ] Checkbox gets visual feedback (color change)
- [ ] Click close or press Escape
- [ ] Modal closes

**4.5 Refresh Page - Modal Suppressed**
- [ ] Refresh page (F5 or Ctrl+R)
- [ ] Modal does NOT auto-open again
- [ ] FAB is still visible in bottom-right

**4.6 Manual FAB Click**
- [ ] Click FAB button
- [ ] Modal opens with same content as first-visit
- [ ] Modal can be opened multiple times
- [ ] Closing and reopening FAB works repeatedly

**4.7 Modal Accessibility**
- [ ] Modal has proper z-index (above page content)
- [ ] Tab navigation trapped within modal
- [ ] Close button accessible via keyboard
- [ ] Escape key closes modal
- [ ] Focus returns to FAB after modal closes

---

## TEST 5: ABSENCE DECLARATION MODAL

**Objective**: Verify formal absence declaration functionality.

### Setup
- On a form step with at least one mandatory optional document
- Click "Non hai questo documento?" link

### Step-by-Step Checks

**5.1 Modal Opens Correctly**
- [ ] Modal title: "Dichiarazione Formale di Assenza"
- [ ] Subtitle shows document name
- [ ] Info warning box explains requirement for letterhead + stamp + signature
- [ ] Modal is centered (not fullscreen)

**5.2 File Upload Area**
- [ ] File input accepts: PDF, DOCX, DOC, JPG, PNG
- [ ] Drag-drop zone has dashed border
- [ ] Label shows file formats and max 10MB
- [ ] File selection shows with checkmark after selection

**5.3 Motivazione Text Area**
- [ ] "Motivazione o Note Aggiuntive" field present
- [ ] Field is optional (no asterisk)
- [ ] Placeholder shows example text
- [ ] Text can be entered

**5.4 Legal Attestation Checkbox**
- [ ] Large yellow box with border around checkbox
- [ ] Checkbox says: "Dichiaro e attesto che il documento allegato costituisce..."
- [ ] Box changes color when checked (green background)
- [ ] Badge updates from warning to success

**5.5 Submit Button**
- [ ] Button: "Salva Dichiarazione Formale"
- [ ] Button is DISABLED until:
  - [ ] File is selected AND checkbox is checked (for mandatory)
  - [ ] OR checkbox is checked (for optional with file)
  - [ ] OR notes are entered (for optional without file)
- [ ] Click to submit

**5.6 Success Feedback**
- [ ] After submit, document status changes to "Dichiarazione Acquisita" (yellow badge)
- [ ] If file was attached, shows filename and size
- [ ] If no file, shows justification reason
- [ ] Modal closes automatically
- [ ] "Avanti" button becomes enabled

---

## TEST 6: ERROR PAGES (404, 403, 500)

**Objective**: Verify error pages display with correct themes and designs.

### Setup
- Have access to test URLs that trigger errors
- Or intentionally cause errors

### Step-by-Step Checks

**6.1 404 Page (Not Found)**
- [ ] Navigate to non-existent URL: `/modules/nonexistent-page/`
- [ ] 404 page displays
- [ ] Title: "Pagina Non Trovata" or "404 - Not Found"
- [ ] Primary color: BLUE (#0d6efd or similar)
- [ ] Icon: Large "404" or empty folder icon
- [ ] Message explains page doesn't exist
- [ ] Action buttons visible:
  - [ ] "Torna al Dashboard" button
  - [ ] "Torna a Inizio" or "Home" button
- [ ] Button colors: Blue primary, gray secondary
- [ ] Background design matches brand (subtle gradient)

**6.2 403 Page (Forbidden/Access Denied)**
- [ ] Try to access page without permission (e.g., another user's form)
- [ ] 403 page displays
- [ ] Title: "Accesso Negato" or "403 - Forbidden"
- [ ] Primary color: ORANGE/AMBER (#f59e0b or similar)
- [ ] Icon: Lock icon or prohibition symbol
- [ ] Message explains access is denied
- [ ] Reasons listed (if applicable):
  - [ ] Insufficient permissions
  - [ ] Assignment expired
  - [ ] Not logged in
- [ ] Action buttons visible
- [ ] Button colors: Orange/Amber for primary

**6.3 500 Page (Server Error)**
- [ ] Cause an unhandled exception (if possible for testing)
- [ ] 500 page displays
- [ ] Title: "Errore del Server" or "500 - Internal Server Error"
- [ ] Primary color: RED (#dc3545 or similar)
- [ ] Icon: Warning/danger symbol
- [ ] Message explains something went wrong
- [ ] Error tracking ID visible: "ERR-YYYYMMDDHHMMSS" format
- [ ] Instructions to contact support with error ID
- [ ] Action buttons:
  - [ ] "Riprova" (Retry) button
  - [ ] "Contatta il Supporto" (Contact Support) button
- [ ] Button colors: Red primary, gray secondary

**6.4 Error Page Accessibility**
- [ ] Page title is meaningful (not generic "Error")
- [ ] Headings hierarchy correct (h1, then h2)
- [ ] Buttons have focus indicators (blue 3px outline)
- [ ] Text contrast meets WCAG AA standards
- [ ] Page is responsive (mobile, tablet, desktop)
- [ ] No horizontal scroll on any device

---

## TEST 7: ACCESSIBILITY

**Objective**: Verify keyboard navigation, focus indicators, and screen reader support.

### Setup
- Use keyboard only (no mouse)
- Open browser DevTools to inspect focus styles

### Step-by-Step Checks

**7.1 Focus Indicators on Interactive Elements**
- [ ] Tab through page
- [ ] All buttons show BLUE 3px outline when focused
- [ ] All links show focus indicator
- [ ] All inputs show focus indicator
- [ ] Focus outline is clearly visible against background
- [ ] Outline is not hidden behind other elements

**7.2 Tab Navigation Order**
- [ ] Tab key moves through elements in logical order
- [ ] Reverse tab (Shift+Tab) works correctly
- [ ] Focus order matches visual layout (top-to-bottom, left-to-right)
- [ ] No skipped elements
- [ ] Hidden elements are skipped (not focusable)

**7.3 Modal Focus Trap**
- [ ] Open any modal (absence declaration, upload guide, etc.)
- [ ] Tab within modal
- [ ] Focus cycles only within modal content
- [ ] Tabbing does NOT escape to background elements
- [ ] Shift+Tab cycles backward within modal only
- [ ] Pressing Escape closes modal and returns focus to trigger button

**7.4 Form Elements**
- [ ] All required fields marked with asterisk (*)
- [ ] Input labels are associated with inputs (click label focuses input)
- [ ] File inputs are accessible via keyboard
- [ ] Checkboxes are focusable and toggleable with Space
- [ ] Radio buttons are accessible
- [ ] Textarea focus works

**7.5 Buttons & Links**
- [ ] All buttons focusable with Tab
- [ ] All links focusable with Tab
- [ ] Disabled buttons not focusable
- [ ] Space/Enter activates focused button
- [ ] Enter activates focused link

**7.6 Color Contrast**
- [ ] Text contrast meets WCAG AA (4.5:1 for normal text, 3:1 for large text)
- [ ] Check using browser DevTools or accessibility checker
- [ ] Error messages in red are visible
- [ ] Success messages in green are visible
- [ ] Warning messages in yellow have sufficient contrast

**7.7 Semantic HTML**
- [ ] Page structure uses proper headings (h1, h2, h3, etc.)
- [ ] No heading levels skipped (don't jump from h2 to h4)
- [ ] Lists use `<ul>` / `<ol>` / `<li>` tags
- [ ] Form uses `<form>`, `<label>`, `<input>` correctly
- [ ] Buttons are `<button>` not styled `<div>`

---

## TEST 8: UPLOAD FUNCTIONALITY

**Objective**: Verify file upload works correctly with validation and drag-drop.

### Setup
- Access a form step with document uploads
- Prepare test files (PDF, DOCX, JPG, PNG)

### Step-by-Step Checks

**8.1 Click-to-Upload**
- [ ] Click on upload dropzone
- [ ] File browser opens
- [ ] Select a valid file
- [ ] File uploads with loading spinner
- [ ] Upload completes and success message appears
- [ ] File name and size displayed
- [ ] Green success badge shown

**8.2 Drag-and-Drop Upload**
- [ ] Drag file over dropzone
- [ ] Dropzone changes style (border color to red, background tint)
- [ ] Drop file on dropzone
- [ ] Upload starts with loading indicator
- [ ] Upload completes successfully
- [ ] Dropzone style returns to normal

**8.3 File Validation**
- [ ] Try uploading unsupported file type (e.g., .exe, .zip)
- [ ] Error message appears
- [ ] File is not uploaded
- [ ] User can try again
- [ ] Try uploading file > 10MB
- [ ] Error message: "File troppo grande"
- [ ] File is rejected

**8.4 Multiple Files**
- [ ] Upload file to requirement 1
- [ ] Upload different file to requirement 2
- [ ] Both files show as uploaded
- [ ] Each has its own success message
- [ ] Files are independent

**8.5 Replace File**
- [ ] Upload a file
- [ ] Upload different file to same requirement
- [ ] Old file is replaced (or shown as superseded)
- [ ] Only latest file remains

---

## TEST 9: UI CONSISTENCY

**Objective**: Verify visual consistency across the application.

### Setup
- Navigate through multiple pages
- Check different device sizes (desktop, tablet, mobile)

### Step-by-Step Checks

**9.1 Button Styles**
- [ ] All buttons have rounded corners (min-radius 8px)
- [ ] Primary buttons: green (#2D8A4E)
- [ ] Secondary buttons: gray outline
- [ ] Danger/Warning buttons: red/orange
- [ ] Buttons have hover effects (color shift or shadow)
- [ ] Buttons have active/pressed state
- [ ] Disabled buttons appear grayed out

**9.2 Cards & Containers**
- [ ] All cards have subtle shadow
- [ ] Card corners are rounded (12-16px)
- [ ] Cards maintain consistent spacing
- [ ] Hover effects on interactive cards
- [ ] No sharp corners anywhere in UI

**9.3 Input Fields**
- [ ] All inputs have rounded corners (8px)
- [ ] Input focus shows blue ring (3px)
- [ ] Placeholder text is visible and muted
- [ ] Required fields marked with red asterisk
- [ ] Error states show red border and red error text
- [ ] Success states show green checkmark

**9.4 Colors**
- [ ] Primary color: Green (#2D8A4E)
- [ ] Accent colors: Red (#E8847D), Blue (#0d6efd)
- [ ] Success: Green (#12b76a)
- [ ] Warning: Amber (#f59e0b)
- [ ] Error: Red (#dc3545)
- [ ] Text: Dark gray (#1d2939)
- [ ] Background: Off-white (#f9fafb)
- [ ] Borders: Light gray (#d0d5dd)

**9.5 Typography**
- [ ] Font family: Inter or system font stack
- [ ] Headings bold and larger (h1 > h2 > h3)
- [ ] Body text readable (16px min on desktop, 14px on mobile)
- [ ] Line height sufficient (1.5 or higher)
- [ ] All text has sufficient contrast

**9.6 Icons**
- [ ] All icons are consistent size (or intentionally varied)
- [ ] Icon colors match button/text colors
- [ ] Icons are properly aligned with text
- [ ] Icons load correctly (no broken images)
- [ ] Icon set is from Bootstrap Icons (or consistent source)

**9.7 Spacing**
- [ ] Consistent padding inside cards (16-20px)
- [ ] Consistent margin between sections (24-32px)
- [ ] Form fields have consistent spacing (16px gap)
- [ ] Button groups have consistent spacing (8px gap)
- [ ] No unexpected whitespace or cramping

**9.8 Responsive Design**
- [ ] Test on mobile (375px width)
- [ ] Test on tablet (768px width)
- [ ] Test on desktop (1024px+ width)
- [ ] Layout adjusts properly at breakpoints
- [ ] No horizontal scrolling
- [ ] Touch targets are large enough (44px min)
- [ ] Buttons stack on mobile if needed

---

## TEST 10: PERFORMANCE

**Objective**: Verify performance is acceptable and no N+1 query issues.

### Setup
- Open DevTools Network tab
- Open DevTools Console to check for errors
- Use Network throttling (Fast 3G or Slow 3G) for realistic testing

### Step-by-Step Checks

**10.1 Page Load Times**
- [ ] Dashboard loads in < 2 seconds
- [ ] Form step loads in < 1.5 seconds
- [ ] Summary page loads in < 1.5 seconds
- [ ] Success page loads immediately

**10.2 API Responses**
- [ ] No excessive API calls
- [ ] Batch requests used where appropriate
- [ ] Response payloads are reasonably sized (< 500KB for forms)
- [ ] No duplicate API calls detected

**10.3 File Upload**
- [ ] File upload shows progress
- [ ] 5MB file uploads in < 10 seconds
- [ ] No timeout errors
- [ ] Large file (9.5MB) rejected gracefully

**10.4 Form Navigation**
- [ ] Clicking "Avanti" navigates instantly (no lag)
- [ ] Page transitions are smooth
- [ ] Progress bar updates without stutter

**10.5 Database Queries**
- [ ] Open Network tab in DevTools
- [ ] Check server logs (if available)
- [ ] Verify no N+1 query patterns
- [ ] Admin dashboard doesn't show multiple queries per item

**10.6 Memory Usage**
- [ ] Opening/closing modals doesn't leak memory
- [ ] Navigating back and forth doesn't accumulate memory
- [ ] No console errors about memory or performance

---

## TEST 11: PASSWORD/SECURITY FEATURES

**Objective**: Verify password handling and security fixes.

### Setup
- Reopen a closed form assignment (if portal_password feature enabled)
- Try accessing form without password

### Step-by-Step Checks

**11.1 Portal Password Protection**
- [ ] When reopening form, portal password prompt appears (if configured)
- [ ] Password field is masked (dots, not visible text)
- [ ] Password validation works
- [ ] Correct password allows access
- [ ] Wrong password shows error message
- [ ] Error message doesn't leak information (generic "invalid")

**11.2 Password Display**
- [ ] Password is never shown in HTML source
- [ ] Password is never logged in console
- [ ] Password field has autocomplete disabled
- [ ] No password hints visible

---

## TEST 12: FORM DATA HANDLING

**Objective**: Verify form data is correctly saved and retrieved.

### Setup
- Start a form
- Fill in various fields and upload documents
- Navigate between steps

### Step-by-Step Checks

**12.1 Data Persistence**
- [ ] Fill in text field
- [ ] Go to next step
- [ ] Go back to previous step
- [ ] Text field still contains entered data
- [ ] Uploaded documents still visible

**12.2 Form Element Types**
- [ ] Text fields save correctly
- [ ] Email fields validate and save
- [ ] Phone fields save
- [ ] Date fields save in correct format
- [ ] Checkboxes maintain state
- [ ] Awareness declarations save

**12.3 Manifests & File Organization**
- [ ] NAS folder structure created correctly
- [ ] Manifest files saved and readable
- [ ] No corrupted JSON in manifests
- [ ] File organization matches form structure

---

## TESTING SUMMARY TEMPLATE

Use this template to record results:

### Device/Browser
- [ ] **Browser**: Chrome / Firefox / Safari / Edge
- [ ] **Version**: ___________
- [ ] **OS**: Windows / macOS / Linux
- [ ] **Screen Size**: Desktop / Tablet / Mobile

### Results
- [ ] **Total Checks**: ___ / ___
- [ ] **Passed**: ___
- [ ] **Failed**: ___
- [ ] **Blocked/N/A**: ___

### Failed Items
```
1. [TEST #]: [Item name]
   Issue: [Description of what failed]
   Steps to reproduce: [Exact steps]
   Expected: [What should happen]
   Actual: [What actually happened]
   Screenshot: [URL or file path if captured]

2. [TEST #]: [Item name]
   Issue: [Description]
   ...
```

### Blocked Items (Can't Test)
```
1. [TEST #]: [Item name]
   Reason: [Why can't test]
   Notes: [Additional context]
```

### Overall Assessment
- [ ] **PASS**: All critical items pass, minor issues only
- [ ] **CONDITIONAL PASS**: Critical items pass, but non-critical issues found (list below)
- [ ] **FAIL**: One or more critical items failed (list below)

### Issues Found
1. ___________
2. ___________
3. ___________

### Sign-Off
- **Tester Name**: ___________
- **Date**: ___________
- **Time Spent**: ___ hours
- **Recommendation**: Ready for Production / Needs Fixes / Needs More Testing

---

## QUICK START GUIDE

1. **Print this checklist** or open in editor
2. **Clone the repository** and set up local environment
3. **Start testing** with TEST 1 (Mandatory Document Validation)
4. **Work through each test sequentially** for logical flow
5. **Mark items as you go** (checkmark when verified)
6. **Take screenshots** of any failures for reference
7. **Document all issues** in the "Failed Items" section
8. **Report results** to development team with checklist completion
9. **If all critical items pass**, mark as production-ready

---

## NOTES FOR TESTERS

### Critical Tests (Must Complete)
- TEST 1: Mandatory Document Validation
- TEST 2: Timeline Modal
- TEST 3: Partial Submission
- TEST 4: Upload Guide FAB
- TEST 6: Error Pages
- TEST 7: Accessibility

### High-Value Tests (Should Complete)
- TEST 5: Absence Declaration
- TEST 8: Upload Functionality
- TEST 9: UI Consistency

### Optional Tests (If Time Permits)
- TEST 10: Performance
- TEST 11: Security Features
- TEST 12: Form Data Handling

### Test Environment
- Use staging/test server if available
- Create test user accounts for client portal
- Have test form assignments ready
- Prepare test documents (PDF, DOCX, JPG, PNG samples)

### Known Limitations
- Cannot test offline behavior with limited connectivity
- Browser-specific issues may vary (test at least Chrome + Firefox)
- Performance varies by network and hardware
- Mobile testing should use real device if possible

### Escalation Path
If critical items fail:
1. Document the issue thoroughly (steps, screenshots)
2. Assign to specific developer if applicable
3. Mark as BLOCKER in issue tracking system
4. Pause other testing until fix is verified
