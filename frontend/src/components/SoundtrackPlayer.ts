import Phaser from 'phaser';
import type { SoundManager } from '../utils/SoundManager';

export class SoundtrackPlayer {
  private scene: Phaser.Scene;
  private manager: SoundManager;
  private domElement: Phaser.GameObjects.DOMElement;
  private root: HTMLElement;
  private title: HTMLElement;
  private status: HTMLElement;
  private previous: HTMLButtonElement;
  private toggle: HTMLButtonElement;
  private next: HTMLButtonElement;
  private unsubscribe: () => void;
  private destroyed = false;

  constructor(scene: Phaser.Scene, manager: SoundManager, x: number, y: number) {
    this.scene = scene;
    this.manager = manager;
    this.domElement = this.scene.add.dom(x, y).createFromHTML(`
      <section id="soundtrack-player" class="soundtrack-player" aria-label="Soundtrack player">
        <div id="track-title" class="track-title">SOUNDTRACK</div>
        <div id="track-status" class="track-status" aria-live="polite" aria-atomic="true"></div>
        <div class="track-controls">
          <button id="track-prev" type="button" aria-label="Previous track">PREV</button>
          <button id="track-toggle" type="button" aria-label="Pause soundtrack">PAUSE</button>
          <button id="track-next" type="button" aria-label="Next track">NEXT</button>
        </div>
      </section>
    `).setOrigin(0, 0);

    this.root = this.domElement.node.querySelector<HTMLElement>('#soundtrack-player')!;
    this.title = this.root.querySelector<HTMLElement>('#track-title')!;
    this.status = this.root.querySelector<HTMLElement>('#track-status')!;
    this.previous = this.root.querySelector<HTMLButtonElement>('#track-prev')!;
    this.toggle = this.root.querySelector<HTMLButtonElement>('#track-toggle')!;
    this.next = this.root.querySelector<HTMLButtonElement>('#track-next')!;

    this.previous.addEventListener('click', this.handlePrevious);
    this.toggle.addEventListener('click', this.handleToggle);
    this.next.addEventListener('click', this.handleNext);
    this.unsubscribe = this.manager.onChange(this.refresh);
    this.refresh();
    this.scene.events.once(Phaser.Scenes.Events.SHUTDOWN, this.destroy, this);
  }

  public destroy(): void {
    if (this.destroyed) return;
    this.destroyed = true;
    this.unsubscribe();
    this.previous.removeEventListener('click', this.handlePrevious);
    this.toggle.removeEventListener('click', this.handleToggle);
    this.next.removeEventListener('click', this.handleNext);
    this.domElement.destroy();
  }

  private handlePrevious = (): void => {
    this.manager.previousTrack();
  };

  private handleToggle = (): void => {
    this.manager.togglePause();
  };

  private handleNext = (): void => {
    this.manager.nextTrack();
  };

  private refresh = (): void => {
    if (this.destroyed) return;

    const snapshot = this.manager.getSnapshot();
    const available = this.manager.hasPlayableTracks();
    this.root.classList.toggle('is-unavailable', !available);
    this.title.textContent = snapshot.currentTitle ?? 'SOUNDTRACK';
    this.status.textContent = available
      ? snapshot.isPaused
        ? 'Paused'
        : snapshot.isPlaying
          ? 'Now playing'
          : 'Ready to play'
      : 'Soundtrack unavailable — audio files not installed';

    for (const button of [this.previous, this.toggle, this.next]) {
      button.disabled = !available;
    }

    const action = snapshot.isPaused ? 'Resume' : snapshot.isPlaying ? 'Pause' : 'Play';
    this.toggle.textContent = action.toUpperCase();
    this.toggle.setAttribute('aria-label', `${action} soundtrack`);
  };
}
