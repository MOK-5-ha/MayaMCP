import Phaser from 'phaser';

export interface ChipBarCallbacks {
  /** Invoked when the user clicks a chip; the chip text becomes the next user message. */
  onChipClick: (text: string) => void;
}

interface ChipPayload {
  text: string;
  type: string;
  action_id?: string | null;
}

const POLL_INTERVAL_MS = 500;
const MAX_POLLS = 8;

/**
 * Quick-reply chip bar rendered as a DOM overlay above the dialogue box.
 * Chips are generated asynchronously after each chat turn, so the bar polls
 * GET /api/v1/chips for a bounded window once the stream completes, then
 * renders native buttons (keyboard-operable, >=44px targets, aria-live status).
 */
export class ChipBar {
  private scene: Phaser.Scene;
  private callbacks: ChipBarCallbacks;
  private domElement: Phaser.GameObjects.DOMElement;
  private root: HTMLElement;
  private status: HTMLElement;
  private buttons: HTMLElement;
  private pollTimer: number | null = null;
  private pollCount = 0;
  private destroyed = false;

  constructor(
    scene: Phaser.Scene,
    x: number,
    y: number,
    width: number,
    callbacks: ChipBarCallbacks
  ) {
    this.scene = scene;
    this.callbacks = callbacks;
    this.domElement = this.scene.add.dom(x, y).createFromHTML(`
      <section id="chip-bar" class="chip-bar" aria-label="Suggested replies">
        <div id="chip-status" class="chip-status" aria-live="polite" aria-atomic="true"></div>
        <div id="chip-buttons" class="chip-buttons" role="group" aria-label="Suggested reply buttons"></div>
      </section>
    `).setOrigin(0, 0);

    this.root = this.domElement.node.querySelector<HTMLElement>('#chip-bar')!;
    this.root.style.width = `${width}px`;
    this.status = this.root.querySelector<HTMLElement>('#chip-status')!;
    this.buttons = this.root.querySelector<HTMLElement>('#chip-buttons')!;
    this.status.textContent = '';
    this.root.classList.add('is-hidden');
    this.scene.events.once(Phaser.Scenes.Events.SHUTDOWN, this.destroy, this);
  }

  /** Begin polling for chips after a completed chat turn. */
  public startPolling(): void {
    if (this.destroyed) return;
    this.stopPolling();
    this.pollCount = 0;
    this.root.classList.remove('is-hidden');
    this.buttons.replaceChildren();
    this.status.textContent = 'Maya is thinking of suggestions…';
    this.pollTimer = window.setInterval(() => void this.pollTick(), POLL_INTERVAL_MS);
  }

  public destroy(): void {
    if (this.destroyed) return;
    this.destroyed = true;
    this.stopPolling();
    this.domElement.destroy();
  }

  private stopPolling(message?: string): void {
    if (this.pollTimer !== null) {
      window.clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
    if (message !== undefined && !this.destroyed) {
      this.status.textContent = message;
    }
  }

  private async pollTick(): Promise<void> {
    if (this.destroyed) return;
    this.pollCount += 1;
    if (this.pollCount > MAX_POLLS) {
      this.root.classList.add('is-hidden');
      this.stopPolling();
      return;
    }
    try {
      const sessionId = localStorage.getItem('maya_session_id') ?? '';
      const response = await fetch('/api/v1/chips', {
        headers: sessionId ? { 'X-Session-ID': sessionId } : {},
      });
      if (!response.ok) {
        throw new Error(`chips poll failed: ${response.status}`);
      }
      const data: { chips?: ChipPayload[] } = await response.json();
      if (Array.isArray(data.chips) && data.chips.length > 0) {
        this.stopPolling();
        this.renderChips(data.chips);
      }
    } catch {
      // Transient failures (generation still in flight, restarts): keep polling
      // until the bounded window expires, then hide the bar silently.
    }
  }

  private renderChips(chips: ChipPayload[]): void {
    if (this.destroyed) return;
    this.buttons.replaceChildren();
    for (const chip of chips) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'chip-button';
      button.textContent = chip.text;
      button.dataset.chipType = chip.type;
      if (chip.action_id) {
        button.dataset.actionId = chip.action_id;
      }
      button.addEventListener('click', this.handleChipClick);
      this.buttons.appendChild(button);
    }
    this.status.textContent = '';
    this.root.classList.remove('is-hidden');
  }

  private handleChipClick = (event: MouseEvent): void => {
    if (this.destroyed) return;
    const target = event.currentTarget as HTMLButtonElement | null;
    if (!target) return;
    this.stopPolling();
    this.root.classList.add('is-hidden');
    this.buttons.replaceChildren();
    this.callbacks.onChipClick(target.textContent ?? '');
  };
}
