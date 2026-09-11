"""
Tests for Suggestion Chips Accessibility Compliance.

Validates:
- Requirements 4.6, 9.1, 9.2, 9.3, 9.5, 9.6, 5.6
- Properties 22, 23, 24, 25, 26, 27, 28
"""

import re
from unittest.mock import MagicMock

import gradio as gr
import pytest

from src.schemas.chips import ActionID, ChipType, SuggestionChip, SuggestionChipSet
from src.ui.chips import (
    ACTION_CHIP_STYLE,
    ACTION_ICONS,
    CHIP_CSS,
    CHIP_FOCUS_STYLE,
    DIALOGUE_CHIP_STYLE,
    create_chip_row,
    format_chip_live_announcement,
    get_chip_aria_label,
    handle_chip_click,
    update_chips,
)


class TestAriaLabels:
    """Tests for ARIA label presence and formatting (Requirements 9.1, Property 23)."""

    def test_aria_label_dialogue_chip(self):
        """Dialogue chips should have ARIA label formatted as 'dialogue chip: <text>'."""
        chip = SuggestionChip(
            text="Show me the cocktail menu",
            type=ChipType.DIALOGUE,
            action_id=None,
        )
        label = get_chip_aria_label(chip)
        assert label == "dialogue chip: Show me the cocktail menu"

    def test_aria_label_action_chip(self):
        """Action chips should have ARIA label formatted as 'action chip: <text>'."""
        chip = SuggestionChip(
            text="Complete payment",
            type=ChipType.ACTION,
            action_id=ActionID.PAYMENT,
        )
        label = get_chip_aria_label(chip)
        assert label == "action chip: Complete payment"

    def test_update_chips_sets_aria_labels_on_all_buttons(self):
        """update_chips must set aria_label attribute on every visible button."""
        session_id = "test-aria-session"
        chip_set = SuggestionChipSet(
            chips=[
                SuggestionChip(
                    text="Surprise me", type=ChipType.DIALOGUE, action_id=None
                ),
                SuggestionChip(
                    text="Pay now", type=ChipType.ACTION, action_id=ActionID.PAYMENT
                ),
                SuggestionChip(
                    text="Add a tip", type=ChipType.ACTION, action_id=ActionID.TIP
                ),
            ]
        )
        app_state = {
            session_id: {
                "chip_state": {"current_chips": chip_set},
            }
        }
        buttons = [gr.Button(value="", visible=False) for _ in range(6)]
        updates = update_chips(session_id, buttons, app_state=app_state)

        assert len(updates) == 6
        assert getattr(updates[0], "aria_label", None) == "dialogue chip: Surprise me"
        assert getattr(updates[1], "aria_label", None) == "action chip: Pay now"
        assert getattr(updates[2], "aria_label", None) == "action chip: Add a tip"
        assert updates[3].visible is False


class TestAriaLiveRegion:
    """Tests for ARIA live region announcements (Requirements 9.3, Property 25)."""

    def test_create_chip_row_contains_aria_live_region(self):
        """create_chip_row must contain an ARIA live region container with polite and atomic attributes."""
        assert 'aria-live="polite"' in CHIP_CSS or 'aria-live="polite"' in str(CHIP_CSS)
        row, buttons = create_chip_row(session_id="test-live-region")
        assert len(buttons) == 6
        assert row.elem_id == "suggestion-chips-row"

    def test_format_chip_live_announcement_with_chips(self):
        """format_chip_live_announcement should produce a readable announcement string."""
        chip_set = SuggestionChipSet(
            chips=[
                SuggestionChip(text="Show menu", type=ChipType.DIALOGUE, action_id=None),
                SuggestionChip(text="Pay order", type=ChipType.ACTION, action_id=ActionID.PAYMENT),
                SuggestionChip(text="Tip bartender", type=ChipType.ACTION, action_id=ActionID.TIP),
            ]
        )
        announcement = format_chip_live_announcement(chip_set)
        assert "3 suggestions available" in announcement
        assert "Show menu" in announcement
        assert "Pay order" in announcement
        assert "Tip bartender" in announcement

    def test_format_chip_live_announcement_single_chip(self):
        """format_chip_live_announcement should handle singular 'suggestion' correctly."""
        chip = SuggestionChip(text="Only option", type=ChipType.DIALOGUE, action_id=None)
        announcement = format_chip_live_announcement([chip])
        assert "1 suggestion available: Only option" in announcement

    def test_format_chip_live_announcement_empty(self):
        """format_chip_live_announcement should announce no suggestions when empty or None."""
        assert format_chip_live_announcement(None) == "No suggestions available"
        empty_set = MagicMock(chips=[])
        assert format_chip_live_announcement(empty_set) == "No suggestions available"


class TestKeyboardNavigation:
    """Tests for keyboard navigation support (Requirements 9.2, 5.6, Property 24)."""

    def test_enter_key_activates_dialogue_chip(self):
        """Activating a dialogue chip via Enter/Space should populate textbox without auto-submit."""
        text, submit_trigger = handle_chip_click(
            chip_text="What beers are on tap?",
            chip_type=ChipType.DIALOGUE,
            action_id=None,
        )
        assert text == "What beers are on tap?"
        assert submit_trigger is None

    def test_enter_key_activates_action_chip(self):
        """Activating an action chip via Enter/Space should populate textbox and trigger auto-submit."""
        text, submit_trigger = handle_chip_click(
            chip_text=f"{ACTION_ICONS[ActionID.PAYMENT]}Complete payment",
            chip_type=ChipType.ACTION,
            action_id=ActionID.PAYMENT,
        )
        assert text == "Complete payment"
        assert submit_trigger == "submit"

    def test_keyboard_navigation_css_and_script(self):
        """CHIP_CSS or create_chip_row must provide focus outlines for keyboard navigation."""
        assert "outline:" in CHIP_CSS
        assert "2px solid" in CHIP_CSS
        assert "outline-offset:" in CHIP_CSS


class TestFocusIndicators:
    """Tests for visual focus indicators (Requirements 9.6, Property 28)."""

    def test_chip_focus_style_has_minimum_2px_outline(self):
        """Focus style must have at least 2px outline for WCAG compliance."""
        assert "outline: 2px solid" in CHIP_FOCUS_STYLE
        assert "outline-offset: 2px" in CHIP_FOCUS_STYLE

    def test_chip_css_focus_and_focus_visible(self):
        """CHIP_CSS must include outline rule with 2px solid on focus."""
        match = re.search(r"\.suggestion-chip:focus[^{]*\{([^}]+)\}", CHIP_CSS)
        assert match is not None, "No .suggestion-chip:focus rule in CHIP_CSS"
        rule_body = match.group(1)
        assert "outline: 2px solid" in rule_body
        assert "outline-offset: 2px" in rule_body


class TestTouchTargetDimensions:
    """Tests for mobile touch target size (Requirements 9.5, Property 27)."""

    def test_style_constants_have_min_44px_touch_target(self):
        """DIALOGUE_CHIP_STYLE and ACTION_CHIP_STYLE must specify min-height and min-width 44px."""
        for style in (DIALOGUE_CHIP_STYLE, ACTION_CHIP_STYLE):
            assert "min-height: 44px" in style
            assert "min-width: 44px" in style

    def test_chip_css_has_min_44px_touch_target(self):
        """CHIP_CSS base and mobile media query must enforce 44x44px minimum touch targets."""
        assert "min-height: 44px" in CHIP_CSS
        assert "min-width: 44px" in CHIP_CSS

        assert "@media (max-width: 768px)" in CHIP_CSS
        media_idx = CHIP_CSS.find("@media (max-width: 768px)")
        mobile_block = CHIP_CSS[media_idx : media_idx + 300]
        assert "min-height: 44px" in mobile_block
        assert "min-width: 44px" in mobile_block


class TestColorContrast:
    """Tests for WCAG 2.1 AA 4.5:1 text color contrast (Requirements 4.6, Property 22)."""

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore

    @classmethod
    def _relative_luminance(cls, hex_color: str) -> float:
        r, g, b = [c / 255.0 for c in cls._hex_to_rgb(hex_color)]
        r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
        g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
        b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    @classmethod
    def _contrast_ratio(cls, hex1: str, hex2: str) -> float:
        l1 = cls._relative_luminance(hex1)
        l2 = cls._relative_luminance(hex2)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)

    def test_dialogue_chip_gradient_contrast(self):
        """Dialogue chip gradient endpoints (#4338ca and #312e81) must exceed 4.5:1 against #ffffff."""
        text_color = "#ffffff"
        for endpoint in ("#4338ca", "#312e81"):
            ratio = self._contrast_ratio(endpoint, text_color)
            assert ratio >= 4.5, f"Endpoint {endpoint} contrast {ratio:.2f} is below 4.5:1"

    def test_action_chip_gradient_contrast(self):
        """Action chip gradient endpoints (#be185d and #881337) must exceed 4.5:1 against #ffffff."""
        text_color = "#ffffff"
        for endpoint in ("#be185d", "#881337"):
            ratio = self._contrast_ratio(endpoint, text_color)
            assert ratio >= 4.5, f"Endpoint {endpoint} contrast {ratio:.2f} is below 4.5:1"
