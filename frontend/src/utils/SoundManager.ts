import Phaser from 'phaser';

export interface SoundtrackTrack {
  key: string;
  title: string;
}

export interface SoundManagerSnapshot {
  currentKey: string | null;
  currentTitle: string | null;
  isPlaying: boolean;
  isPaused: boolean;
  playlistKeys: string[];
  intendedKey: string | null;
}

export class SoundManager {
  private scene: Phaser.Scene;
  private currentBGM: Phaser.Sound.BaseSound | null = null;
  private currentKey: string | null = null;
  private currentTitle: string | null = null;
  private intendedKey: string | null = null;
  private playlist: SoundtrackTrack[] = [];
  private currentIndex = -1;
  private currentLoop = true;
  private destroyed = false;
  private bgmVolume = 0.5;
  private sfxVolume = 0.8;
  private changeListeners = new Set<() => void>();

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
    this.scene.sound.on(Phaser.Sound.Events.UNLOCKED, this.handleUnlocked, this);
    this.scene.events.once(Phaser.Scenes.Events.SHUTDOWN, this.destroy, this);
  }

  public setPlaylist(tracks: SoundtrackTrack[]): void {
    this.stopCurrent();
    this.playlist = tracks.map((track) => ({ ...track }));
    this.emitChange();
  }

  public playTrack(index: number): boolean {
    if (this.destroyed) return false;

    const availableIndex = this.findAvailableIndex(index);
    if (availableIndex < 0) {
      this.stopCurrent();
      this.emitChange();
      return false;
    }

    const track = this.playlist[availableIndex];
    const started = this.playBGM(track.key, false, track.title);
    this.currentIndex = started ? availableIndex : -1;
    this.emitChange();
    return started;
  }

  public nextTrack(): boolean {
    return this.playTrack(this.currentIndex < 0 ? 0 : this.currentIndex + 1);
  }

  public previousTrack(): boolean {
    const index = this.currentIndex < 0 ? this.playlist.length - 1 : this.currentIndex - 1;
    return this.playTrack(index);
  }

  public playBGM(key: string, loop = true, title?: string): boolean {
    this.stopCurrent();
    if (this.destroyed || !this.hasAudio(key)) {
      this.emitChange();
      return false;
    }

    this.currentKey = key;
    this.currentTitle = title ?? key;
    this.intendedKey = key;
    this.currentLoop = loop;
    this.currentBGM = this.scene.sound.add(key, {
      loop,
      volume: this.bgmVolume
    });
    this.currentBGM.once(Phaser.Sound.Events.COMPLETE, this.handleComplete, this);
    this.startCurrent();
    return true;
  }

  public togglePause(): boolean {
    if (this.destroyed) return false;
    if (!this.currentBGM) {
      return this.playTrack(this.currentIndex < 0 ? 0 : this.currentIndex);
    }
    if (this.currentBGM.isPaused) {
      if (this.scene.sound.locked) return false;
      const resumed = this.currentBGM.resume();
      this.emitChange();
      return resumed;
    }
    if (this.currentBGM.isPlaying) {
      const paused = this.currentBGM.pause();
      this.emitChange();
      return paused;
    }
    return this.startCurrent();
  }

  public stopBGM(): void {
    this.stopCurrent();
    this.emitChange();
  }

  public hasPlayableTracks(): boolean {
    return this.playlist.some((track) => this.hasAudio(track.key));
  }

  public getSnapshot(): SoundManagerSnapshot {
    return {
      currentKey: this.currentKey,
      currentTitle: this.currentTitle,
      isPlaying: Boolean(this.currentBGM?.isPlaying),
      isPaused: Boolean(this.currentBGM?.isPaused),
      playlistKeys: this.playlist.map((track) => track.key),
      intendedKey: this.intendedKey
    };
  }

  public onChange(listener: () => void): () => void {
    this.changeListeners.add(listener);
    return () => this.changeListeners.delete(listener);
  }

  public playSFX(key: string): void {
    if (!this.destroyed && this.hasAudio(key)) {
      this.scene.sound.play(key, { volume: this.sfxVolume });
    }
  }

  public setBGMVolume(volume: number): void {
    this.bgmVolume = Phaser.Math.Clamp(volume, 0, 1);
    if (this.currentBGM && 'setVolume' in this.currentBGM) {
      (this.currentBGM as Phaser.Sound.WebAudioSound).setVolume(this.bgmVolume);
    }
  }

  public setSFXVolume(volume: number): void {
    this.sfxVolume = Phaser.Math.Clamp(volume, 0, 1);
  }

  public playSpeechAudioBase64(base64Data: string, onEnded?: () => void): void {
    try {
      const audioUrl = `data:audio/wav;base64,${base64Data}`;
      const audio = new Audio(audioUrl);
      audio.volume = 1.0;
      audio.onended = () => {
        if (onEnded) onEnded();
      };
      audio.play().catch((error) => {
        console.warn('[SoundManager] Speech audio autoplay prevented:', error);
        if (onEnded) onEnded();
      });
    } catch (error) {
      console.error('[SoundManager] Failed to decode base64 speech audio:', error);
      if (onEnded) onEnded();
    }
  }

  public destroy(): void {
    if (this.destroyed) return;
    this.destroyed = true;
    this.scene.sound.off(Phaser.Sound.Events.UNLOCKED, this.handleUnlocked, this);
    this.stopCurrent();
    this.changeListeners.clear();
  }

  private hasAudio(key: string): boolean {
    return this.scene.cache.audio.exists(key) || this.scene.sound.get(key) !== null;
  }

  private findAvailableIndex(startIndex: number): number {
    const count = this.playlist.length;
    if (count === 0) return -1;

    const normalized = ((startIndex % count) + count) % count;
    for (let offset = 0; offset < count; offset += 1) {
      const index = (normalized + offset) % count;
      if (this.hasAudio(this.playlist[index].key)) return index;
    }
    return -1;
  }

  private startCurrent(): boolean {
    if (
      this.destroyed ||
      !this.currentBGM ||
      this.scene.sound.locked
    ) {
      this.emitChange();
      return false;
    }

    const started = this.currentBGM.play();
    this.emitChange();
    return started;
  }

  private handleUnlocked(): void {
    if (
      this.intendedKey &&
      this.currentBGM &&
      !this.currentBGM.isPlaying &&
      !this.currentBGM.isPaused
    ) {
      this.startCurrent();
    }
  }

  private handleComplete(): void {
    if (this.destroyed || this.currentLoop) return;
    if (this.playlist.length > 0) {
      this.nextTrack();
    } else {
      this.stopBGM();
    }
  }

  private stopCurrent(): void {
    if (this.currentBGM) {
      this.currentBGM.off(Phaser.Sound.Events.COMPLETE, this.handleComplete, this);
      this.currentBGM.stop();
      this.currentBGM.destroy();
    }
    this.currentBGM = null;
    this.currentKey = null;
    this.currentTitle = null;
    this.intendedKey = null;
    this.currentIndex = -1;
    this.currentLoop = true;
  }

  private emitChange(): void {
    for (const listener of this.changeListeners) listener();
  }
}
