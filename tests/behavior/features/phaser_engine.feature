Feature: Phaser 3 Pixel Art Game Engine & Viseme HUD
  As a bar patron playing MayaMCP in the browser
  I want a responsive 2D pixel-art interface with mouth-flap animations, cocktail mixing, and crypto payments
  So that I have an immersive Cyberpunk bartending experience

  Scenario: Phaser 3 Canvas Configuration initializes with Nearest-Neighbor Pixel Art
    Given the Phaser 3 game canvas initializes in the browser
    When the game config and scale manager are loaded
    Then game.config.pixelArt is true
    And the scale mode is configured to FIT with nearest-neighbor rendering

  Scenario: Asset Manifest loader parses spritesheets and audio tracks
    Given a valid asset_manifest.json containing spritesheet and audio definitions
    When PreloadScene processes the manifest data
    Then all declared spritesheets and audio tracks are queued into Phaser caches
    And fallback placeholders are assigned for any missing media files

  Scenario: SSE chat stream events trigger viseme mouth-flap animation state
    Given Maya receives a streamed chat response with text token "Hello"
    When the backend derives viseme tag "mouth_talk_a" from the token
    Then MouthFlapController switches mouth graphic to "mouth_talk_a"
    And resets to "mouth_closed" when the speech stream completes

  Scenario: Interactive Cocktail Mixer HUD generates drink order payload
    Given the DrinkMixerHUD overlay is active on the screen
    When the customer selects ingredients "Adelhyde" and "Brantini" and clicks SERVE
    Then a drink order payload "Adelhyde & Brantini" is formatted for the MayaMCP chat API

  Scenario: Crypto Payment Modal displays Base Sepolia USDC transfer details
    Given a pending drink tab requires payment
    When the customer opens the PaymentModal overlay
    Then the Base Sepolia USDC wallet address and QR code placeholder are displayed
    And the modal listens for background transaction confirmation
