# Design Specification: Phaser 3 Pixel Art Engine Migration for MayaMCP

## Executive Summary
MayaMCP is transitioning from a Gradio-based interface to a bespoke 2D pixel-art in-browser game engine built with **Phaser 3**, inspired by *VA-11 Hall-A: Cyberpunk Bartender Action*. This document outlines the technical architecture, component breakdown, backend integration, and deployment strategy for Modal Labs.

---

## Architectural Overview

```
+-----------------------------------------------------------------------------------+
|                                Browser / Client                                   |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                           Phaser 3 Game Engine                              |  |
|  |                                                                             |  |
|  |  +-------------------+  +---------------------+  +-----------------------+  |  |
|  |  |   BarScene (2D)   |  | HUDOverlayScene     |  | Sound & Viseme Mgr    |  |  |
|  |  | - Pixel Art Canvas|  | - Dialogue Window   |  | - BGM Jukebox         |  |  |
|  |  | - Maya Sprite     |  | - Drink Mixer UI    |  | - Speech Audio Sync   |  |  |
|  |  | - Mouth Flap Layer|  | - Crypto Payment Modal| - SFX Trigger Bus    |  |  |
|  |  +-------------------+  +---------------------+  +-----------------------+  |  |
|  +-----------------------------------------------------------------------------+  |
|                                      ^                                            |
|                                      | SSE / WebSockets                           |
+--------------------------------------|--------------------------------------------+
                                       |
+--------------------------------------|--------------------------------------------+
|                               Modal Labs Container                                |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                               FastAPI Server                                |  |
|  |                                                                             |  |
|  |  +-------------------+  +---------------------+  +-----------------------+  |  |
|  |  | /static Asset Svc |  | /api/chat/stream    |  | /a2a & Payment RPCs   |  |  |
|  |  | (Vite SPA Bundle) |  | (Gemini 3.6 + ADK)  |  | (Coinbase CDP Agent)  |  |  |
|  |  +-------------------+  +---------------------+  +-----------------------+  |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## Core Components

### 1. Phaser 3 Engine Configuration
* **Pixel Art Mode:** `pixelArt: true` configured on game initialization to enforce nearest-neighbor texture filtering (no blur on retro sprites).
* **Resolution & Scaling:** Base canvas resolution set to 640×360 or 960×540, scaled dynamically to viewport aspect ratio using `Phaser.Scale.FIT` and `Phaser.Scale.CENTER_BOTH`.
* **Scene Architecture:**
  * `BootScene`: Initializes engine settings, crisp pixel scaling, and global state keys.
  * `PreloadScene`: Loads asset manifest (`assets_manifest.json`), sprite sheets, audio buffers, and retro bitmap fonts.
  * `BarScene`: Renders cyberpunk bar background, ambient particle effects (neon glow, cocktail steam), and Maya's multi-layered character sprite.
  * `HUDOverlayScene`: Renders dialogue window, interactive drink mixing controls, recipe book overlay, and CDP payment modal.

### 2. Maya Character Sprite & Mouth-Flap System
* **Layered Composition:**
  1. Base Body Sprite (`maya_body`)
  2. Expression / Eyes Layer (`maya_eyes_blink`, `maya_eyes_smile`, `maya_eyes_surprised`)
  3. Mouth Flap Layer (`mouth_closed`, `mouth_talk_a`, `mouth_talk_e`, `mouth_talk_o`)
* **Viseme & Dialogue Synchronization:**
  * Backend emits SSE events containing text chunks, audio playback timestamps, or viseme identifiers (`A`, `E`, `I`, `O`, `U`, `M`).
  * `VisemeController` listens to audio amplitude or viseme event payloads to animate `mouth_flap` frames in real time during TTS speech playback.

### 3. Audio Engine & Jukebox
* **Web Audio Channels:**
  * `BGM Channel`: Loopable synthwave jukebox track playlist with fading transitions and title notifications.
  * `Speech Channel`: Streamed audio buffer playback from Cartesia TTS.
  * `SFX Bus`: Sound effects for ice dropping, cocktail shaker mixing, glass sliding, and payment confirmation chimes.

### 4. Backend Communication Layer
* **SSE Endpoint (`/api/chat/stream`):** Replaces legacy Gradio request-response handlers with asynchronous Server-Sent Events delivering:
  * Gemini 3.6 Flash generated response tokens.
  * Speech synthesis audio URLs / base64 audio chunks.
  * Viseme alignment cues.
  * Bartending state updates (drink served, tip registered, payment requested).
* **Stateless BYOK Protocol:** API keys passed securely per session header or initial handshake token.

### 5. Modal Labs Deployment (`deploy.py`)
* Replaces `mount_gradio_app` in `deploy.py` with FastAPI `StaticFiles` mounting the Vite production bundle (`dist/`) at root `/`.
* Retains health checks (`/healthz`), distributed session state (`modal.Dict`), and Memvid/FAISS RAG volume mounts (`modal.Volume`).

---

## Future Asset Integration Framework
The engine uses a declarative JSON manifest structure (`assets/manifest.json`), allowing Antigravity to easily register new audio files, sprite atlases, and fonts without modifying core engine logic:

```json
{
  "spritesheets": [
    { "key": "maya_portrait", "path": "assets/sprites/maya_portrait.png", "frameWidth": 128, "frameHeight": 128 }
  ],
  "audio": [
    { "key": "bgm_valhalla", "path": "assets/audio/bgm_valhalla.mp3", "type": "music" },
    { "key": "sfx_pour", "path": "assets/audio/pour.wav", "type": "sfx" }
  ]
}
```
