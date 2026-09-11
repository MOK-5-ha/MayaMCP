"""Visual regression and styling tests for suggestion chips UI components.

Validates Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 9.1, 9.4, 9.5, 9.6.
"""

import math
import re

import gradio as gr
import pytest

from src.schemas.chips import ActionID
from src.ui.chips import (
    ACTION_CHIP_STYLE,
    ACTION_ICONS,
    CHIP_CSS,
    CHIP_FOCUS_STYLE,
    CHIP_HOVER_STYLE,
    DIALOGUE_CHIP_STYLE,
    create_chip_row,
)


def _relative_luminance(hex_color: str) -> float:
    """Calculate relative luminance for a hex color string (#rrggbb)."""
    hex_color = hex_color.lstrip("#")
    r, g, b = [int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def _adjust(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r_adj, g_adj, b_adj = _adjust(r), _adjust(g), _adjust(b)
    return 0.2126 * r_adj + 0.7152 * g_adj + 0.0722 * b_adj


def _contrast_ratio(hex1: str, hex2: str) -> float:
    """Calculate WCAG contrast ratio between two hex colors."""
    lum1 = _relative_luminance(hex1)
    lum2 = _relative_luminance(hex2)
    l_bright = max(lum1, lum2)
    l_dark = min(lum1, lum2)
    return (l_bright + 0.05) / (l_dark + 0.05)


class TestChipStylingConstants:
    """Tests for chip styling constants, gradients, and icon mappings."""

    def test_dialogue_chip_style_properties(self):
        """Dialogue chips must use neutral gradient with rounded corners and 44x44px min sizing."""
        assert "linear-gradient" in DIALOGUE_CHIP_STYLE
        assert "#667eea" in DIALOGUE_CHIP_STYLE
        assert "#764ba2" in DIALOGUE_CHIP_STYLE
        assert "border-radius: 20px" in DIALOGUE_CHIP_STYLE
        assert "min-height: 44px" in DIALOGUE_CHIP_STYLE
        assert "min-width: 44px" in DIALOGUE_CHIP_STYLE

    def test_action_chip_style_properties(self):
        """Action chips must use accent gradient, bold weight, and 44x44px min sizing."""
        assert "linear-gradient" in ACTION_CHIP_STYLE
        assert "#f093fb" in ACTION_CHIP_STYLE
        assert "#f5576c" in ACTION_CHIP_STYLE
        assert "font-weight: 600" in ACTION_CHIP_STYLE
        assert "min-height: 44px" in ACTION_CHIP_STYLE
        assert "min-width: 44px" in ACTION_CHIP_STYLE

    def test_action_icons_mapping(self):
        """ACTION_ICONS dictionary must cover all ActionID enum members with non-empty emoji prefixes."""
        expected_ids = {
            ActionID.PAYMENT: "💳 ",
            ActionID.TIP: "💰 ",
            ActionID.MENU: "📋 ",
            ActionID.CANCEL: "❌ ",
            ActionID.ORDER_ANOTHER: "🍹 ",
        }
        for action_id, expected_prefix in expected_ids.items():
            assert action_id in ACTION_ICONS
            assert ACTION_ICONS[action_id] == expected_prefix
            # String access compatibility
            assert ACTION_ICONS.get(action_id.value) == expected_prefix

    def test_hover_and_focus_styles(self):
        """Chip hover and focus styles must provide clear interactive feedback."""
        assert "translateY(-2px)" in CHIP_HOVER_STYLE
        assert "outline: 2px solid" in CHIP_FOCUS_STYLE
        assert "outline-offset: 2px" in CHIP_FOCUS_STYLE

    def test_wcag_color_contrast(self):
        """Chip text must maintain adequate contrast against gradient background stops."""
        text_color = "#ffffff"
        # Primary dark endpoint of dialogue gradient (#764ba2) satisfies WCAG AA (>= 4.5:1)
        assert _contrast_ratio(text_color, "#764ba2") >= 4.5
        # Lighter endpoint (#667eea) satisfies graphical UI element contrast (>= 3.0:1)
        assert _contrast_ratio(text_color, "#667eea") >= 3.0
        # Action gradient dark endpoint (#f5576c) satisfies UI contrast (>= 3.0:1)
        assert _contrast_ratio(text_color, "#f5576c") >= 3.0


class TestChipCSSRules:
    """Tests for responsive and accessibility CSS definitions."""

    def test_chip_container_layout_css(self):
        """Container must support horizontal scrolling and flex layout."""
        assert ".chip-container" in CHIP_CSS
        assert "overflow-x: auto" in CHIP_CSS
        assert "scroll-behavior: smooth" in CHIP_CSS
        assert "display: flex" in CHIP_CSS

    def test_mobile_responsive_css(self):
        """Mobile media query must enforce 44x44px minimum touch targets."""
        assert "@media (max-width: 768px)" in CHIP_CSS
        assert "min-height: 44px" in CHIP_CSS
        assert "min-width: 44px" in CHIP_CSS

    def test_accessibility_high_contrast_mode(self):
        """High contrast media query must provide explicit 2px borders."""
        assert "@media (prefers-contrast: high)" in CHIP_CSS
        assert "border: 2px solid" in CHIP_CSS

    def test_accessibility_reduced_motion(self):
        """Reduced motion media query must disable transitions and transforms."""
        assert "@media (prefers-reduced-motion: reduce)" in CHIP_CSS
        assert "transition: none" in CHIP_CSS
        assert "transform: none" in CHIP_CSS

    def test_accessibility_focus_indicator(self):
        """Focus indicators must have at least 2px outline."""
        assert ".suggestion-chip:focus" in CHIP_CSS
        assert "outline: 2px solid" in CHIP_CSS

    def test_aria_live_region_css(self):
        """ARIA live region must be visually hidden for screen readers."""
        assert '.chip-updates[aria-live="polite"]' in CHIP_CSS
        assert "position: absolute" in CHIP_CSS


class TestCreateChipRow:
    """Tests for the create_chip_row helper function."""

    def test_create_chip_row_structure(self):
        """create_chip_row must return a hidden Row and 6 placeholder buttons."""
        row, buttons = create_chip_row(session_id="test_session")

        assert isinstance(row, gr.Row)
        assert row.elem_id == "suggestion-chips-row"
        assert "chip-container" in (row.elem_classes or [])
        assert row.visible is False

        assert len(buttons) == 6
        for i, btn in enumerate(buttons):
            assert isinstance(btn, gr.Button)
            assert btn.elem_id == f"chip-{i}"
            assert "suggestion-chip" in (btn.elem_classes or [])
            assert btn.visible is False
            assert btn.size == "sm"
