import Phaser from 'phaser';
import { BootScene } from './scenes/BootScene';
import { PreloadScene } from './scenes/PreloadScene';
import { BarScene } from './scenes/BarScene';
import { HUDOverlayScene } from './scenes/HUDOverlayScene';

// Phaser 3 Game Engine Configuration for 2D Retro Pixel Art
export const config: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  parent: 'game-container',
  width: 640,
  height: 360,
  pixelArt: true, // Enforces nearest-neighbor crisp pixel scaling
  roundPixels: true,
  backgroundColor: '#0b0a12',
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH
  },
  scene: [BootScene, PreloadScene, BarScene, HUDOverlayScene]
};

export const game = new Phaser.Game(config);
