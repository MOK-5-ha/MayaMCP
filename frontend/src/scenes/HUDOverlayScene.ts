import Phaser from 'phaser';
import { SoundtrackPlayer } from '../components/SoundtrackPlayer';
import type { SoundManager } from '../utils/SoundManager';

interface HUDData {
  soundManager: SoundManager;
}

export class HUDOverlayScene extends Phaser.Scene {
  private dialogueBoxText: Phaser.GameObjects.Text | null = null;

  constructor() {
    super('HUDOverlayScene');
  }

  create(data: HUDData): void {
    const { width, height } = this.scale;
    const dialogueX = 224;
    const dialogueWidth = width - dialogueX - 16;

    const dialogBg = this.add.graphics();
    dialogBg.fillStyle(0x0e0d1a, 0.95);
    dialogBg.fillRect(dialogueX, height - 140, dialogueWidth, 120);
    dialogBg.lineStyle(2, 0x00f0ff, 1);
    dialogBg.strokeRect(dialogueX, height - 140, dialogueWidth, 120);

    const nameTagBg = this.add.graphics();
    nameTagBg.fillStyle(0x00f0ff, 1);
    nameTagBg.fillRect(dialogueX + 10, height - 155, 120, 20);

    this.add.text(dialogueX + 15, height - 152, 'MAYA', {
      font: 'bold 12px Courier, monospace',
      color: '#000000'
    });

    this.dialogueBoxText = this.add.text(
      dialogueX + 15,
      height - 125,
      'Welcome to the bar, stranger. What can I get started for you today?',
      {
        font: '13px Courier, monospace',
        color: '#e0e0ff',
        wordWrap: { width: dialogueWidth - 30 }
      }
    );

    const topHudBg = this.add.graphics();
    topHudBg.fillStyle(0x090812, 0.9);
    topHudBg.fillRect(0, 0, width, 32);
    topHudBg.lineStyle(2, 0x1f1d36, 1);
    topHudBg.lineBetween(0, 32, width, 32);

    this.add.text(16, 8, 'SYSTEM // MAYAMCP v2.0.0 (PHASER 4 ENGINE)', {
      font: 'bold 11px Courier, monospace',
      color: '#00f0ff'
    });

    this.add.text(width - 16, 8, 'ONLINE [VERTEX AI]', {
      font: 'bold 11px Courier, monospace',
      color: '#00ff88'
    }).setOrigin(1, 0);

    new SoundtrackPlayer(this, data.soundManager, 16, 280);
  }

  public setDialogueText(text: string): void {
    if (this.dialogueBoxText) {
      this.dialogueBoxText.setText(text);
    }
  }
}
