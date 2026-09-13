import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import http from 'node:http';
import puppeteer from 'puppeteer-core';

const chromeCandidates = [
  process.env.CHROME_BIN,
  process.env.PUPPETEER_EXECUTABLE_PATH,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium-browser',
  '/usr/bin/chromium',
];

const executablePath = chromeCandidates.find((p) => p && existsSync(p));
if (!executablePath) {
  console.error('[smoke-test] No Chrome or Chromium executable found. Please set CHROME_BIN.');
  process.exit(1);
}

const PORT = 4173;
const previewProcess = spawn('npx', ['vite', 'preview', '--port', String(PORT), '--strictPort'], {
  cwd: process.cwd(),
  stdio: ['ignore', 'pipe', 'pipe'],
});

const cleanup = async (browser, exitCode = 0) => {
  try {
    if (browser) {
      await browser.close();
    }
  } catch {
    // Ignore close errors during teardown
  }
  previewProcess.kill();
  process.exit(exitCode);
};

// Wait for preview server readiness
const waitForServer = async (retries = 30) => {
  for (let i = 0; i < retries; i++) {
    try {
      await new Promise((resolve, reject) => {
        const req = http.get(`http://localhost:${PORT}/`, (res) => {
          if (res.statusCode === 200) resolve();
          else reject(new Error(`HTTP ${res.statusCode}`));
        });
        req.on('error', reject);
        req.setTimeout(1000, () => req.destroy());
      });
      return;
    } catch {
      await new Promise((r) => setTimeout(r, 200));
    }
  }
  throw new Error('Vite preview server timed out.');
};

async function runSmokeTest() {
  let browser = null;
  const pageErrors = [];
  const consoleLogs = [];

  try {
    console.log('[smoke-test] Waiting for Vite preview server...');
    await waitForServer();

    console.log(`[smoke-test] Launching headless browser (${executablePath})...`);
    browser = await puppeteer.launch({
      executablePath,
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
    });

    const page = await browser.newPage();

    page.on('pageerror', (err) => {
      console.error('[smoke-test] Browser pageerror:', err.message);
      pageErrors.push(err.message);
    });

    page.on('console', (msg) => {
      const text = msg.text();
      consoleLogs.push(text);
      if (msg.type() === 'error') {
        console.error('[smoke-test] Browser console error:', text);
        pageErrors.push(text);
      }
    });

    console.log(`[smoke-test] Navigating to http://localhost:${PORT}/...`);
    await page.goto(`http://localhost:${PORT}/`, { waitUntil: 'domcontentloaded', timeout: 15000 });

    console.log('[smoke-test] Verifying Phaser canvas initialization and BarScene transition...');
    await page.waitForFunction(
      () => {
        const g = window.__MAYA_GAME__;
        return (
          g &&
          g.isBooted &&
          g.scene &&
          g.scene.isActive('BarScene') &&
          g.scene.isActive('HUDOverlayScene')
        );
      },
      { timeout: 15000, polling: 100 }
    );

    // Verify canvas rendered
    const hasCanvas = await page.evaluate(() => {
      const container = document.getElementById('game-container');
      return container && container.querySelector('canvas') !== null;
    });

    if (!hasCanvas) {
      throw new Error('Phaser game canvas element was not found in #game-container.');
    }

    if (pageErrors.length > 0) {
      throw new Error(`Browser runtime errors detected: ${pageErrors.join(', ')}`);
    }

    console.log('✅ [smoke-test] Phaser 4 game runtime initialized successfully:');
    console.log('   - BootScene -> PreloadScene -> BarScene active');
    console.log('   - HUDOverlayScene active');
    console.log('   - Canvas element mounted in #game-container');
    console.log('   - 0 browser pageerrors or console errors');

    await cleanup(browser, 0);
  } catch (err) {
    console.error('❌ [smoke-test] Smoke test failed:', err.message);
    console.error('Captured logs:', consoleLogs.slice(-10));
    await cleanup(browser, 1);
  }
}

runSmokeTest();
