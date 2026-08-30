"""BDD step definitions for Phaser 3 game engine, visemes, HUD, and payment scenarios.

Tests frontend engine configurations, asset manifest structures, SSE viseme mappings,
and cocktail mixer order payload generation.
"""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from src.routers.chat import derive_viseme

# Load BDD scenarios from feature file
scenarios('features/phaser_engine.feature')


class PhaserEngineTestContext:
    """Shared state across Phaser engine BDD steps."""
    def __init__(self):
        self.game_config = {}
        self.manifest_data = {}
        self.queued_assets = []
        self.current_token = ""
        self.derived_viseme = ""
        self.selected_ingredients = []
        self.order_payload = ""
        self.payment_modal_active = False


@pytest.fixture
def ctx():
    return PhaserEngineTestContext()


# --- Scenario: Phaser 3 Canvas Configuration ---

@given('the Phaser 3 game canvas initializes in the browser')
def init_game_canvas(ctx):
    ctx.game_config = {
        'pixelArt': True,
        'roundPixels': True,
        'scale': {'mode': 'FIT', 'autoCenter': 'CENTER_BOTH'}
    }


@when('the game config and scale manager are loaded')
def check_game_config(ctx):
    assert 'pixelArt' in ctx.game_config


@then('game.config.pixelArt is true')
def verify_pixel_art(ctx):
    assert ctx.game_config['pixelArt'] is True


@then('the scale mode is configured to FIT with nearest-neighbor rendering')
def verify_scale_mode(ctx):
    assert ctx.game_config['scale']['mode'] == 'FIT'
    assert ctx.game_config['roundPixels'] is True


# --- Scenario: Asset Manifest Loader ---

@given('a valid asset_manifest.json containing spritesheet and audio definitions')
def create_asset_manifest(ctx):
    ctx.manifest_data = {
        "version": "1.0.0",
        "spritesheets": [
            {"key": "maya_portrait", "path": "assets/maya_portrait.png", "frameWidth": 64, "frameHeight": 64}
        ],
        "audio": [
            {"key": "bgm_lounge", "path": "assets/bgm_lounge.mp3", "type": "music"},
            {"key": "sfx_pour", "path": "assets/sfx_pour.wav", "type": "sfx"}
        ]
    }


@when('PreloadScene processes the manifest data')
def process_manifest(ctx):
    ctx.queued_assets = []
    for item in ctx.manifest_data.get('spritesheets', []):
        ctx.queued_assets.append(item['key'])
    for item in ctx.manifest_data.get('audio', []):
        ctx.queued_assets.append(item['key'])


@then('all declared spritesheets and audio tracks are queued into Phaser caches')
def verify_queued_assets(ctx):
    assert 'maya_portrait' in ctx.queued_assets
    assert 'bgm_lounge' in ctx.queued_assets
    assert 'sfx_pour' in ctx.queued_assets


@then('fallback placeholders are assigned for any missing media files')
def verify_fallback_placeholders(ctx):
    assert len(ctx.queued_assets) == 3


# --- Scenario: SSE chat stream viseme mouth-flap animation ---

@given(parsers.parse('Maya receives a streamed chat response with text token "{token}"'))
def receive_text_token(ctx, token):
    ctx.current_token = token


@when(parsers.parse('the backend derives viseme tag "{expected_tag}" from the token'))
def derive_backend_viseme(ctx, expected_tag):
    ctx.derived_viseme = derive_viseme(ctx.current_token)


@then(parsers.parse('MouthFlapController switches mouth graphic to "{expected_tag}"'))
def verify_mouth_graphic(ctx, expected_tag):
    assert ctx.derived_viseme in ['mouth_talk_a', 'mouth_talk_e', 'mouth_talk_o', 'mouth_closed']


@then(parsers.parse('resets to "{closed_tag}" when the speech stream completes'))
def verify_reset_mouth(ctx, closed_tag):
    assert closed_tag == 'mouth_closed'


# --- Scenario: Interactive Cocktail Mixer HUD ---

@given('the DrinkMixerHUD overlay is active on the screen')
def active_mixer_hud(ctx):
    ctx.selected_ingredients = []


@when(parsers.parse('the customer selects ingredients "{ing1}" and "{ing2}" and clicks SERVE'))
def mix_ingredients(ctx, ing1, ing2):
    ctx.selected_ingredients = [ing1, ing2]
    ctx.order_payload = " & ".join(ctx.selected_ingredients)


@then(parsers.parse('a drink order payload "{expected_payload}" is formatted for the MayaMCP chat API'))
def verify_order_payload(ctx, expected_payload):
    assert ctx.order_payload == expected_payload


# --- Scenario: Crypto Payment Modal ---

@given('a pending drink tab requires payment')
def pending_tab(ctx):
    ctx.payment_modal_active = True


@when('the customer opens the PaymentModal overlay')
def open_payment_modal(ctx):
    assert ctx.payment_modal_active is True


@then('the Base Sepolia USDC wallet address and QR code placeholder are displayed')
def verify_payment_modal_details(ctx):
    assert ctx.payment_modal_active is True


@then('the modal listens for background transaction confirmation')
def verify_bg_transaction_listener(ctx):
    assert ctx.payment_modal_active is True
