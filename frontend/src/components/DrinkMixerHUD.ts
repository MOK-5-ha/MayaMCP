import Phaser from 'phaser';

export class DrinkMixerHUD extends Phaser.GameObjects.Container {
  private selectedIngredients: string[] = [];
  private ingredientText: Phaser.GameObjects.Text;

  constructor(scene: Phaser.Scene, x: number, y: number, onServe: (drink: string) => void) {
    super(scene, x, y);

    // Background HUD Panel
    const panelBg = scene.add.graphics();
    panelBg.fillStyle(0x0e0d1a, 0.95);
    panelBg.fillRoundedRect(-140, -80, 280, 160, 8);
    panelBg.lineStyle(2, 0xff007f, 1);
    panelBg.strokeRoundedRect(-140, -80, 280, 160, 8);
    this.add(panelBg);

    // Title Header
    const headerText = scene.add.text(0, -68, 'CYBERPUNK COCKTAIL MIXER', {
      font: 'bold 11px Courier, monospace',
      color: '#ff007f'
    }).setOrigin(0.5, 0.5);
    this.add(headerText);

    // Selected Ingredients Display
    this.ingredientText = scene.add.text(0, -45, 'MIX: [Empty]', {
      font: '10px Courier, monospace',
      color: '#00f0ff'
    }).setOrigin(0.5, 0.5);
    this.add(this.ingredientText);

    // Ingredient Buttons Grid (VA-11 Hall-A drinks)
    const ingredients = ['Adelhyde', 'Brantini', 'Kadelic', 'Colokey', 'Flanergide'];
    ingredients.forEach((name, idx) => {
      const btnX = -100 + (idx % 3) * 68;
      const btnY = -20 + Math.floor(idx / 3) * 32;

      const btnBg = scene.add.graphics();
      btnBg.fillStyle(0x1a162b, 1);
      btnBg.fillRect(btnX - 30, btnY - 10, 60, 20);
      btnBg.lineStyle(1, 0x00f0ff, 1);
      btnBg.strokeRect(btnX - 30, btnY - 10, 60, 20);

      const label = scene.add.text(btnX, btnY, name.substring(0, 7), {
        font: '9px Courier, monospace',
        color: '#e0e0ff'
      }).setOrigin(0.5, 0.5);

      const hitZone = scene.add.zone(btnX, btnY, 60, 20).setInteractive();
      hitZone.on('pointerdown', () => {
        if (this.selectedIngredients.length < 5) {
          this.selectedIngredients.push(name);
          this.updateMixDisplay();
        }
      });

      this.add([btnBg, label, hitZone]);
    });

    // Action Buttons: Clear & Serve
    const clearBtn = scene.add.text(-60, 48, '[CLEAR]', {
      font: 'bold 11px Courier, monospace',
      color: '#ff0055'
    }).setOrigin(0.5, 0.5).setInteractive();

    clearBtn.on('pointerdown', () => {
      this.selectedIngredients = [];
      this.updateMixDisplay();
    });

    const serveBtn = scene.add.text(60, 48, '[SERVE DRINK]', {
      font: 'bold 11px Courier, monospace',
      color: '#00ff88'
    }).setOrigin(0.5, 0.5).setInteractive();

    serveBtn.on('pointerdown', () => {
      const drinkName = this.selectedIngredients.length > 0
        ? this.selectedIngredients.join(' & ')
        : 'Cyberpunk Bartender Special';
      onServe(drinkName);
      this.selectedIngredients = [];
      this.updateMixDisplay();
    });

    this.add([clearBtn, serveBtn]);
    scene.add.existing(this);
  }

  private updateMixDisplay(): void {
    if (this.selectedIngredients.length === 0) {
      this.ingredientText.setText('MIX: [Empty]');
    } else {
      this.ingredientText.setText(`MIX: ${this.selectedIngredients.join(', ')}`);
    }
  }
}
