import Phaser from 'phaser';

export interface AssetManifest {
  version: string;
  spritesheets?: Array<{
    key: string;
    path: string;
    frameWidth: number;
    frameHeight: number;
  }>;
  audio?: Array<{
    key: string;
    path: string;
    type: 'music' | 'sfx';
  }>;
}

export class PreloadScene extends Phaser.Scene {
  private manifestData: AssetManifest | null = null;

  constructor() {
    super('PreloadScene');
  }

  preload(): void {
    // Render retro progress bar
    const width = this.cameras.main.width;
    const height = this.cameras.main.height;
    
    const progressBar = this.add.graphics();
    const progressBox = this.add.graphics();
    progressBox.fillStyle(0x1a1a2e, 0.8);
    progressBox.fillRect(width / 2 - 160, height / 2 - 25, 320, 50);

    const loadingText = this.make.text({
      x: width / 2,
      y: height / 2 - 50,
      text: 'MAYAMCP // INITIALIZING SYSTEMS...',
      style: {
        font: '14px Courier, monospace',
        color: '#00f0ff'
      }
    });
    loadingText.setOrigin(0.5, 0.5);

    this.load.on('progress', (value: number) => {
      progressBar.clear();
      progressBar.fillStyle(0x00f0ff, 1);
      progressBar.fillRect(width / 2 - 150, height / 2 - 15, 300 * value, 30);
    });

    this.load.on('loaderror', (fileObj: Phaser.Loader.File) => {
      console.warn(`[PreloadScene] Asset load fallback for missing file: ${fileObj.key} (${fileObj.url})`);
    });

    // Load manifest JSON
    this.load.json('asset_manifest', 'assets/manifest.json');
  }

  create(): void {
    this.manifestData = this.cache.json.get('asset_manifest') as AssetManifest;
    if (this.manifestData) {
      console.log('[PreloadScene] Asset manifest loaded successfully:', this.manifestData.version);
    } else {
      console.warn('[PreloadScene] Asset manifest missing; proceeding with default dynamic canvas assets.');
    }

    // Launch main BarScene and HUD overlay scene in parallel
    this.scene.start('BarScene');
    this.scene.launch('HUDOverlayScene');
  }
}
