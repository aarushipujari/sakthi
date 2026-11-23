const { spawn } = require('child_process');
const { chromium } = require('playwright');
const http = require('http');

const prefix = process.argv[2] || 'before';
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
  console.log(`Starting uvicorn server for ${prefix} screenshots...`);
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

    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);

    // 1. Screenshot of main tab
    await page.screenshot({ path: `${prefix}_main.png`, fullPage: false });
    console.log(`Saved ${prefix}_main.png`);

    // 2. Click Economics tab
    const econTab = await page.$('[data-tab="tab-economics"], #whatif-toggle');
    if (econTab) {
      await econTab.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: `${prefix}_economics.png`, fullPage: false });
      console.log(`Saved ${prefix}_economics.png`);
    } else {
      console.warn('Economics tab selector not found');
    }

    await browser.close();
  } catch (err) {
    console.error('Error during screenshot capture:', err);
  } finally {
    console.log('Shutting down server...');
    server.kill();
  }
})();
