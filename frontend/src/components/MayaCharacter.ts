import Phaser from 'phaser';
import { MouthFlapController } from '../utils/MouthFlapController';

export type CharacterExpression = 'maya_idle' | 'maya_smirk' | 'maya_surprised' | 'maya_happy';

export class MayaCharacter extends Phaser.GameObjects.Container {
  private mouthController: MouthFlapController;
  private eyeGraphics: Phaser.GameObjects.Graphics;
  private currentExpression: CharacterExpression = 'maya_idle';
  private blinkTimer: Phaser.Time.TimerEvent | null = null;
  private isBlinking: boolean = false;

  constructor(scene: Phaser.Scene, x: number, y: number) {
    super(scene, x, y);

    // Layer 1: Base Head & Hair Graphic
    const headGraphic = scene.add.graphics();
    // Cyberpunk Hair / Head Silhouette
    headGraphic.fillStyle(0x1a162b, 1);
    headGraphic.fillRoundedRect(-48, -60, 96, 110, 16);
    headGraphic.lineStyle(2, 0x00f0ff, 1);
    headGraphic.strokeRoundedRect(-48, -60, 96, 110, 16);

    // Face Skin Surface
    headGraphic.fillStyle(0x2d2745, 1);
    headGraphic.fillRoundedRect(-36, -40, 72, 80, 12);

    // Cyberpunk Visor / Glasses accent line
    headGraphic.fillStyle(0xff007f, 0.4);
    headGraphic.fillRect(-32, -24, 64, 4);

    this.add(headGraphic);

    // Layer 2: Eyes Graphic Layer
    this.eyeGraphics = scene.add.graphics();
    this.add(this.eyeGraphics);
    this.renderEyes('maya_idle');

    // Layer 3: Viseme Mouth Flap Layer
    this.mouthController = new MouthFlapController(scene, 0, 20, this);

    scene.add.existing(this);

    // Start auto-blinking timer
    this.startBlinkLoop(scene);
  }

  public renderEyes(expression: CharacterExpression): void {
    this.currentExpression = expression;
    this.eyeGraphics.clear();

    if (this.isBlinking) {
      // Blinking Eyes (Horizontal Lines)
      this.eyeGraphics.fillStyle(0x00f0ff, 1);
      this.eyeGraphics.fillRect(-20, -12, 12, 2);
      this.eyeGraphics.fillRect(8, -12, 12, 2);
      return;
    }

    switch (expression) {
      case 'maya_surprised':
        // Wide circle eyes
        this.eyeGraphics.fillStyle(0x00f0ff, 1);
        this.eyeGraphics.fillCircle(-14, -14, 7);
        this.eyeGraphics.fillCircle(14, -14, 7);
        this.eyeGraphics.fillStyle(0x000000, 1);
        this.eyeGraphics.fillCircle(-14, -14, 3);
        this.eyeGraphics.fillCircle(14, -14, 3);
        break;

      case 'maya_smirk':
        // Slanted smirking eyes
        this.eyeGraphics.fillStyle(0x00f0ff, 1);
        this.eyeGraphics.fillRect(-20, -14, 12, 4);
        this.eyeGraphics.fillRect(8, -16, 12, 5);
        break;

      case 'maya_happy':
        // Upward arc happy eyes
        this.eyeGraphics.lineStyle(2, 0x00f0ff, 1);
        this.eyeGraphics.beginPath();
        this.eyeGraphics.arc(-14, -10, 6, Math.PI, 0, false);
        this.eyeGraphics.strokePath();
        this.eyeGraphics.beginPath();
        this.eyeGraphics.arc(14, -10, 6, Math.PI, 0, false);
        this.eyeGraphics.strokePath();
        break;

      case 'maya_idle':
      default:
        // Standard Cyberpunk Pixel Eyes
        this.eyeGraphics.fillStyle(0x00f0ff, 1);
        this.eyeGraphics.fillRect(-20, -16, 12, 6);
        this.eyeGraphics.fillRect(8, -16, 12, 6);
        this.eyeGraphics.fillStyle(0xffffff, 1);
        this.eyeGraphics.fillRect(-18, -15, 4, 3);
        this.eyeGraphics.fillRect(10, -15, 4, 3);
        break;
    }
  }

  private startBlinkLoop(scene: Phaser.Scene): void {
    this.blinkTimer = scene.time.addEvent({
      delay: 3500,
      loop: true,
      callback: () => {
        this.isBlinking = true;
        this.renderEyes(this.currentExpression);
        scene.time.delayedCall(150, () => {
          this.isBlinking = false;
          this.renderEyes(this.currentExpression);
        });
      }
    });
  }

  public setExpression(expression: CharacterExpression): void {
    this.renderEyes(expression);
  }

  public getMouthController(): MouthFlapController {
    return this.mouthController;
  }

  public destroy(fromScene?: boolean): void {
    if (this.blinkTimer) {
      this.blinkTimer.destroy();
      this.blinkTimer = null;
    }
    super.destroy(fromScene);
  }
}
