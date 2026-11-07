import Phaser from 'phaser';
import { ChipBar } from '../components/ChipBar';
import { SoundtrackPlayer } from '../components/SoundtrackPlayer';
import type { ChatController } from '../utils/ChatController';
import type { SoundManager } from '../utils/SoundManager';

interface HUDData {
  soundManager: SoundManager;
  chat: ChatController;
}

export class HUDOverlayScene extends Phaser.Scene {
  private dialogueText: HTMLElement | null = null;
  private chatAccumulated = '';
  private chipBar: ChipBar | null = null;

  constructor() {
    super('HUDOverlayScene');
  }

  create(data: HUDData): void {
    const { width, height } = this.scale;
    const dialogueX = 224;
    const dialogueWidth = width - dialogueX - 16;

    const dialogBg = this.add.graphics();
    dialogBg.fillStyle(0x0e0d1a, 0.95);
    dialogBg.fillRect(dialogueX, height - 165, dialogueWidth, 120);
    dialogBg.lineStyle(2, 0x00f0ff, 1);
    dialogBg.strokeRect(dialogueX, height - 165, dialogueWidth, 120);

    const nameTagBg = this.add.graphics();
    nameTagBg.fillStyle(0x00f0ff, 1);
    nameTagBg.fillRect(dialogueX + 10, height - 185, 120, 20);

    this.add.text(dialogueX + 15, height - 182, 'MAYA', {
      font: 'bold 12px Courier, monospace',
      color: '#000000'
    });

    const dialogueEl = this.add.dom(dialogueX + 15, height - 155).createFromHTML(`
      <div id="dialogue-text" class="dialogue-text" role="log" aria-label="Maya's reply" tabindex="0"></div>
    `).setOrigin(0, 0);
    this.dialogueText = dialogueEl.node.querySelector<HTMLElement>('#dialogue-text')!;
    this.dialogueText.style.width = `${dialogueWidth - 30}px`;
    this.setDialogueText('Welcome to the bar, stranger. What can I get started for you today?');

    const chat = data.chat;
    chat.bindHUD({
      onSend: () => {
        this.chatAccumulated = '';
        this.setDialogueText('…');
      },
      onDelta: (delta) => this.appendDialogueText(delta),
      onComplete: (full) => {
        this.setDialogueText(full);
        this.chipBar?.startPolling();
      },
      onError: (message) => this.setDialogueText(message),
    });

    this.chipBar = new ChipBar(this, dialogueX, height - 310, dialogueWidth, {
      onChipClick: (text) => chat.send(text),
    });

    const chatInputEl = this.add.dom(dialogueX, height - 44).createFromHTML(`
      <form id="chat-input-row" class="chat-input-row">
        <input id="chat-input" type="text" placeholder="Order a drink or just talk to Maya…" aria-label="Chat message" maxlength="500" autocomplete="off" />
        <button id="chat-send" type="submit" aria-label="Send message">SEND</button>
      </form>
    `).setOrigin(0, 0);
    const chatForm = chatInputEl.node.querySelector<HTMLFormElement>('#chat-input-row')!;
    const chatInput = chatInputEl.node.querySelector<HTMLInputElement>('#chat-input')!;
    chatForm.addEventListener('submit', (event) => {
      event.preventDefault();
      if (chat.send(chatInput.value)) {
        chatInput.value = '';
      }
    });

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
    if (this.dialogueText) {
      this.dialogueText.textContent = text;
      this.dialogueText.scrollTop = this.dialogueText.scrollHeight;
    }
  }

  private appendDialogueText(delta: string): void {
    if (this.dialogueText) {
      this.chatAccumulated += delta;
      this.setDialogueText(this.chatAccumulated);
    }
  }
}
