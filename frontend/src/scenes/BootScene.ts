import Phaser from 'phaser';

export class BootScene extends Phaser.Scene {
  constructor() {
    super('BootScene');
  }

  preload(): void {
    // Set texture scale filter mode to Nearest for crisp 2D pixel art
    this.textures.on('onload', (key: string) => {
      const texture = this.textures.get(key);
      if (texture) {
        texture.setFilter(Phaser.Textures.FilterMode.NEAREST);
      }
    });
  }

  create(): void {
    console.log('[BootScene] Engine initialized with pixelArt: true');
    this.scene.start('PreloadScene');
  }
}
