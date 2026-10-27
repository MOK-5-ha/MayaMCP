import Phaser from 'phaser';
import {
  MANIFEST_REGISTRY_KEY,
  type AssetManifest
} from '../utils/assetManifest';

export class PreloadScene extends Phaser.Scene {
  private manifestData: AssetManifest | null = null;

  constructor() {
    super('PreloadScene');
  }

  preload(): void {
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
      console.warn(`[PreloadScene] Asset load failed: ${fileObj.key} (${fileObj.url})`);
    });

    this.load.json('asset_manifest', 'assets/manifest.json');
  }

  create(): void {
    this.manifestData = this.cache.json.get('asset_manifest') as AssetManifest | null;
    let hasAssetsToLoad = false;

    if (this.manifestData) {
      this.registry.set(MANIFEST_REGISTRY_KEY, this.manifestData);

      for (const sprite of this.manifestData.spritesheets ?? []) {
        if (sprite.key && sprite.path) {
          this.load.spritesheet(sprite.key, sprite.path, {
            frameWidth: sprite.frameWidth,
            frameHeight: sprite.frameHeight
          });
          hasAssetsToLoad = true;
        }
      }

      for (const image of this.manifestData.images ?? []) {
        if (image.key && image.path) {
          this.load.image(image.key, image.path);
          hasAssetsToLoad = true;
        }
      }

      for (const track of this.manifestData.audio ?? []) {
        if (track.key && track.path && !track.placeholder) {
          this.load.audio(track.key, track.path);
          hasAssetsToLoad = true;
        }
      }
    } else {
      console.warn('[PreloadScene] Asset manifest missing; using canvas fallbacks.');
    }

    const transitionToStart = () => this.scene.start('StartScene');

    if (hasAssetsToLoad) {
      this.load.once('complete', transitionToStart);
      this.load.start();
    } else {
      transitionToStart();
    }
  }
}
