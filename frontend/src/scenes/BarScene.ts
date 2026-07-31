import Phaser from 'phaser';
import { MayaCharacter } from '../components/MayaCharacter';
import { SoundManager } from '../utils/SoundManager';

export class BarScene extends Phaser.Scene {
  private neonGlow: Phaser.GameObjects.Graphics | null = null;
  private mayaCharacter: MayaCharacter | null = null;
  private soundManager: SoundManager | null = null;

  constructor() {
    super('BarScene');
  }

  create(): void {
    const { width, height } = this.scale;

    // Draw Cyberpunk Bar Background (Neon Gradient & Pixel Grids)
    const bgGraphics = this.add.graphics();
    bgGraphics.fillStyle(0x0c0b16, 1);
    bgGraphics.fillRect(0, 0, width, height);

    // Neon Accent Grid / Windows
    bgGraphics.lineStyle(1, 0x1f1d36, 0.6);
    for (let x = 0; x < width; x += 32) {
      bgGraphics.lineBetween(x, 0, x, height);
    }
    for (let y = 0; y < height; y += 32) {
      bgGraphics.lineBetween(0, y, width, y);
    }

    // Cyberpunk Bar Counter Surface
    const barCounter = this.add.graphics();
    barCounter.fillStyle(0x16152b, 1);
    barCounter.fillRect(0, height * 0.55, width, height * 0.45);
    
    // Bar Top Neon Strip
    barCounter.fillStyle(0x00f0ff, 1);
    barCounter.fillRect(0, height * 0.55 - 4, width, 4);

    // Animated Neon Atmospheric Glow
    this.neonGlow = this.add.graphics();
    this.neonGlow.fillStyle(0xff007f, 0.08);
    this.neonGlow.fillCircle(width * 0.5, height * 0.3, 200);

    this.tweens.add({
      targets: this.neonGlow,
      alpha: 0.2,
      duration: 2000,
      yoyo: true,
      repeat: -1,
      ease: 'Sine.easeInOut'
    });

    // Instantiate Multi-Layer Maya Character Component at Center Stage
    this.mayaCharacter = new MayaCharacter(this, width * 0.5, height * 0.34);

    // Initialize Cyberpunk Sound & Jukebox Manager
    this.soundManager = new SoundManager(this);
    this.soundManager.playBGM('bgm_lounge');

    console.log('[BarScene] Cyberpunk pixel-art bar environment & Maya character initialized');
  }

  public getMayaCharacter(): MayaCharacter | null {
    return this.mayaCharacter;
  }

  public getSoundManager(): SoundManager | null {
    return this.soundManager;
  }
}
