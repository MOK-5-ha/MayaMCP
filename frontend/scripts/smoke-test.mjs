import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import http from 'node:http';
import net from 'node:net';
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

// Find a guaranteed free ephemeral port to prevent port conflicts with other checkouts
const getFreePort = () =>
  new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on('error', reject);
    srv.listen(0, '127.0.0.1', () => {
      const address = srv.address();
      const port = typeof address === 'object' && address ? address.port : 4173;
      srv.close(() => resolve(port));
    });
  });

const cleanup = async (browser, previewProc, exitCode = 0) => {
  try {
    if (browser) {
      await browser.close();
    }
  } catch {
    // Ignore close errors during teardown
  }
  if (previewProc && !previewProc.killed) {
    try {
      previewProc.kill('SIGTERM');
    } catch {
      // Ignore kill error
    }
  }
  process.exit(exitCode);
};

async function runSmokeTest() {
  let browser = null;
  let previewProcess = null;
  const pageErrors = [];
  const consoleLogs = [];

  try {
    const PORT = await getFreePort();
    console.log(`[smoke-test] Allocated isolated preview port: ${PORT}`);

    console.log('[smoke-test] Spawning Vite preview server with strict port enforcement...');
    previewProcess = spawn('npx', ['vite', 'preview', '--port', String(PORT), '--strictPort'], {
      cwd: process.cwd(),
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let previewExited = false;
    let previewExitCode = null;
    let previewError = null;
    const stderrChunks = [];
    const stdoutChunks = [];

    previewProcess.stderr.on('data', (chunk) => stderrChunks.push(chunk));
    previewProcess.stdout.on('data', (chunk) => stdoutChunks.push(chunk));
    previewProcess.on('error', (err) => {
      previewError = err;
    });
    previewProcess.on('exit', (code, signal) => {
      previewExited = true;
      previewExitCode = code ?? signal;
    });

    // Wait for preview server readiness while actively monitoring process lifecycle
    const waitForServer = async (retries = 40) => {
      for (let i = 0; i < retries; i++) {
        if (previewExited) {
          const errOutput =
            Buffer.concat(stderrChunks).toString().trim() ||
            Buffer.concat(stdoutChunks).toString().trim();
          throw new Error(
            `Vite preview server exited prematurely with code ${previewExitCode}.\nProcess output:\n${errOutput}`
          );
        }
        if (previewError) {
          throw new Error(`Failed to spawn Vite preview process: ${previewError.message}`);
        }

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

      if (previewExited) {
        const errOutput =
          Buffer.concat(stderrChunks).toString().trim() ||
          Buffer.concat(stdoutChunks).toString().trim();
        throw new Error(
          `Vite preview server exited prematurely with code ${previewExitCode}.\nProcess output:\n${errOutput}`
        );
      }
      throw new Error(`Vite preview server timed out on port ${PORT}.`);
    };

    console.log('[smoke-test] Waiting for Vite preview server readiness...');
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

    // Verify canvas element rendered
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
    console.log('   - Isolated ephemeral port verified (no cross-checkout conflict)');
    console.log('   - BootScene -> PreloadScene -> BarScene active');
    console.log('   - HUDOverlayScene active');
    console.log('   - Canvas element mounted in #game-container');
    console.log('   - 0 browser pageerrors or console errors');

    await cleanup(browser, previewProcess, 0);
  } catch (err) {
    console.error('❌ [smoke-test] Smoke test failed:', err.message);
    if (consoleLogs.length > 0) {
      console.error('Captured logs:', consoleLogs.slice(-10));
    }
    await cleanup(browser, previewProcess, 1);
  }
}

runSmokeTest();
