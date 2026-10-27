import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
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

const DUMMY_GCP_PROJECT = 'smoke-gcp-project-secret';
const DUMMY_CARTESIA_KEY = 'smoke-cartesia-secret';
const SESSION_ID = 'smoke-session';
const UNAVAILABLE_MESSAGE = 'Soundtrack unavailable — audio files not installed';
const MUSIC_FILES = {
  bgm_start_rain: 'start-rain.wav',
  bgm_lounge: 'lounge.wav',
  bgm_afterhours: 'afterhours.wav',
  bgm_midnight: 'midnight.wav',
};
const MUSIC_TITLES = {
  bgm_start_rain: 'Start Rain',
  bgm_lounge: 'Lounge',
  bgm_afterhours: 'Afterhours',
  bgm_midnight: 'Midnight',
};
const BASE_PLAYLIST = ['bgm_lounge', 'bgm_afterhours'];
const PARTIAL_PLAYLIST = [...BASE_PLAYLIST, 'bgm_midnight'];

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

function createWavBuffer(durationSeconds, frequency) {
  const sampleRate = 22050;
  const sampleCount = Math.ceil(sampleRate * durationSeconds);
  const dataSize = sampleCount * 2;
  const buffer = Buffer.alloc(44 + dataSize);

  buffer.write('RIFF', 0);
  buffer.writeUInt32LE(36 + dataSize, 4);
  buffer.write('WAVE', 8);
  buffer.write('fmt ', 12);
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20);
  buffer.writeUInt16LE(1, 22);
  buffer.writeUInt32LE(sampleRate, 24);
  buffer.writeUInt32LE(sampleRate * 2, 28);
  buffer.writeUInt16LE(2, 32);
  buffer.writeUInt16LE(16, 34);
  buffer.write('data', 36);
  buffer.writeUInt32LE(dataSize, 40);

  for (let index = 0; index < sampleCount; index++) {
    const sample = Math.round(Math.sin((2 * Math.PI * frequency * index) / sampleRate) * 4096);
    buffer.writeInt16LE(sample, 44 + index * 2);
  }

  return buffer;
}

function buildFixtureManifest(realManifest, unavailableTracks) {
  const manifest = structuredClone(realManifest);
  const fixtureKeys = new Set(Object.keys(MUSIC_FILES));
  const otherAudio = (manifest.audio || []).filter(
    (entry) => entry.type !== 'music' || !fixtureKeys.has(entry.key)
  );
  manifest.audio = [
    ...otherAudio,
    ...Object.entries(MUSIC_FILES).map(([key, filename]) => ({
      key,
      path: `assets/audio/${filename}`,
      type: 'music',
      title: MUSIC_TITLES[key],
      placeholder: unavailableTracks.has(key),
    })),
  ];
  manifest.soundtrack = {
    startTrack: 'bgm_start_rain',
    playlist: BASE_PLAYLIST,
  };
  return manifest;
}

function buildMediaManifest(realManifest) {
  return buildFixtureManifest(realManifest, new Set());
}

function buildPlaceholderManifest(realManifest) {
  return buildFixtureManifest(realManifest, new Set(Object.keys(MUSIC_FILES)));
}

function buildPartialManifest(realManifest) {
  const manifest = buildFixtureManifest(realManifest, new Set(['bgm_afterhours']));
  manifest.soundtrack.playlist = PARTIAL_PLAYLIST;
  return manifest;
}

function validateManifestStructure(manifest) {
  assert.ok(manifest && typeof manifest === 'object', 'Asset manifest must be an object.');
  assert.ok(
    typeof manifest.version === 'string' || typeof manifest.version === 'number',
    'Manifest v2 must declare a version.'
  );
  assert.ok(Array.isArray(manifest.images), 'Manifest v2 must declare an images array.');
  assert.ok(Array.isArray(manifest.audio), 'Manifest v2 must declare an audio array.');
  assert.ok(
    manifest.images.some(
      (entry) =>
        entry.key === 'start_bar_exterior' &&
        entry.path === 'assets/images/start-bar-exterior.png'
    ),
    'Manifest must include the real start_bar_exterior artwork.'
  );

  const musicByKey = new Map();
  for (const entry of manifest.audio) {
    if (entry.type !== 'music') continue;

    assert.ok(
      !musicByKey.has(entry.key),
      `Duplicate music key in real manifest: ${entry.key}`
    );
    assert.equal(typeof entry.key, 'string', 'Music entries need string keys.');
    assert.equal(typeof entry.path, 'string', `${entry.key} must have an audio path.`);
    assert.equal(typeof entry.title, 'string', `${entry.key} must have a title.`);
    assert.equal(
      typeof entry.placeholder,
      'boolean',
      `${entry.key} must explicitly declare whether it is a placeholder.`
    );
    musicByKey.set(entry.key, entry);
  }

  const soundtrack = manifest.soundtrack;
  assert.ok(soundtrack && typeof soundtrack === 'object', 'Manifest needs soundtrack config.');
  assert.equal(typeof soundtrack.startTrack, 'string', 'Manifest needs a fixed start track.');
  assert.ok(
    musicByKey.has(soundtrack.startTrack),
    `soundtrack.startTrack references missing music: ${soundtrack.startTrack}`
  );
  assert.ok(Array.isArray(soundtrack.playlist), 'Manifest needs a soundtrack playlist.');
  for (const key of soundtrack.playlist) {
    assert.equal(typeof key, 'string', 'Soundtrack playlist keys must be strings.');
    assert.ok(
      musicByKey.has(key),
      `soundtrack.playlist references missing music: ${key}`
    );
  }
}

function validateFixtureManifest(manifest, expectedPlaylist, unavailableTracks) {
  const fixtureKeys = new Set(Object.keys(MUSIC_FILES));
  const musicByKey = new Map(
    manifest.audio.filter((entry) => entry.type === 'music').map((entry) => [entry.key, entry])
  );

  assert.ok(
    [...fixtureKeys].every((key) => musicByKey.has(key)),
    'Soundtrack fixture is missing one or more test music tracks.'
  );
  for (const [key, entry] of musicByKey) {
    if (!fixtureKeys.has(key)) continue;

    assert.equal(
      entry.placeholder,
      unavailableTracks.has(key),
      `${key} has the wrong fixture placeholder state.`
    );
  }
  assert.deepEqual(manifest.soundtrack.startTrack, 'bgm_start_rain');
  assert.deepEqual(manifest.soundtrack.playlist, expectedPlaylist);
}

function validateSnapshot(snapshot, label) {
  assert.ok(snapshot && typeof snapshot === 'object', `${label} snapshot must exist.`);
  assert.deepEqual(
    Object.keys(snapshot).sort(),
    ['currentKey', 'currentTitle', 'intendedKey', 'isPaused', 'isPlaying', 'playlistKeys'].sort(),
    `${label} snapshot shape is incorrect.`
  );
  for (const key of ['currentKey', 'currentTitle', 'intendedKey']) {
    assert.ok(
      snapshot[key] === null || typeof snapshot[key] === 'string',
      `${label}.${key} must be a string or null.`
    );
  }
  assert.equal(typeof snapshot.isPlaying, 'boolean', `${label}.isPlaying must be boolean.`);
  assert.equal(typeof snapshot.isPaused, 'boolean', `${label}.isPaused must be boolean.`);
  assert.ok(Array.isArray(snapshot.playlistKeys), `${label}.playlistKeys must be an array.`);
  assert.ok(
    snapshot.playlistKeys.every((key) => typeof key === 'string'),
    `${label}.playlistKeys must contain only strings.`
  );
}

function validateCredentialBody(body, includeCartesiaKey) {
  assert.ok(body && typeof body === 'object' && !Array.isArray(body), 'Credentials must be JSON.');
  assert.ok(
    Object.keys(body).every((key) => key === 'gcp_project' || key === 'cartesia_key'),
    `Credential payload contains unsupported fields: ${Object.keys(body).sort().join(', ')}`
  );
  assert.equal(body.gcp_project, DUMMY_GCP_PROJECT);
  if (includeCartesiaKey) {
    assert.equal(body.cartesia_key, DUMMY_CARTESIA_KEY);
  } else {
    assert.ok(!Object.hasOwn(body, 'cartesia_key'), 'Blank optional Cartesia key must be omitted.');
  }
}

async function waitForStartGate(page) {
  try {
    await page.waitForFunction(
      () => {
        const game = window.__MAYA_GAME__;
        return (
          game?.isBooted &&
          game.scene?.isActive('StartScene') &&
          !game.scene.isActive('BarScene') &&
          !game.scene.isActive('HUDOverlayScene') &&
          document.getElementById('maya-start-form') &&
          document.getElementById('gcp-project') &&
          document.getElementById('cartesia-key') &&
          document.getElementById('cartesia-visibility') &&
          document.getElementById('start-submit') &&
          document.getElementById('start-error')
        );
      },
      { timeout: 5000, polling: 100 }
    );
  } catch {
    const state = await page.evaluate(() => {
      const game = window.__MAYA_GAME__;
      return {
        booted: Boolean(game?.isBooted),
        startActive: Boolean(game?.scene?.isActive('StartScene')),
        formPresent: Boolean(document.getElementById('maya-start-form')),
      };
    });
    throw new Error(
      `StartScene gate was not reached (expected on every load): ${JSON.stringify(state)}`
    );
  }
}

async function waitForBar(page) {
  await page.waitForFunction(
    () => {
      const game = window.__MAYA_GAME__;
      return (
        game?.scene?.isActive('BarScene') &&
        game.scene.isActive('HUDOverlayScene') &&
        !game.scene.isActive('StartScene') &&
        !document.getElementById('maya-start-form') &&
        document.getElementById('soundtrack-player')
      );
    },
    { timeout: 15000, polling: 100 }
  );
}

async function getSnapshot(page, sceneKey) {
  const snapshot = await page.evaluate((key) => {
    const scene = window.__MAYA_GAME__?.scene.getScene(key);
    return scene?.getSoundManager?.().getSnapshot() ?? null;
  }, sceneKey);
  validateSnapshot(snapshot, sceneKey);
  return snapshot;
}

async function waitForSnapshot(page, sceneKey, expected, timeout = 15000) {
  await page.waitForFunction(
    (key, expectedState) => {
      const scene = window.__MAYA_GAME__?.scene.getScene(key);
      const snapshot = scene?.getSoundManager?.().getSnapshot();
      return (
        snapshot &&
        Object.entries(expectedState).every(
          ([stateKey, value]) => JSON.stringify(snapshot[stateKey]) === JSON.stringify(value)
        )
      );
    },
    { timeout, polling: 100 },
    sceneKey,
    expected
  );
  return getSnapshot(page, sceneKey);
}

async function assertStartSemantics(page) {
  const semantics = await page.evaluate(() => {
    const form = document.getElementById('maya-start-form');
    const gcp = document.getElementById('gcp-project');
    const cartesia = document.getElementById('cartesia-key');
    const visibility = document.getElementById('cartesia-visibility');
    const submit = document.getElementById('start-submit');
    const error = document.getElementById('start-error');
    const labelText = (id) => document.querySelector(`label[for="${id}"]`)?.textContent?.trim() || '';
    return {
      formTag: form.tagName,
      gcpType: gcp.type,
      gcpRequired: gcp.required,
      gcpLabel: labelText('gcp-project'),
      cartesiaType: cartesia.type,
      cartesiaRequired: cartesia.required,
      cartesiaLabel: labelText('cartesia-key'),
      visibilityTag: visibility.tagName,
      visibilityLabel:
        visibility.getAttribute('aria-label') || visibility.textContent?.trim() || '',
      submitTag: submit.tagName,
      submitType: submit.type,
      errorRole: error.getAttribute('role'),
      startPlayerPresent: Boolean(document.getElementById('soundtrack-player')),
    };
  });

  assert.equal(semantics.formTag, 'FORM');
  assert.equal(semantics.gcpType, 'text');
  assert.equal(semantics.gcpRequired, true);
  assert.ok(semantics.gcpLabel.length > 0, 'GCP project input needs a visible label.');
  assert.equal(semantics.cartesiaType, 'password');
  assert.equal(semantics.cartesiaRequired, false);
  assert.ok(semantics.cartesiaLabel.length > 0, 'Cartesia input needs a visible label.');
  assert.equal(semantics.visibilityTag, 'BUTTON');
  assert.ok(semantics.visibilityLabel.length > 0, 'Password visibility control needs a label.');
  assert.equal(semantics.submitTag, 'BUTTON');
  assert.equal(semantics.submitType, 'submit');
  assert.equal(semantics.errorRole, 'alert');
  assert.equal(semantics.startPlayerPresent, false, 'Start must not render the bar player.');

  await page.click('#cartesia-visibility');
  assert.equal(
    await page.$eval('#cartesia-key', (input) => input.type),
    'text',
    'Visibility control must reveal the optional password.'
  );
  await page.click('#cartesia-visibility');
  assert.equal(
    await page.$eval('#cartesia-key', (input) => input.type),
    'password',
    'Visibility control must conceal the password again.'
  );

  await page.evaluate(() => document.activeElement?.blur());
  await page.keyboard.press('Tab');
  const focus = await page.evaluate(() => {
    const active = document.activeElement;
    if (!active || !document.getElementById('maya-start-form').contains(active)) {
      return { insideForm: false, focusVisible: false, indicator: false };
    }
    const style = getComputedStyle(active);
    return {
      insideForm: true,
      focusVisible: active.matches(':focus-visible'),
      indicator:
        (style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0) ||
        style.boxShadow !== 'none',
    };
  });
  assert.ok(focus.insideForm && focus.focusVisible, 'Keyboard focus must enter the Start form.');
  assert.ok(focus.indicator, 'Keyboard-focused Start controls need a visible focus indicator.');
}

async function assertResponsiveLayout(page, elementId) {
  const originalViewport = page.viewport();
  for (const size of [
    { width: 1280, height: 720 },
    { width: 640, height: 360 },
    { width: 390, height: 844 },
  ]) {
    await page.setViewport({ ...size, deviceScaleFactor: 1 });
    await page.evaluate(
      () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))
    );
    const layout = await page.evaluate((id) => {
      const canvas = document.querySelector('canvas').getBoundingClientRect();
      const element = document.getElementById(id).getBoundingClientRect();
      return {
        viewport: { width: innerWidth, height: innerHeight },
        canvas: { left: canvas.left, top: canvas.top, right: canvas.right, bottom: canvas.bottom },
        element: {
          left: element.left,
          top: element.top,
          right: element.right,
          bottom: element.bottom,
        },
        scroll: {
          width: document.documentElement.scrollWidth,
          height: document.documentElement.scrollHeight,
        },
      };
    }, elementId);
    const { canvas, element, viewport, scroll } = layout;
    assert.ok(
      element.left >= canvas.left - 1 &&
        element.top >= canvas.top - 1 &&
        element.right <= canvas.right + 1 &&
        element.bottom <= canvas.bottom + 1,
      `${elementId} must stay inside the canvas: ${JSON.stringify(layout)}`
    );
    assert.ok(
      scroll.width <= viewport.width && scroll.height <= viewport.height,
      `${elementId} must not create page overflow: ${JSON.stringify(layout)}`
    );
  }
  await page.setViewport(originalViewport);
}

async function assertNoSecretsPersisted(page, expectedSessionId) {
  const storage = await page.evaluate(() =>
    Object.fromEntries(Object.entries(localStorage).map(([key, value]) => [key, value]))
  );
  assert.ok(
    Object.keys(storage).every((key) => key === 'maya_session_id'),
    `Only maya_session_id may persist; found: ${Object.keys(storage).sort().join(', ')}`
  );
  assert.equal(storage.maya_session_id, expectedSessionId);
  const serialized = JSON.stringify(storage);
  assert.ok(!serialized.includes(DUMMY_GCP_PROJECT), 'GCP secret leaked into localStorage.');
  assert.ok(!serialized.includes(DUMMY_CARTESIA_KEY), 'Cartesia secret leaked into localStorage.');
}

async function installStopAllMonitor(page) {
  await page.evaluate(() => {
    const game = window.__MAYA_GAME__;
    const original = game.sound.stopAll.bind(game.sound);
    window.__SMOKE_STOP_ALL_CALLS__ = 0;
    game.sound.stopAll = (...args) => {
      window.__SMOKE_STOP_ALL_CALLS__ += 1;
      return original(...args);
    };
  });
}

async function assertPlayerSemantics(page) {
  const controls = await page.evaluate(() => {
    const status = document.getElementById('track-status');
    return {
      statusLive: status.getAttribute('aria-live'),
      buttons: ['track-prev', 'track-toggle', 'track-next'].map((id) => {
        const button = document.getElementById(id);
        const rect = button.getBoundingClientRect();
        return {
          id,
          tag: button.tagName,
          type: button.type,
          disabled: button.disabled,
          width: rect.width,
          height: rect.height,
        };
      }),
    };
  });
  assert.equal(controls.statusLive, 'polite');
  for (const button of controls.buttons) {
    assert.equal(button.tag, 'BUTTON', `${button.id} must be a native button.`);
    assert.equal(button.type, 'button', `${button.id} must not submit a form.`);
    assert.ok(button.width >= 44 && button.height >= 44, `${button.id} must be at least 44x44.`);
    assert.equal(button.disabled, false, `${button.id} should be enabled with installed music.`);
  }
}

async function submitAndEnterBar(page, { includeCartesiaKey }) {
  await page.click('#gcp-project');
  await page.type('#gcp-project', DUMMY_GCP_PROJECT);
  if (includeCartesiaKey) {
    await page.type('#cartesia-key', DUMMY_CARTESIA_KEY);
  }
  await page.click('#start-submit');
  await waitForBar(page);
}

async function runMediaPass(browser, realManifest, diagnostics) {
  console.log('[smoke-test] Pass 1: media-enabled Start and soundtrack flow...');
  const page = await browser.newPage();
  diagnostics.attach(page);

  const mediaManifest = buildMediaManifest(realManifest);
  const wavBuffers = {
    'start-rain.wav': createWavBuffer(12, 220),
    'lounge.wav': createWavBuffer(12, 330),
    'afterhours.wav': createWavBuffer(1.5, 440),
    'midnight.wav': createWavBuffer(12, 550),
  };
  const credentialBodies = [];
  let credentialRequestCount = 0;
  let releasePendingResponse;
  const pendingResponse = new Promise((resolve) => {
    releasePendingResponse = resolve;
  });

  await page.setRequestInterception(true);
  page.on('request', (request) => {
    void (async () => {
      const url = new URL(request.url());
      if (url.pathname === '/assets/manifest.json') {
        await request.respond({
          status: 200,
          contentType: 'application/json',
          headers: { 'Cache-Control': 'no-store' },
          body: JSON.stringify(mediaManifest),
        });
        return;
      }

      const wavEntry = Object.values(MUSIC_FILES).find((filename) =>
        url.pathname.endsWith(`/${filename}`)
      );
      if (wavEntry) {
        await request.respond({
          status: 200,
          contentType: 'audio/wav',
          headers: { 'Cache-Control': 'no-store' },
          body: wavBuffers[wavEntry],
        });
        return;
      }

      if (url.pathname === '/api/session/keys' && request.method() === 'POST') {
        credentialRequestCount += 1;
        credentialBodies.push(JSON.parse(request.postData() || 'null'));
        if (credentialRequestCount === 1) {
          await pendingResponse;
          await request.respond({
            status: 400,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'Invalid smoke credentials' }),
          });
        } else {
          await request.respond({
            status: 200,
            contentType: 'application/json',
            headers: { 'X-Session-ID': SESSION_ID },
            body: JSON.stringify({ status: 'success', session_id: SESSION_ID, has_valid_keys: true }),
          });
        }
        return;
      }

      await request.continue();
    })().catch((error) => {
      diagnostics.interceptionErrors.push(error.message);
      void request.abort().catch(() => {});
    });
  });

  await page.goto(diagnostics.origin, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await waitForStartGate(page);
  validateFixtureManifest(mediaManifest, BASE_PLAYLIST, new Set());
  assert.deepEqual(diagnostics.interceptionErrors, []);
  await assertStartSemantics(page);
  await assertResponsiveLayout(page, 'maya-start-form');
  await installStopAllMonitor(page);

  const canvasPresent = await page.evaluate(() =>
    Boolean(document.getElementById('game-container')?.querySelector('canvas'))
  );
  assert.ok(canvasPresent, 'Phaser canvas must remain mounted in #game-container.');

  console.log('[smoke-test] Unlocking WebAudio through a native field click...');
  await page.click('#gcp-project');
  await page.type('#gcp-project', DUMMY_GCP_PROJECT);
  await page.type('#cartesia-key', DUMMY_CARTESIA_KEY);
  const initialStartSnapshot = await waitForSnapshot(page, 'StartScene', {
    currentKey: 'bgm_start_rain',
    isPlaying: true,
  });
  assert.equal(initialStartSnapshot.intendedKey, 'bgm_start_rain');
  assert.deepEqual(initialStartSnapshot.playlistKeys, []);
  assert.equal(
    await page.evaluate(() => {
      const scene = window.__MAYA_GAME__.scene.getScene('StartScene');
      return scene.sound.get('bgm_start_rain')?.loop;
    }),
    true,
    'Start rain music must loop.'
  );

  await page.click('#start-submit');
  await page.waitForFunction(
    () => {
      const button = document.getElementById('start-submit');
      const form = document.getElementById('maya-start-form');
      return (
        button?.disabled &&
        (button.getAttribute('aria-busy') === 'true' ||
          /validat/i.test(button.textContent || '') ||
          form?.getAttribute('aria-busy') === 'true')
      );
    },
    { timeout: 5000, polling: 50 }
  );
  assert.equal(credentialRequestCount, 1);
  validateCredentialBody(credentialBodies[0], true);

  await page.focus('#gcp-project');
  await page.keyboard.press('Enter');
  await page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))
  );
  assert.equal(credentialRequestCount, 1, 'Pending validation must not allow duplicate POSTs.');

  diagnostics.expectedConsoleErrors.push(
    'Failed to load resource: the server responded with a status of 400 (Bad Request)'
  );
  releasePendingResponse();
  await page.waitForFunction(
    () => {
      const error = document.getElementById('start-error');
      const submit = document.getElementById('start-submit');
      return error?.textContent?.trim() && submit && !submit.disabled;
    },
    { timeout: 5000, polling: 100 }
  );
  assert.ok(await page.evaluate(() => window.__MAYA_GAME__.scene.isActive('StartScene')));
  assert.equal(await page.$eval('#start-error', (element) => element.getAttribute('role')), 'alert');
  assert.equal(await page.$('#soundtrack-player'), null);
  await waitForSnapshot(page, 'StartScene', { currentKey: 'bgm_start_rain', isPlaying: true });
  await assertNoSecretsPersisted(page, undefined);

  console.log('[smoke-test] Retrying validation through native keyboard submission...');
  await page.focus('#cartesia-key');
  await page.keyboard.press('Enter');
  await waitForBar(page);
  assert.equal(credentialRequestCount, 2);
  validateCredentialBody(credentialBodies[1], true);
  await assertNoSecretsPersisted(page, SESSION_ID);

  const stoppedStartSnapshot = await getSnapshot(page, 'StartScene');
  assert.equal(stoppedStartSnapshot.isPlaying, false, 'Start music must stop before Bar.');
  assert.equal(stoppedStartSnapshot.isPaused, false, 'Start music must not remain paused in Bar.');

  const initialBarSnapshot = await waitForSnapshot(page, 'BarScene', {
    currentKey: 'bgm_lounge',
    isPlaying: true,
    playlistKeys: ['bgm_lounge', 'bgm_afterhours'],
  });
  assert.equal(initialBarSnapshot.intendedKey, 'bgm_lounge');
  assert.ok(initialBarSnapshot.currentTitle, 'The current bar track needs a title.');
  assert.equal(
    await page.$eval('#track-title', (element) => element.textContent.trim()),
    initialBarSnapshot.currentTitle
  );
  await assertPlayerSemantics(page);
  await assertResponsiveLayout(page, 'soundtrack-player');
  assert.equal(
    await page.evaluate(() => window.__SMOKE_STOP_ALL_CALLS__),
    0,
    'Scene transitions must not globally stop independent audio.'
  );

  await page.click('#track-prev');
  await waitForSnapshot(page, 'BarScene', { currentKey: 'bgm_afterhours', isPlaying: true });
  await page.click('#track-next');
  await waitForSnapshot(page, 'BarScene', { currentKey: 'bgm_lounge', isPlaying: true });

  await page.click('#track-toggle');
  const pausedSnapshot = await waitForSnapshot(page, 'BarScene', {
    currentKey: 'bgm_lounge',
    isPlaying: false,
    isPaused: true,
  });
  assert.equal(pausedSnapshot.intendedKey, 'bgm_lounge');
  await page.click('#track-toggle');
  await waitForSnapshot(page, 'BarScene', {
    currentKey: 'bgm_lounge',
    isPlaying: true,
    isPaused: false,
  });

  await page.click('#track-next');
  await waitForSnapshot(page, 'BarScene', { currentKey: 'bgm_afterhours', isPlaying: true });
  console.log('[smoke-test] Waiting for the short afterhours track to end naturally...');
  await waitForSnapshot(
    page,
    'BarScene',
    { currentKey: 'bgm_lounge', isPlaying: true, isPaused: false },
    20000
  );

  diagnostics.assertClean(page);
  console.log('✅ [smoke-test] Media-enabled Start, credentials, and soundtrack flow passed.');
  await page.close();
}

async function runPlaceholderPass(browser, realManifest, diagnostics) {
  console.log('[smoke-test] Pass 2: unchanged placeholder manifest and unavailable player...');
  const page = await browser.newPage();
  diagnostics.attach(page);

  const placeholderManifest = buildPlaceholderManifest(realManifest);
  const credentialBodies = [];
  await page.setRequestInterception(true);
  page.on('request', (request) => {
    void (async () => {
      const url = new URL(request.url());
      if (url.pathname === '/assets/manifest.json') {
        await request.respond({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(placeholderManifest),
        });
        return;
      }
      if (url.pathname === '/api/session/keys' && request.method() === 'POST') {
        credentialBodies.push(JSON.parse(request.postData() || 'null'));
        await request.respond({
          status: 200,
          contentType: 'application/json',
          headers: { 'X-Session-ID': SESSION_ID },
          body: JSON.stringify({ status: 'success', session_id: SESSION_ID, has_valid_keys: true }),
        });
        return;
      }
      await request.continue();
    })().catch((error) => {
      diagnostics.interceptionErrors.push(error.message);
      void request.abort().catch(() => {});
    });
  });

  await page.goto(diagnostics.origin, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await waitForStartGate(page);
  validateFixtureManifest(
    placeholderManifest,
    BASE_PLAYLIST,
    new Set(Object.keys(MUSIC_FILES))
  );
  await assertStartSemantics(page);
  await submitAndEnterBar(page, { includeCartesiaKey: false });
  assert.equal(credentialBodies.length, 1);
  validateCredentialBody(credentialBodies[0], false);
  await assertNoSecretsPersisted(page, SESSION_ID);

  assert.equal(
    await page.$eval('#track-status', (element) => element.textContent.trim()),
    UNAVAILABLE_MESSAGE
  );
  for (const id of ['track-prev', 'track-toggle', 'track-next']) {
    assert.equal(await page.$eval(`#${id}`, (button) => button.disabled), true, `${id} disabled`);
  }
  const unavailableSnapshot = await getSnapshot(page, 'BarScene');
  assert.equal(unavailableSnapshot.currentKey, null);
  assert.equal(unavailableSnapshot.isPlaying, false);
  assert.deepEqual(unavailableSnapshot.playlistKeys, ['bgm_lounge', 'bgm_afterhours']);

  diagnostics.assertClean(page);
  console.log('✅ [smoke-test] Placeholder soundtrack passed without asset 404s.');
  await page.close();
}

async function runPartialPass(browser, realManifest, diagnostics) {
  console.log('[smoke-test] Pass 3: partially installed playlist...');
  const page = await browser.newPage();
  diagnostics.attach(page);

  const partialManifest = buildPartialManifest(realManifest);
  const wavBuffers = {
    'start-rain.wav': createWavBuffer(6, 220),
    'lounge.wav': createWavBuffer(6, 330),
    'midnight.wav': createWavBuffer(6, 550),
  };
  let afterhoursRequested = false;

  await page.setRequestInterception(true);
  page.on('request', (request) => {
    void (async () => {
      const url = new URL(request.url());
      if (url.pathname === '/assets/manifest.json') {
        await request.respond({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(partialManifest),
        });
        return;
      }
      if (url.pathname.endsWith('/afterhours.wav')) {
        afterhoursRequested = true;
      }
      const wavEntry = Object.keys(wavBuffers).find((filename) =>
        url.pathname.endsWith(`/${filename}`)
      );
      if (wavEntry) {
        await request.respond({
          status: 200,
          contentType: 'audio/wav',
          body: wavBuffers[wavEntry],
        });
        return;
      }
      if (url.pathname === '/api/session/keys' && request.method() === 'POST') {
        await request.respond({
          status: 200,
          contentType: 'application/json',
          headers: { 'X-Session-ID': SESSION_ID },
          body: JSON.stringify({ status: 'success', session_id: SESSION_ID, has_valid_keys: true }),
        });
        return;
      }
      await request.continue();
    })().catch((error) => {
      diagnostics.interceptionErrors.push(error.message);
      void request.abort().catch(() => {});
    });
  });

  await page.goto(diagnostics.origin, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await waitForStartGate(page);
  validateFixtureManifest(partialManifest, PARTIAL_PLAYLIST, new Set(['bgm_afterhours']));
  await submitAndEnterBar(page, { includeCartesiaKey: false });
  await waitForSnapshot(page, 'BarScene', {
    currentKey: 'bgm_lounge',
    isPlaying: true,
    playlistKeys: PARTIAL_PLAYLIST,
  });

  await page.click('#track-next');
  await waitForSnapshot(page, 'BarScene', { currentKey: 'bgm_midnight', isPlaying: true });
  await page.click('#track-prev');
  await page.waitForFunction(
    () => {
      const scene = window.__MAYA_GAME__?.scene.getScene('BarScene');
      const snapshot = scene?.getSoundManager?.().getSnapshot();
      return snapshot && snapshot.currentKey !== 'bgm_midnight';
    },
    { timeout: 5000, polling: 100 }
  );
  await waitForSnapshot(page, 'BarScene', { currentKey: 'bgm_lounge', isPlaying: true });
  assert.equal(afterhoursRequested, false, 'Placeholder audio must not be requested or played.');

  diagnostics.assertClean(page);
  console.log('✅ [smoke-test] Partial playlist skips the unavailable track.');
  await page.close();
}

async function runSmokeTest() {
  let browser = null;
  let previewProcess = null;
  const pageErrors = [];
  const consoleLogs = [];
  const asset404s = [];
  const interceptionErrors = [];
  const expectedConsoleErrors = [];
  let secretLeakDetected = false;

  const pushBounded = (target, value, limit = 200) => {
    target.push(value);
    if (target.length > limit) target.splice(0, target.length - limit);
  };

  try {
    const realManifest = JSON.parse(
      await readFile(new URL('../public/assets/manifest.json', import.meta.url), 'utf8')
    );
    validateManifestStructure(realManifest);
    const PORT = await getFreePort();
    const origin = `http://localhost:${PORT}/`;
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
            const req = http.get(origin, (res) => {
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

    const diagnostics = {
      origin,
      interceptionErrors,
      expectedConsoleErrors,
      attach(page) {
        page.on('pageerror', (err) => {
          console.error('[smoke-test] Browser pageerror:', err.message);
          pushBounded(pageErrors, err.message);
        });
        page.on('console', (msg) => {
          const text = msg.text();
          if (text.includes(DUMMY_GCP_PROJECT) || text.includes(DUMMY_CARTESIA_KEY)) {
            secretLeakDetected = true;
          }
          pushBounded(consoleLogs, text);
          if (msg.type() === 'error') {
            const expectedIndex = expectedConsoleErrors.indexOf(text);
            if (expectedIndex >= 0) {
              expectedConsoleErrors.splice(expectedIndex, 1);
            } else {
              console.error('[smoke-test] Browser console error:', text);
              pushBounded(pageErrors, text);
            }
          }
        });
        page.on('response', (response) => {
          const url = new URL(response.url());
          if (response.status() === 404 && url.pathname.startsWith('/assets/')) {
            pushBounded(asset404s, url.pathname);
          }
        });
      },
      assertClean() {
        assert.deepEqual(interceptionErrors, [], 'Request interception failed.');
        assert.deepEqual(asset404s, [], 'Unexpected asset 404 responses.');
        assert.deepEqual(expectedConsoleErrors, [], 'Expected console error was not observed.');
        assert.deepEqual(pageErrors, [], 'Unexpected browser page/console errors.');
        assert.equal(secretLeakDetected, false, 'Dummy secrets appeared in captured console output.');
        const captured = consoleLogs.join('\n');
        assert.ok(!captured.includes(DUMMY_GCP_PROJECT), 'GCP secret appeared in console logs.');
        assert.ok(!captured.includes(DUMMY_CARTESIA_KEY), 'Cartesia secret appeared in console logs.');
      },
    };

    await runMediaPass(browser, realManifest, diagnostics);
    await runPlaceholderPass(browser, realManifest, diagnostics);
    await runPartialPass(browser, realManifest, diagnostics);
    diagnostics.assertClean();

    console.log('✅ [smoke-test] All browser passes completed successfully:');
    console.log('   - Isolated ephemeral Vite preview and Chrome lifecycle verified');
    console.log('   - Every load gated by Boot -> Preload -> StartScene');
    console.log('   - Credential pending, validation failure, and success paths verified');
    console.log('   - Native accessible controls and keyboard submission verified');
    console.log('   - Start/bar music lifecycle, wrapping, pause/resume, and auto-advance verified');
    console.log('   - Placeholder and partial soundtrack filtering verified');
    console.log('   - Three-track partial playlist backward wrapping verified');
    console.log('   - Zero unexpected browser/asset errors verified');

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
