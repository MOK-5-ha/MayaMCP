import Phaser from 'phaser';
import { MANIFEST_REGISTRY_KEY, type AssetManifest } from '../utils/assetManifest';
import { SSEClient } from '../utils/SSEClient';
import { SoundManager } from '../utils/SoundManager';

interface SessionKeyResponse {
  detail?: unknown;
  session_id?: unknown;
  has_valid_keys?: unknown;
}

export class StartScene extends Phaser.Scene {
  private soundManager: SoundManager | null = null;
  private formElement: Phaser.GameObjects.DOMElement | null = null;
  private abortController: AbortController | null = null;
  private sessionClient = new SSEClient();
  private submitting = false;

  constructor() {
    super('StartScene');
  }

  create(): void {
    const { width, height } = this.scale;
    this.submitting = false;
    this.abortController = null;

    if (this.textures.exists('start_bar_exterior')) {
      this.add.image(0, 0, 'start_bar_exterior').setOrigin(0, 0).setDisplaySize(width, height);
    } else {
      this.add.graphics().fillStyle(0x080d18, 1).fillRect(0, 0, width, height);
    }

    this.add.text(326, 24, 'MAYA', {
      font: 'bold 32px Courier, monospace',
      color: '#00f0ff'
    });
    this.add.text(328, 61, 'NEON BARTENDER // ACCESS TERMINAL', {
      font: 'bold 10px Courier, monospace',
      color: '#d7e4f5'
    });

    this.formElement = this.add.dom(326, 78).createFromHTML(`
      <form id="maya-start-form" class="start-form" method="post" action="/api/session/keys" autocomplete="off">
        <h2>ENTER THE BAR</h2>
        <div class="start-field">
          <label for="gcp-project">GCP PROJECT ID (REQUIRED)</label>
          <input id="gcp-project" name="gcp_project" type="text" required
            autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"
            enterkeyhint="next" aria-describedby="gcp-project-hint" placeholder="your-project-id">
          <small id="gcp-project-hint" class="start-hint">Server ADC must have Vertex AI access.</small>
        </div>
        <div class="start-field">
          <label for="cartesia-key">CARTESIA API KEY (OPTIONAL)</label>
          <div class="password-row">
            <input id="cartesia-key" name="cartesia_key" type="password"
              autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"
              enterkeyhint="done" placeholder="Voice disabled if blank">
            <button id="cartesia-visibility" class="password-visibility" type="button"
              aria-label="Show Cartesia API key" aria-controls="cartesia-key" aria-pressed="false">SHOW</button>
          </div>
        </div>
        <div id="start-error" class="start-error" role="alert" aria-live="assertive" aria-atomic="true"></div>
        <button id="start-submit" class="start-submit" type="submit">ENTER THE BAR</button>
      </form>
    `).setOrigin(0, 0);

    this.query<HTMLFormElement>('maya-start-form')?.addEventListener('submit', this.handleSubmit);
    this.query<HTMLButtonElement>('cartesia-visibility')?.addEventListener(
      'click',
      this.handleVisibility
    );

    this.soundManager = new SoundManager(this);
    const manifest = this.registry.get(MANIFEST_REGISTRY_KEY) as AssetManifest | undefined;
    const startKey = manifest?.soundtrack?.startTrack;
    const startTrack = manifest?.audio?.find((track) => track.key === startKey);
    if (startKey && startTrack && !startTrack.placeholder) {
      this.soundManager.playBGM(startKey, true, startTrack.title ?? startKey);
    }

    this.events.once(Phaser.Scenes.Events.SHUTDOWN, this.shutdown, this);
  }

  public getSoundManager(): SoundManager | null {
    return this.soundManager;
  }

  private query<T extends HTMLElement>(id: string): T | null {
    const node = this.formElement?.node as HTMLElement | null | undefined;
    return node?.querySelector<T>(`#${id}`) ?? null;
  }

  private handleVisibility = (): void => {
    const input = this.query<HTMLInputElement>('cartesia-key');
    const button = this.query<HTMLButtonElement>('cartesia-visibility');
    if (!input || !button) return;

    const reveal = input.type === 'password';
    input.type = reveal ? 'text' : 'password';
    button.textContent = reveal ? 'HIDE' : 'SHOW';
    button.setAttribute('aria-pressed', String(reveal));
    button.setAttribute('aria-label', `${reveal ? 'Hide' : 'Show'} Cartesia API key`);
  };

  private setPending(pending: boolean): void {
    this.submitting = pending;
    const form = this.query<HTMLFormElement>('maya-start-form');
    const button = this.query<HTMLButtonElement>('start-submit');
    form?.setAttribute('aria-busy', String(pending));
    if (button) {
      button.disabled = pending;
      button.textContent = pending ? 'VALIDATING...' : 'ENTER THE BAR';
      button.setAttribute('aria-busy', String(pending));
    }
  }

  private handleSubmit = async (event: Event): Promise<void> => {
    event.preventDefault();
    if (this.submitting) return;

    const projectInput = this.query<HTMLInputElement>('gcp-project');
    const cartesiaInput = this.query<HTMLInputElement>('cartesia-key');
    const errorElement = this.query<HTMLElement>('start-error');
    if (!projectInput || !cartesiaInput || !errorElement) return;

    const project = projectInput.value.trim();
    const cartesiaKey = cartesiaInput.value.trim();
    if (!project) {
      errorElement.textContent = 'GCP project ID is required.';
      projectInput.focus();
      return;
    }

    errorElement.textContent = '';
    this.setPending(true);
    this.abortController = new AbortController();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    const existingSessionId = this.sessionClient.getSessionId();
    if (existingSessionId) headers['X-Session-ID'] = existingSessionId;
    const payload: { gcp_project: string; cartesia_key?: string } = { gcp_project: project };
    if (cartesiaKey) payload.cartesia_key = cartesiaKey;

    try {
      const response = await fetch('/api/session/keys', {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
        signal: this.abortController.signal
      });
      const data = await response.json().catch(() => ({})) as SessionKeyResponse;
      if (!response.ok) {
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : 'Vertex AI validation failed. Check the project and ADC access.'
        );
      }
      if (data.has_valid_keys !== true || typeof data.session_id !== 'string') {
        throw new Error('The session could not be started. Please try again.');
      }

      this.sessionClient.setSessionId(data.session_id);
      projectInput.value = '';
      cartesiaInput.value = '';
      this.soundManager?.stopBGM();
      this.scene.start('BarScene');
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      errorElement.textContent = error instanceof Error
        ? error.message
        : 'Unable to validate Vertex AI configuration.';
      this.setPending(false);
    }
  };

  private shutdown(): void {
    this.abortController?.abort();
    this.abortController = null;
    this.query<HTMLFormElement>('maya-start-form')?.removeEventListener('submit', this.handleSubmit);
    this.query<HTMLButtonElement>('cartesia-visibility')?.removeEventListener(
      'click',
      this.handleVisibility
    );
    this.formElement?.destroy();
    this.formElement = null;
  }
}
