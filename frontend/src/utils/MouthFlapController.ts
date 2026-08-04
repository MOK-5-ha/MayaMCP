import Phaser from 'phaser';

export type VisemeKey = 'mouth_closed' | 'mouth_talk_a' | 'mouth_talk_e' | 'mouth_talk_o';

export class MouthFlapController {
  private mouthGraphic: Phaser.GameObjects.Graphics;
  private currentViseme: VisemeKey = 'mouth_closed';
  private flapTimer: Phaser.Time.TimerEvent | null = null;
  private isTalking: boolean = false;

  constructor(scene: Phaser.Scene, x: number, y: number, container: Phaser.GameObjects.Container) {
    this.mouthGraphic = scene.add.graphics();
    this.mouthGraphic.setPosition(x, y);
    container.add(this.mouthGraphic);
    this.renderViseme('mouth_closed');
  }

  public renderViseme(viseme: VisemeKey): void {
    this.currentViseme = viseme;
    this.mouthGraphic.clear();

    // Render retro pixel art mouth shapes
    switch (viseme) {
      case 'mouth_talk_a':
        // Wide open mouth
        this.mouthGraphic.fillStyle(0xff0055, 1);
        this.mouthGraphic.fillRect(-12, -4, 24, 10);
        this.mouthGraphic.lineStyle(1, 0x000000, 1);
        this.mouthGraphic.strokeRect(-12, -4, 24, 10);
        break;

      case 'mouth_talk_e':
        // Wide grin / teeth visible
        this.mouthGraphic.fillStyle(0xff0055, 1);
        this.mouthGraphic.fillRect(-14, -2, 28, 6);
        this.mouthGraphic.fillStyle(0xffffff, 1);
        this.mouthGraphic.fillRect(-10, -2, 20, 2);
        break;

      case 'mouth_talk_o':
        // Small circle mouth
        this.mouthGraphic.fillStyle(0xff0055, 1);
        this.mouthGraphic.fillRect(-6, -6, 12, 12);
        this.mouthGraphic.lineStyle(1, 0x000000, 1);
        this.mouthGraphic.strokeRect(-6, -6, 12, 12);
        break;

      case 'mouth_closed':
      default:
        // Closed line mouth
        this.mouthGraphic.fillStyle(0xff0055, 1);
        this.mouthGraphic.fillRect(-10, 0, 20, 3);
        break;
    }
  }

  public setVisemeFromBackend(viseme: string): void {
    if (viseme === 'mouth_talk_a' || viseme === 'mouth_talk_e' || viseme === 'mouth_talk_o' || viseme === 'mouth_closed') {
      this.renderViseme(viseme as VisemeKey);
    } else {
      this.renderViseme('mouth_talk_a');
    }
  }

  public startTalkingAnimation(scene: Phaser.Scene): void {
    if (this.isTalking) return;
    this.isTalking = true;

    const visemes: VisemeKey[] = ['mouth_talk_a', 'mouth_talk_e', 'mouth_talk_o'];
    let index = 0;

    this.flapTimer = scene.time.addEvent({
      delay: 150,
      loop: true,
      callback: () => {
        if (!this.isTalking) return;
        index = (index + 1) % visemes.length;
        this.renderViseme(visemes[index]);
      }
    });
  }

  public stopTalkingAnimation(): void {
    this.isTalking = false;
    if (this.flapTimer) {
      this.flapTimer.destroy();
      this.flapTimer = null;
    }
    this.renderViseme('mouth_closed');
  }

  public getViseme(): VisemeKey {
    return this.currentViseme;
  }

  public destroy(): void {
    this.stopTalkingAnimation();
    if (this.mouthGraphic) {
      this.mouthGraphic.destroy();
    }
  }
}
