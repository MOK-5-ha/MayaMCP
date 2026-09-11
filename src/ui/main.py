"""Main UI module re-exporting launcher and chips components.

Fulfills Task 10.1 specification referencing src/ui/main.py.
"""

from .chips import (
    ACTION_CHIP_STYLE,
    ACTION_ICONS,
    CHIP_CSS,
    CHIP_FOCUS_STYLE,
    CHIP_HOVER_STYLE,
    DIALOGUE_CHIP_STYLE,
    create_chip_row,
    get_chip_aria_label,
    handle_chip_click,
    register_chip_handlers,
    update_chips,
)
from .launcher import create_avatar_with_overlay, launch_bartender_interface

__all__ = [
    "launch_bartender_interface",
    "create_avatar_with_overlay",
    "create_chip_row",
    "update_chips",
    "handle_chip_click",
    "register_chip_handlers",
    "get_chip_aria_label",
    "DIALOGUE_CHIP_STYLE",
    "ACTION_CHIP_STYLE",
    "CHIP_HOVER_STYLE",
    "CHIP_FOCUS_STYLE",
    "ACTION_ICONS",
    "CHIP_CSS",
]
