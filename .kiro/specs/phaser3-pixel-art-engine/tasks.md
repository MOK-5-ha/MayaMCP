# Task Matrix: Phaser 3 Pixel Art Engine Implementation Plan

This document outlines the execution tracks and test-driven tasks for implementing the Phaser 3 2D pixel-art game engine for MayaMCP.

---

## Execution Overview

> [!TIP] PARALLEL EXECUTION
> Tracks 1 (Backend SSE API) and Track 2 (Phaser 3 Core Setup) can be executed concurrently.
> Track 3 (Mouth-Flap Sync) and Track 4 (Audio Subsystem) can also be developed in parallel once Track 2 is complete.

```
Track 1: Backend SSE & Static Router
  ├── Task 1.1: FastAPI SSE Streaming Adapter [FR-2.2]
  └── Task 1.2: Modal Labs Static Bundle Mount [NFR-3]
       │
       ├─────────────────────────────────────────────┐
       ▼                                             ▼
Track 2: Phaser 3 Core Engine              Track 5: Cyberpunk HUD & Payments
  ├── Task 2.1: Canvas & Scale Manager [FR-1]       ├── Task 5.1: Bartending Controls [FR-5.1]
  └── Task 2.2: Asset Manifest Loader [FR-6]        └── Task 5.2: CDP Payment Modal [FR-5.2]
       │                                             │
       ├───────────────────────┐                     │
       ▼                       ▼                     ▼
Track 3: Character & Visemes  Track 4: Audio Engine  Track 6: E2E Integration
  ├── Task 3.1: Sprite Layer  ├── Task 4.1: BGM Bus   └── Task 6.1: Full Playthrough
  └── Task 3.2: Mouth-Flap    └── Task 4.2: SFX Bus
```

---

## Detailed Task Breakdown

### Track 1: Backend SSE Adapter & Static Server [COMPLETE]

#### Task 1.1: Implement FastAPI SSE Endpoint for Streamed Chat & Visemes [COMPLETED]
* **Status:** `[x]` Completed
* **Traceability:** `FR-2.2`, `NFR-2`
* **Dependencies:** None
* **Description:** Create `/api/chat/stream` SSE endpoint in FastAPI that wraps `Runner` / Gemini 3.6 Flash responses, emitting structured JSON events containing text tokens, base64 audio chunks, and viseme timing tags.
* **TDD Acceptance Criteria:**
  ```python
  def test_chat_stream_sse_endpoint():
      # Unit test verifying SSE stream yields event-stream format with 'data: {...}' payloads
      client = TestClient(app)
      response = client.post("/api/chat/stream", json={"message": "Pour me a drink"})
      assert response.status_code == 200
      assert "text/event-stream" in response.headers["content-type"]
  ```

#### Task 1.2: Update Modal Labs Deployment for Static Vite Bundle Mount [COMPLETED]
* **Status:** `[x]` Completed
* **Traceability:** `NFR-3`
* **Dependencies:** Task 1.1
* **Description:** Modify [`deploy.py`](file:///Users/pretermodernist/.gemini/antigravity/worktrees/MayaMCP/migrate_gradio_to_engine/deploy.py) to mount the compiled frontend `dist/` directory using FastAPI `StaticFiles(directory="/app/frontend/dist", html=True)`.

---

### Track 2: Phaser 3 Core Engine Setup [COMPLETE]

> [!TIP] PARALLEL EXECUTION
> Track 2 can be developed alongside Track 1 using mocked backend SSE data.

#### Task 2.1: Initialize Phaser 3 Canvas with Nearest-Neighbor Pixel Art Engine [COMPLETED]
* **Status:** `[x]` Completed
* **Traceability:** `FR-1.1`, `FR-1.2`
* **Dependencies:** None
* **Description:** Set up Vite project (`frontend/`) with Phaser 3, configuring `pixelArt: true` and responsive scale manager (`Phaser.Scale.FIT`).
* **BDD Acceptance Criteria:**
  ```gherkin
  Given the game canvas initializes in the browser
  When inspect element checks game config
  Then game.config.pixelArt is true
  And textures use NearestFilter rendering
  ```

#### Task 2.2: Implement Declarative Asset Loader (`assets_manifest.json`) [COMPLETED]
* **Status:** `[x]` Completed
* **Traceability:** `FR-6.1`, `FR-6.2`
* **Dependencies:** Task 2.1
* **Description:** Build `PreloadScene` to asynchronously fetch `assets/manifest.json` and load sprite sheets, bitmap fonts, and audio buffers with fallback handling for missing files.

---

### Track 3: Character Sprite Layer & Viseme Mouth-Flap Controller [COMPLETE]

#### Task 3.1: Create Multi-Layer Character Sprite Component (`MayaCharacter.ts`) [COMPLETED]
* **Status:** `[x]` Completed
* **Traceability:** `FR-3.1`, `FR-3.3`
* **Dependencies:** Task 2.2
* **Description:** Construct composite Phaser Container managing Maya's body base layer, eye blinking timer, and facial expression keyframes.

#### Task 3.2: Implement Audio & Text-Synced Mouth-Flap Animator [COMPLETED]
* **Status:** `[x]` Completed
* **Traceability:** `FR-3.2`, `US-1`
* **Dependencies:** Task 3.1, Task 1.1
* **Description:** Connect SSE speech stream events to `MouthFlapController`. Animate mouth frames (`mouth_talk_a`, `mouth_talk_e`, `mouth_talk_o`) while speech audio is playing, returning to `mouth_closed` on audio `ended` event.

---

### Track 4: Cyberpunk Audio Engine (BGM Jukebox & SFX Bus) [COMPLETE]

> [!TIP] PARALLEL EXECUTION
> Track 4 audio development can run concurrently with Track 3 sprite development.

#### Task 4.1: Implement Jukebox Background Music Channel [COMPLETED]
* **Status:** `[x]` Completed
* **Traceability:** `FR-4.1`
* **Dependencies:** Task 2.2
* **Description:** Build `SoundManager` class managing BGM track queue, volume fade transitions, and track title notifications.

#### Task 4.2: Implement SFX Trigger Bus & Cartesia Speech Channel [COMPLETED]
* **Status:** `[x]` Completed
* **Traceability:** `FR-4.2`, `FR-4.3`
* **Dependencies:** Task 4.1
* **Description:** Create dedicated SFX trigger system (`playSFX('pour')`, `playSFX('clink')`) and high-priority Web Audio bus for Cartesia speech streaming.

---

### Track 5: Cyberpunk Bartending HUD & Payment UI [COMPLETE]

#### Task 5.1: Build Interactive Pixel-Art Drink Mixer HUD [COMPLETED]
* **Status:** `[x]` Completed
* **Traceability:** `FR-5.1`, `US-2`
* **Dependencies:** Task 2.1
* **Description:** Implement `HUDOverlayScene` with pixel-art ingredient buttons, shaker animation trigger, and serve button that sends drink payloads to MayaMCP backend.

#### Task 5.2: Build Coinbase CDP AgentKit Crypto Payment Overlay [COMPLETED]
* **Status:** `[x]` Completed
* **Traceability:** `FR-5.2`
* **Dependencies:** Task 5.1
* **Description:** Build pixel-art styled popup modal for Base Sepolia USDC tip/drink payments with QR code and transaction status spinner.

---

### Track 6: End-to-End Verification [COMPLETE]

#### Task 6.1: Run Full Cyberpunk Bartending Session E2E Test [COMPLETED]
* **Status:** `[x]` Completed
* **Traceability:** All FRs and NFRs
* **Dependencies:** Tracks 1-5
* **Description:** Perform complete visual and functional test of customer ordering drink, Maya speaking with mouth flaps & audio, jukebox music playing, mixing drink, and completing crypto payment.
