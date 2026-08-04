# Requirements Specification: Phaser 3 Pixel Art Engine Migration for MayaMCP

## Glossary
* **Phaser 3**: 2D HTML5 game framework rendering via WebGL / HTML Canvas.
* **Viseme**: A visual representation of a spoken phoneme (mouth position during speech).
* **Mouth Flap**: Sprite animation frames representing lip movement during dialogue playback.
* **Pixel Art Mode**: Rendering configuration enforcing nearest-neighbor texture filtering.
* **Jukebox**: Audio management subsystem handling background music (BGM) playback.
* **SSE (Server-Sent Events)**: Uni-directional streaming protocol over HTTP from FastAPI to client.

---

## Functional Requirements (FR)

### FR-1: Pixel-Art Rendering Engine
* **FR-1.1**: The application MUST render all game graphics using Phaser 3 with nearest-neighbor texture filtering (`pixelArt: true`).
* **FR-1.2**: The canvas MUST scale dynamically to fit the browser viewport while preserving a fixed 16:9 pixel aspect ratio without blur or stretching.

### FR-2: Cyberpunk Bartending Dialogue UI
* **FR-2.1**: Dialogue text MUST be rendered in a typewriter/bitmap style window with retro typography.
* **FR-2.2**: Dialogue text MUST stream progressively in sync with incoming SSE response events from Gemini 3.6 Flash.

### FR-3: Character Sprite & Expression System
* **FR-3.1**: Maya's avatar MUST be rendered using a multi-layer sprite system (base, eyes/blinking, mouth).
* **FR-3.2**: Mouth flap animations MUST play dynamically while speech audio is playing and pause when speech ends.
* **FR-3.3**: Character facial expression frames MUST update based on conversation phase (e.g., greeting, drink ordering, payment, farewell).

### FR-4: Jukebox & Audio Subsystem
* **FR-4.1**: The jukebox MUST provide background music (BGM) playback with play/pause, next/previous track controls, and volume adjustment.
* **FR-4.2**: The audio engine MUST trigger distinct sound effects (SFX) for drink mixing, glass clinking, ice dropping, and payment completion.
* **FR-4.3**: Speech audio from Cartesia TTS MUST play over a dedicated high-priority audio bus without distorting or muting BGM.

### FR-5: Interactive Bartending & Payment Interface
* **FR-5.1**: The HUD MUST provide interactive 2D pixel-art drink mixing controls (ingredient selection, shaker, serve action).
* **FR-5.2**: The UI MUST provide a crypto payment modal supporting Base Sepolia / Coinbase CDP wallet transactions.

### FR-6: Declarative Asset Extensibility
* **FR-6.1**: All game assets (sprites, audio, fonts) MUST be defined in a declarative `assets_manifest.json` file.
* **FR-6.2**: The asset loader MUST gracefully handle missing optional SFX/BGM files without throwing fatal scene errors.

---

## Non-Functional Requirements (NFR)

* **NFR-1 (Bundle Size)**: The core compiled web engine bundle (excluding external audio assets) MUST be less than 3 MB.
* **NFR-2 (Latency)**: UI response to backend SSE text chunks MUST occur in under 50ms.
* **NFR-3 (Modal Labs Compatibility)**: The static frontend MUST mount cleanly under FastAPI via Modal Labs ASGI deployment without requiring separate server instances.
* **NFR-4 (Accessibility & Fallbacks)**: The game canvas MUST support full keyboard navigation for dialogue advancement and drink selection.

---

## User Stories & BDD Acceptance Criteria

### US-1: Cyberpunk Dialogue & Mouth-Flap Sync
**As a user** chatting with Maya,  
**I want** to see her avatar animate her mouth in sync with spoken dialogue,  
**So that** the interaction feels like an immersive pixel-art bartending visual novel.

#### Scenario: Dialogue Streaming with Mouth Flaps
```gherkin
Given Maya is generating a response via Gemini 3.6 Flash and Cartesia TTS
When the client receives a speech audio stream and text chunks
Then Maya's mouth flap sprite animation plays frame sequence [mouth_open_small, mouth_open_wide, mouth_o]
And when the audio playback completes, Maya's mouth sprite returns to [mouth_closed]
```

### US-2: Interactive Cyberpunk Bartending Controls
**As a user** ordering a drink,  
**I want** an interactive 2D pixel-art drink mixing HUD,  
**So that** I can craft drinks directly in the game UI instead of selecting standard web dropdowns.

#### Scenario: Mixing and Serving a Drink
```gherkin
Given the user is on the drink mixing screen
When the user clicks the "Adelhyde" and "Brantini" ingredient taps
And the user clicks "Shake"
Then the cocktail shaker SFX ("sfx_shaker") plays
And the drink served event is sent to the MayaMCP backend
```

---

## Traceability Matrix

| Requirement | User Story | Components | Verification Method |
|---|---|---|---|
| FR-1.1, FR-1.2 | US-1, US-2 | `BootScene`, `BarScene` | Automated Visual / E2E Test |
| FR-2.1, FR-2.2 | US-1 | `HUDOverlayScene`, SSE Client | Integration Test |
| FR-3.1, FR-3.2, FR-3.3 | US-1 | `VisemeController`, Sprite Manager | Unit & BDD Test |
| FR-4.1, FR-4.2, FR-4.3 | US-1, US-2 | `SoundManager`, Web Audio Bus | Unit Test |
| FR-5.1, FR-5.2 | US-2 | Bartending HUD, CDP Payment Modal | Integration Test |
| NFR-1, NFR-3 | US-1, US-2 | Vite Build, FastAPI Static Mount | Deployment Verification |
