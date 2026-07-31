import Phaser from 'phaser';

export class PaymentModal extends Phaser.GameObjects.Container {
  private statusText: Phaser.GameObjects.Text;

  constructor(scene: Phaser.Scene, x: number, y: number, onClose: () => void) {
    super(scene, x, y);

    // Modal Background Darkening Tint
    const backdrop = scene.add.graphics();
    backdrop.fillStyle(0x000000, 0.7);
    backdrop.fillRect(-x, -y, scene.scale.width, scene.scale.height);
    this.add(backdrop);

    // Modal Popup Card
    const modalBg = scene.add.graphics();
    modalBg.fillStyle(0x0c0b16, 0.98);
    modalBg.fillRoundedRect(-150, -100, 300, 200, 10);
    modalBg.lineStyle(2, 0x00f0ff, 1);
    modalBg.strokeRoundedRect(-150, -100, 300, 200, 10);
    this.add(modalBg);

    // Title Header
    const title = scene.add.text(0, -82, 'COINBASE CDP // BASE SEPOLIA PAYMENT', {
      font: 'bold 10px Courier, monospace',
      color: '#00f0ff'
    }).setOrigin(0.5, 0.5);
    this.add(title);

    // QR / Pixel Art Wallet Placeholder Box
    const qrBox = scene.add.graphics();
    qrBox.fillStyle(0x1a162b, 1);
    qrBox.fillRect(-45, -60, 90, 90);
    qrBox.lineStyle(1, 0xff007f, 1);
    qrBox.strokeRect(-45, -60, 90, 90);
    this.add(qrBox);

    const qrText = scene.add.text(0, -15, '[USDC QR]', {
      font: 'bold 11px Courier, monospace',
      color: '#ff007f'
    }).setOrigin(0.5, 0.5);
    this.add(qrText);

    // Status Message
    this.statusText = scene.add.text(0, 42, 'Awaiting Base Sepolia USDC transfer...', {
      font: '10px Courier, monospace',
      color: '#e0e0ff'
    }).setOrigin(0.5, 0.5);
    this.add(this.statusText);

    // Close Button
    const closeBtn = scene.add.text(0, 75, '[CLOSE MODAL]', {
      font: 'bold 11px Courier, monospace',
      color: '#ff0055'
    }).setOrigin(0.5, 0.5).setInteractive();

    closeBtn.on('pointerdown', () => {
      onClose();
      this.destroy();
    });

    this.add(closeBtn);
    scene.add.existing(this);
  }

  public setStatus(msg: string): void {
    this.statusText.setText(msg);
  }
}
