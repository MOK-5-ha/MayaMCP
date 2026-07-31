import Phaser from 'phaser';

export class HUDOverlayScene extends Phaser.Scene {
  private dialogueBoxText: Phaser.GameObjects.Text | null = null;

  constructor() {
    super('HUDOverlayScene');
  }

  create(): void {
    const { width, height } = this.scale;

    // Dialogue Window Box (VA-11 Hall-A Retro Styling)
    const dialogBg = this.add.graphics();
    dialogBg.fillStyle(0x0e0d1a, 0.95);
    dialogBg.fillRect(20, height - 140, width - 40, 120);
    dialogBg.lineStyle(2, 0x00f0ff, 1);
    dialogBg.strokeRect(20, height - 140, width - 40, 120);

    // Title Tag
    const nameTagBg = this.add.graphics();
    nameTagBg.fillStyle(0x00f0ff, 1);
    nameTagBg.fillRect(30, height - 155, 120, 20);

    this.add.text(35, height - 152, 'MAYA', {
      font: 'bold 12px Courier, monospace',
      color: '#000000'
    });

    // Dialogue Text Output
    this.dialogueBoxText = this.add.text(35, height - 125, 'Welcome to the bar, stranger. What can I get started for you today?', {
      font: '13px Courier, monospace',
      color: '#e0e0ff',
      wordWrap: { width: width - 70 }
    });

    // Top Header Status HUD Bar
    const topHudBg = this.add.graphics();
    topHudBg.fillStyle(0x090812, 0.9);
    topHudBg.fillRect(0, 0, width, 32);
    topHudBg.lineStyle(1, 0x1f1d36, 1);
    topHudBg.lineBetween(0, 32, width, 32);

    this.add.text(16, 8, 'SYSTEM // MAYAMCP v2.0.0 (PHASER 3 ENGINE)', {
      font: 'bold 11px Courier, monospace',
      color: '#00f0ff'
    });

    this.add.text(width - 16, 8, 'ONLINE [VERTEX AI]', {
      font: 'bold 11px Courier, monospace',
      color: '#00ff88'
    }).setOrigin(1, 0);

    console.log('[HUDOverlayScene] Cyberpunk dialogue HUD overlay rendered');
  }

  public setDialogueText(text: string): void {
    if (this.dialogueBoxText) {
      this.dialogueBoxText.setText(text);
    }
  }
}
