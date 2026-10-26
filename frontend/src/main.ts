import Phaser from 'phaser';
import { BootScene } from './scenes/BootScene';
import { PreloadScene } from './scenes/PreloadScene';
import { StartScene } from './scenes/StartScene';
import { BarScene } from './scenes/BarScene';
import { HUDOverlayScene } from './scenes/HUDOverlayScene';
import './styles.css';

export const config: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  parent: 'game-container',
  width: 640,
  height: 360,
  pixelArt: true,
  roundPixels: true,
  backgroundColor: '#0b0a12',
  dom: {
    createContainer: true
  },
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH
  },
  scene: [BootScene, PreloadScene, StartScene, BarScene, HUDOverlayScene]
};

export const game = new Phaser.Game(config);

// Expose game instance for runtime smoke tests and accessibility tree inspection
if (typeof window !== 'undefined') {
  (window as unknown as { __MAYA_GAME__?: Phaser.Game }).__MAYA_GAME__ = game;
}
