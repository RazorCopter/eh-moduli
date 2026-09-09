import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const BASE_URL = (process.env.BASE_URL || 'http://app:8000').replace(/\/$/, '');
const SCREENSHOT_DIR = process.env.SCREENSHOT_DIR || '/work/collaudo/evidenze/ui';

const ADMIN_USER = 'collaudo_admin';
const ADMIN_PASS = 'Collaudo-Admin-Only-2026!';
const CUSTOMER_CODE = 'COLLAUDO-UI';
const CUSTOMER_PASS = 'Collaudo-Cliente-Only-2026!';
const CUSTOMER_EMPTY_CODE = 'COLLAUDO-EMPTY';
const ASSIGNMENT_ID = '50000000-0000-0000-0000-000000000001';

// Viewport profiles
const VIEWPORTS = {
  desktop: { width: 1280, height: 800, deviceScaleFactor: 1 },
  mobile_390: { width: 390, height: 844, deviceScaleFactor: 1, isMobile: true, hasTouch: true },
  mobile_360: { width: 360, height: 800, deviceScaleFactor: 1, isMobile: true, hasTouch: true },
  zoom_200: { width: 1280, height: 800, deviceScaleFactor: 2 },
};

fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

async function dismissIntroIfPresent(page) {
  try {
    await page.evaluate(() => {
      const intro = document.querySelector('etichub-intro');
      if (intro) intro.remove();
    });
  } catch (e) {}
}

async function captureScreen(browser, name, setupFn) {
  console.log(`\n=== Capturing Screen: ${name} ===`);
  for (const [vpName, vpConfig] of Object.entries(VIEWPORTS)) {
    const context = await browser.newContext({
      viewport: { width: vpConfig.width, height: vpConfig.height },
      deviceScaleFactor: vpConfig.deviceScaleFactor,
      isMobile: vpConfig.isMobile || false,
      hasTouch: vpConfig.hasTouch || false,
    });
    const page = await context.newPage();
    try {
      await setupFn(page, vpName);
      await dismissIntroIfPresent(page);
      await page.waitForTimeout(400);
      const outPath = path.join(SCREENSHOT_DIR, `${name}_${vpName}.png`);
      await page.screenshot({ path: outPath, fullPage: false });
      console.log(`  ✓ Saved: ${name}_${vpName}.png (${vpConfig.width}x${vpConfig.height} @${vpConfig.deviceScaleFactor}x)`);
    } catch (err) {
      console.error(`  ✗ Error capturing ${name}_${vpName}:`, err.message);
    } finally {
      await context.close();
    }
  }
}

async function run() {
  console.log(`Starting UI verification against ${BASE_URL}`);
  console.log(`Saving screenshots to: ${SCREENSHOT_DIR}`);

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
  });

  const results = [];

  // =========================================================================
  // SCHERMATA 1: Accesso Cliente (/modules/client/login/)
  // =========================================================================
  await captureScreen(browser, '01_login_cliente', async (page) => {
    await page.goto(`${BASE_URL}/modules/client/login/`, { waitUntil: 'networkidle' });
  });

  // 1. Keyboard Navigation on Login
  {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    await page.goto(`${BASE_URL}/modules/client/login/`, { waitUntil: 'networkidle' });
    await dismissIntroIfPresent(page);
    await page.focus('#id_code');
    await page.keyboard.type(CUSTOMER_CODE);
    await page.keyboard.press('Tab');
    await page.keyboard.type(CUSTOMER_PASS);
    await page.keyboard.press('Tab'); // focus on submit button or show password
    await page.waitForTimeout(300);
    const outPath = path.join(SCREENSHOT_DIR, '01_login_cliente_keyboard_focus.png');
    await page.screenshot({ path: outPath });
    console.log(`  ✓ Saved: 01_login_cliente_keyboard_focus.png`);
    await context.close();
  }

  // 1. Error state on Login
  {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    await page.goto(`${BASE_URL}/modules/client/login/`, { waitUntil: 'networkidle' });
    await dismissIntroIfPresent(page);
    await page.fill('#id_code', 'ERRATO_NON_ESISTE');
    await page.fill('#id_password', 'PasswordErrata123!');
    await page.click('button[type="submit"]');
    await page.waitForSelector('.login-error-alert', { timeout: 5000 });
    await page.waitForTimeout(300);
    const outPath = path.join(SCREENSHOT_DIR, '01_login_cliente_error_state.png');
    await page.screenshot({ path: outPath });
    console.log(`  ✓ Saved: 01_login_cliente_error_state.png`);
    await context.close();
  }

  // =========================================================================
  // SCHERMATA 2: Dashboard Cliente (/modules/client/dashboard/)
  // =========================================================================
  async function loginClient(page, code = CUSTOMER_CODE, pass = CUSTOMER_PASS) {
    await page.goto(`${BASE_URL}/modules/client/login/`, { waitUntil: 'networkidle' });
    await dismissIntroIfPresent(page);
    await page.fill('#id_code', code);
    await page.fill('#id_password', pass);
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle' }),
      page.click('button[type="submit"]'),
    ]);
  }

  await captureScreen(browser, '02_dashboard_cliente', async (page) => {
    await loginClient(page, CUSTOMER_CODE, CUSTOMER_PASS);
    await page.goto(`${BASE_URL}/modules/client/dashboard/`, { waitUntil: 'networkidle' });
  });

  // 2. Keyboard Navigation on Client Dashboard
  {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    await loginClient(page, CUSTOMER_CODE, CUSTOMER_PASS);
    await page.goto(`${BASE_URL}/modules/client/dashboard/`, { waitUntil: 'networkidle' });
    await dismissIntroIfPresent(page);
    // Tab into main CTA
    for (let i = 0; i < 4; i++) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(100);
    }
    const outPath = path.join(SCREENSHOT_DIR, '02_dashboard_cliente_keyboard_focus.png');
    await page.screenshot({ path: outPath });
    console.log(`  ✓ Saved: 02_dashboard_cliente_keyboard_focus.png`);
    await context.close();
  }

  // 2. Empty State on Client Dashboard
  {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    await loginClient(page, CUSTOMER_EMPTY_CODE, CUSTOMER_PASS);
    await page.goto(`${BASE_URL}/modules/client/dashboard/`, { waitUntil: 'networkidle' });
    await dismissIntroIfPresent(page);
    await page.waitForTimeout(300);
    const outPath = path.join(SCREENSHOT_DIR, '02_dashboard_cliente_empty_state.png');
    await page.screenshot({ path: outPath });
    console.log(`  ✓ Saved: 02_dashboard_cliente_empty_state.png`);
    await context.close();
  }

  // =========================================================================
  // SCHERMATA 3: Compilazione Modulo / Step (/modules/form/<id>/step/0/)
  // =========================================================================
  async function prepareFormStep(page) {
    await loginClient(page, CUSTOMER_CODE, CUSTOMER_PASS);
    // Open product view to ensure session grant
    await page.goto(`${BASE_URL}/modules/client/product/${ASSIGNMENT_ID}/`, { waitUntil: 'networkidle' });
    await page.goto(`${BASE_URL}/modules/form/${ASSIGNMENT_ID}/step/0/`, { waitUntil: 'networkidle' });
    await dismissIntroIfPresent(page);
  }

  await captureScreen(browser, '03_compilazione_step', async (page) => {
    await prepareFormStep(page);
  });

  // 3. Keyboard Navigation on Step
  {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    await prepareFormStep(page);
    // Tab to inputs
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);
    const outPath = path.join(SCREENSHOT_DIR, '03_compilazione_step_keyboard_focus.png');
    await page.screenshot({ path: outPath });
    console.log(`  ✓ Saved: 03_compilazione_step_keyboard_focus.png`);
    await context.close();
  }

  // 3. Validation / Required field state (disabled next button with tooltip when mandatory fields/docs missing)
  {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    await prepareFormStep(page);
    const nextBtn = await page.$('#nextStepBtn') || await page.$('button[type="submit"]');
    if (nextBtn) {
      await nextBtn.scrollIntoViewIfNeeded();
      await page.waitForTimeout(400);
    }
    const outPath = path.join(SCREENSHOT_DIR, '03_compilazione_step_validation_state.png');
    await page.screenshot({ path: outPath });
    console.log(`  ✓ Saved: 03_compilazione_step_validation_state.png`);
    await context.close();
  }

  // =========================================================================
  // SCHERMATA 4: Riepilogo Pratica / Invio (/modules/form/<id>/summary/)
  // =========================================================================
  async function prepareFormSummary(page) {
    await loginClient(page, CUSTOMER_CODE, CUSTOMER_PASS);
    await page.goto(`${BASE_URL}/modules/client/product/${ASSIGNMENT_ID}/`, { waitUntil: 'networkidle' });
    await page.goto(`${BASE_URL}/modules/form/${ASSIGNMENT_ID}/summary/`, { waitUntil: 'networkidle' });
    await dismissIntroIfPresent(page);
  }

  await captureScreen(browser, '04_riepilogo_invio', async (page) => {
    await prepareFormSummary(page);
  });

  // 4. Keyboard Navigation on Summary
  {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    await prepareFormSummary(page);
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(100);
    }
    const outPath = path.join(SCREENSHOT_DIR, '04_riepilogo_invio_keyboard_focus.png');
    await page.screenshot({ path: outPath });
    console.log(`  ✓ Saved: 04_riepilogo_invio_keyboard_focus.png`);
    await context.close();
  }

  // 4. Missing Requirements / Empty Uploads State
  {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    await prepareFormSummary(page);
    // Screenshot highlighting pending documents warning banner
    const outPath = path.join(SCREENSHOT_DIR, '04_riepilogo_invio_pending_requirements.png');
    await page.screenshot({ path: outPath });
    console.log(`  ✓ Saved: 04_riepilogo_invio_pending_requirements.png`);
    await context.close();
  }

  // =========================================================================
  // SCHERMATA 5: Dashboard Operatore / Admin (/modules/admin/)
  // =========================================================================
  async function loginAdmin(page) {
    await page.goto(`${BASE_URL}/login/`, { waitUntil: 'networkidle' });
    await page.fill('input[name="username"]', ADMIN_USER);
    await page.fill('input[name="password"]', ADMIN_PASS);
    await Promise.all([
      page.waitForNavigation({ waitUntil: 'networkidle' }),
      page.click('button[type="submit"]'),
    ]);
  }

  await captureScreen(browser, '05_dashboard_operatore', async (page) => {
    await loginAdmin(page);
    await page.goto(`${BASE_URL}/modules/admin/`, { waitUntil: 'networkidle' });
  });

  // 5. Keyboard Navigation on Operator Dashboard
  {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    await loginAdmin(page);
    await page.goto(`${BASE_URL}/modules/admin/`, { waitUntil: 'networkidle' });
    for (let i = 0; i < 6; i++) {
      await page.keyboard.press('Tab');
      await page.waitForTimeout(100);
    }
    const outPath = path.join(SCREENSHOT_DIR, '05_dashboard_operatore_keyboard_focus.png');
    await page.screenshot({ path: outPath });
    console.log(`  ✓ Saved: 05_dashboard_operatore_keyboard_focus.png`);
    await context.close();
  }

  // 5. Filter / Empty search state on Operator Dashboard
  {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    await loginAdmin(page);
    await page.goto(`${BASE_URL}/modules/admin/?search=NESSUNA_PRATICA_CON_QUESTO_NOME`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(300);
    const outPath = path.join(SCREENSHOT_DIR, '05_dashboard_operatore_empty_state.png');
    await page.screenshot({ path: outPath });
    console.log(`  ✓ Saved: 05_dashboard_operatore_empty_state.png`);
    await context.close();
  }

  // =========================================================================
  // SCHERMATA 6: Elenco Clienti (/modules/admin/customers/)
  // =========================================================================
  await captureScreen(browser, '06_elenco_clienti', async (page) => {
    await loginAdmin(page);
    await page.goto(`${BASE_URL}/modules/admin/customers/`, { waitUntil: 'networkidle' });
  });

  // 6. Keyboard Navigation on Customer List
  {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    await loginAdmin(page);
    await page.goto(`${BASE_URL}/modules/admin/customers/`, { waitUntil: 'networkidle' });
    const searchInput = await page.$('input[name="q"]') || await page.$('input[type="search"]') || await page.$('input[name="search"]');
    if (searchInput) {
      await searchInput.focus();
    } else {
      await page.keyboard.press('Tab');
    }
    await page.waitForTimeout(200);
    const outPath = path.join(SCREENSHOT_DIR, '06_elenco_clienti_keyboard_focus.png');
    await page.screenshot({ path: outPath });
    console.log(`  ✓ Saved: 06_elenco_clienti_keyboard_focus.png`);
    await context.close();
  }

  // 6. Empty State on Customer List (search with no results)
  {
    const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
    const page = await context.newPage();
    await loginAdmin(page);
    await page.goto(`${BASE_URL}/modules/admin/customers/?q=INESISTENTE_NESSUN_CLIENTE`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(300);
    const outPath = path.join(SCREENSHOT_DIR, '06_elenco_clienti_empty_state.png');
    await page.screenshot({ path: outPath });
    console.log(`  ✓ Saved: 06_elenco_clienti_empty_state.png`);
    await context.close();
  }

  await browser.close();

  const files = fs.readdirSync(SCREENSHOT_DIR).filter(f => f.endsWith('.png'));
  console.log(`\n======================================================`);
  console.log(`Collaudo UI completato con successo!`);
  console.log(`Totale screenshot esportati in ${SCREENSHOT_DIR}: ${files.length}`);
  files.forEach(f => console.log(` - ${f}`));
  console.log(`======================================================\n`);
}

run().catch(err => {
  console.error('FATAL ERROR in verify_ui.mjs:', err);
  process.exit(1);
});
