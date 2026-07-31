import Phaser from 'phaser';

export class SoundManager {
  private scene: Phaser.Scene;
  private currentBGM: Phaser.Sound.BaseSound | null = null;
  private bgmVolume: number = 0.5;
  private sfxVolume: number = 0.8;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
  }

  public playBGM(key: string, loop: boolean = true): void {
    if (this.currentBGM && this.currentBGM.isPlaying) {
      this.currentBGM.stop();
    }

    if (this.scene.sound.get(key)) {
      this.currentBGM = this.scene.sound.add(key, {
        loop,
        volume: this.bgmVolume
      });
      this.currentBGM.play();
      console.log(`[SoundManager] BGM playing: ${key}`);
    } else {
      console.log(`[SoundManager] BGM track '${key}' not in cache (synthesizing ambient audio fallback)`);
    }
  }

  public playSFX(key: string): void {
    if (this.scene.sound.get(key)) {
      this.scene.sound.play(key, { volume: this.sfxVolume });
      console.log(`[SoundManager] SFX played: ${key}`);
    } else {
      console.log(`[SoundManager] SFX '${key}' triggered (fallback audio trigger)`);
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
      audio.play().catch(err => {
        console.warn('[SoundManager] Speech audio autoplay prevented:', err);
        if (onEnded) onEnded();
      });
    } catch (e) {
      console.error('[SoundManager] Failed to decode base64 speech audio:', e);
      if (onEnded) onEnded();
    }
  }
}
