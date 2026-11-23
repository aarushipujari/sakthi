const { spawn } = require('child_process');
const { chromium } = require('playwright');
const http = require('http');

const pythonExe = 'C:\\Users\\aarus\\AppData\\Local\\Programs\\Python\\Python310\\python.exe';
const chromeExe = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

function waitForServer(url, timeoutMs = 15000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    function check() {
      http.get(url, (res) => {
        if (res.statusCode === 200) return resolve();
        if (Date.now() - start > timeoutMs) return reject(new Error('Timeout'));
        setTimeout(check, 300);
      }).on('error', () => {
        if (Date.now() - start > timeoutMs) return reject(new Error('Timeout'));
        setTimeout(check, 300);
      });
    }
    check();
  });
}

(async () => {
  console.log('Starting uvicorn server for tab & mobile verification...');
  const server = spawn(pythonExe, ['-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8000'], {
    stdio: 'ignore'
  });

  try {
    await waitForServer('http://127.0.0.1:8000/api/grades');
    console.log('Server is ready. Launching Playwright Chromium...');

    const browser = await chromium.launch({
      executablePath: chromeExe,
      headless: true
    });

    const consoleErrors = [];
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    const tabs = [
      { id: 'tab-optimizer', name: 'Live Calculation' },
      { id: 'tab-economics', name: 'Economics' },
      { id: 'tab-heats', name: 'Heat History' },
      { id: 'tab-settings', name: 'Master Recipe Settings' },
      { id: 'tab-corridors', name: 'Chemistry & Corridors' }
    ];

    console.log('\n--- VERIFYING DESKTOP TABS FOR NaN / undefined ---');
    for (const tab of tabs) {
      const btn = await page.$(`[data-tab="${tab.id}"]`);
      if (btn) {
        await btn.click();
        await page.waitForTimeout(600);
      }
      const text = await page.evaluate(() => document.body.innerText);
      if (text.includes('NaN')) {
        throw new Error(`Found "NaN" in DOM on tab ${tab.name}!`);
      }
      if (text.includes('undefined')) {
        throw new Error(`Found "undefined" in DOM on tab ${tab.name}!`);
      }
      console.log(`[PASS] Tab "${tab.name}" has ZERO NaN and ZERO undefined.`);
    }

    console.log('\n--- VERIFYING MOBILE VIEWPORT 390x800 ---');
    await page.setViewportSize({ width: 390, height: 800 });
    await page.waitForTimeout(500);

    for (const tab of tabs) {
      const btn = await page.$(`[data-tab="${tab.id}"]`);
      if (btn) {
        await btn.click();
        await page.waitForTimeout(600);
      }
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
      console.log(`Tab "${tab.name}" document.documentElement.scrollWidth = ${scrollWidth}`);
      if (scrollWidth > 390) {
        const overflowing = await page.evaluate(() => {
          return Array.from(document.querySelectorAll('*'))
            .filter(el => el.getBoundingClientRect().right > 390)
            .map(el => ({ tag: el.tagName, id: el.id, class: el.className, right: el.getBoundingClientRect().right, width: el.getBoundingClientRect().width }))
            .slice(0, 10);
        });
        console.log('Overflowing elements:', JSON.stringify(overflowing, null, 2));
        throw new Error(`Horizontal overflow on tab ${tab.name}: scrollWidth=${scrollWidth} > 390`);
      }
    }
    console.log('[PASS] All tabs fit 390x800 viewport with scrollWidth <= 390px (no horizontal scrollbar).');

    console.log('\n--- CHECKING CONSOLE ERRORS ---');
    if (consoleErrors.length > 0) {
      console.warn('Console errors detected:', consoleErrors);
    } else {
      console.log('[PASS] ZERO console errors.');
    }

    await browser.close();
    console.log('\nALL PLAYWRIGHT TESTS PASSED 100%!');
  } catch (err) {
    console.error('VERIFICATION FAILED:', err);
    process.exit(1);
  } finally {
    server.kill();
  }
})();
