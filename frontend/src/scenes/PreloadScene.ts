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
    let hasAssetsToLoad = false;

    if (this.manifestData) {
      console.log('[PreloadScene] Asset manifest parsed:', this.manifestData.version);

      if (this.manifestData.spritesheets && this.manifestData.spritesheets.length > 0) {
        for (const sprite of this.manifestData.spritesheets) {
          if (sprite.key && sprite.path) {
            console.log(`[PreloadScene] Queuing spritesheet: ${sprite.key} (${sprite.path})`);
            this.load.spritesheet(sprite.key, sprite.path, {
              frameWidth: sprite.frameWidth,
              frameHeight: sprite.frameHeight
            });
            hasAssetsToLoad = true;
          }
        }
      }

      if (this.manifestData.audio && this.manifestData.audio.length > 0) {
        for (const track of this.manifestData.audio) {
          if (track.key && track.path) {
            console.log(`[PreloadScene] Queuing audio [${track.type}]: ${track.key} (${track.path})`);
            this.load.audio(track.key, track.path);
            hasAssetsToLoad = true;
          }
        }
      }
    } else {
      console.warn('[PreloadScene] Asset manifest missing; proceeding with dynamic canvas assets.');
    }

    const transitionToGame = () => {
      this.scene.start('BarScene');
      this.scene.launch('HUDOverlayScene');
    };

    if (hasAssetsToLoad) {
      this.load.once('complete', () => {
        console.log('[PreloadScene] Manifest assets loader pass complete.');
        transitionToGame();
      });
      this.load.start();
    } else {
      transitionToGame();
    }
  }
}
