"""Gradio suggestion chip UI components, styling, and event handlers.

Validates Requirements 4.1-4.6, 5.1-5.6, 6.1-6.6, 9.1-9.6, 11.5-11.6.
"""

from collections.abc import MutableMapping
from typing import Any

import gradio as gr

from ..config.logging_config import get_logger
from ..schemas.chips import ActionID, ChipType, SuggestionChip
from ..utils.state_manager import get_session_state

logger = get_logger(__name__)

# Chip styling constants (WCAG 2.1 AA compliant, >= 4.5:1 text contrast against #ffffff)
DIALOGUE_CHIP_STYLE = """
    background: linear-gradient(135deg, #4338ca 0%, #312e81 100%);
    color: white;
    border: none;
    border-radius: 20px;
    padding: 10px 20px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
    min-height: 44px;
    min-width: 44px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
"""

ACTION_CHIP_STYLE = """
    background: linear-gradient(135deg, #be185d 0%, #881337 100%);
    color: white;
    border: none;
    border-radius: 20px;
    padding: 10px 20px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
    min-height: 44px;
    min-width: 44px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    font-weight: 600;
"""

CHIP_HOVER_STYLE = """
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
"""

CHIP_FOCUS_STYLE = """
    outline: 2px solid #4299e1;
    outline-offset: 2px;
"""


class ActionIconsDict(dict):
    """Dictionary supporting both ActionID enum members and string keys."""

    def __getitem__(self, key: Any) -> str:
        if hasattr(key, "value") and key in self:
            return super().__getitem__(key)
        if hasattr(key, "value") and key.value in self:
            return super().__getitem__(key.value)
        if key in self:
            return super().__getitem__(key)
        return ""

    def get(self, key: Any, default: str = "") -> str:
        if hasattr(key, "value") and key in self:
            return super().__getitem__(key)
        if hasattr(key, "value") and key.value in self:
            return super().__getitem__(key.value)
        if key in self:
            return super().__getitem__(key)
        return default


# Action icons (emoji prefixes)
ACTION_ICONS = ActionIconsDict({
    ActionID.PAYMENT: "💳 ",
    ActionID.TIP: "💰 ",
    ActionID.MENU: "📋 ",
    ActionID.CANCEL: "❌ ",
    ActionID.ORDER_ANOTHER: "🍹 ",
    ActionID.PAYMENT.value: "💳 ",
    ActionID.TIP.value: "💰 ",
    ActionID.MENU.value: "📋 ",
    ActionID.CANCEL.value: "❌ ",
    ActionID.ORDER_ANOTHER.value: "🍹 ",
})


# CSS for chip styling and accessibility
CHIP_CSS = """
.chip-container {
    display: flex;
    flex-direction: row;
    gap: 8px;
    overflow-x: auto;
    overflow-y: hidden;
    padding: 12px 0;
    scroll-behavior: smooth;
    -webkit-overflow-scrolling: touch;
}

.chip-container::-webkit-scrollbar {
    height: 6px;
}

.chip-container::-webkit-scrollbar-track {
    background: rgba(0,0,0,0.05);
    border-radius: 3px;
}

.chip-container::-webkit-scrollbar-thumb {
    background: rgba(0,0,0,0.2);
    border-radius: 3px;
}

.chip-container::-webkit-scrollbar-thumb:hover {
    background: rgba(0,0,0,0.3);
}

.suggestion-chip {
    flex-shrink: 0;
    white-space: nowrap;
    transition: all 0.2s ease;
    border-radius: 20px !important;
    padding: 10px 20px !important;
    font-size: 14px !important;
    min-height: 44px !important;
    min-width: 44px !important;
    cursor: pointer !important;
}

.suggestion-chip:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
}

.suggestion-chip:focus {
    outline: 2px solid #4299e1 !important;
    outline-offset: 2px;
}

.chip-dialogue {
    background: linear-gradient(135deg, #4338ca 0%, #312e81 100%) !important;
    color: white !important;
}

.chip-action {
    background: linear-gradient(135deg, #be185d 0%, #881337 100%) !important;
    color: white !important;
    font-weight: 600 !important;
}

/* Mobile responsive */
@media (max-width: 768px) {
    .chip-container {
        padding: 8px 0;
    }

    .suggestion-chip {
        min-height: 44px !important;
        min-width: 44px !important;
        font-size: 13px !important;
    }
}

/* Accessibility - high contrast mode */
@media (prefers-contrast: high) {
    .suggestion-chip {
        border: 2px solid currentColor !important;
    }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
    .suggestion-chip {
        transition: none !important;
    }

    .suggestion-chip:hover {
        transform: none !important;
    }
}

/* ARIA live region for screen readers */
.chip-updates[aria-live="polite"] {
    position: absolute;
    left: -10000px;
    width: 1px;
    height: 1px;
    overflow: hidden;
}
"""


def create_chip_row(session_id: str = "default") -> tuple[gr.Row, list[gr.Button]]:
    """
    Create suggestion chips row component.

    Args:
        session_id: Current session identifier

    Returns:
        Tuple of (chip_row, chip_buttons)
    """
    with gr.Row(
        visible=False,
        elem_id="suggestion-chips-row",
        elem_classes=["chip-container"],
    ) as chip_row:
        # ARIA live region for screen readers to announce chip updates (Requirement 9.3)
        gr.HTML(
            '<div class="chip-updates" aria-live="polite" aria-atomic="true" id="chip-live-region"></div>',
            visible=True,
            elem_id="chip-live-region-html",
        )
        chip_buttons = []
        for i in range(6):
            btn = gr.Button(
                "",
                visible=False,
                elem_id=f"chip-{i}",
                elem_classes=["suggestion-chip"],
                size="sm",
            )
            chip_buttons.append(btn)

    return chip_row, chip_buttons


def get_chip_aria_label(chip: SuggestionChip) -> str:
    """
    Generate ARIA label for screen readers.

    Args:
        chip: SuggestionChip instance

    Returns:
        Formatted ARIA label string
    """
    chip_type_str = chip.type.value if hasattr(chip.type, "value") else str(chip.type)
    return f"{chip_type_str} chip: {chip.text}"


def update_chips(
    session_id: str,
    chip_buttons: list[gr.Button],
    app_state: MutableMapping | None = None,
) -> list[gr.Button]:
    """
    Update chip buttons with latest chip set from session state.

    Args:
        session_id: Current session ID
        chip_buttons: List of Gradio button components
        app_state: Optional application state dict

    Returns:
        Updated button components
    """
    session_state = get_session_state(session_id, app_state)
    chip_state = session_state.get("chip_state", {})
    chip_set = chip_state.get("current_chips")

    if not chip_set or not getattr(chip_set, "chips", None):
        return [gr.Button(value="", visible=False) for _ in chip_buttons]

    updates = []
    for i, _ in enumerate(chip_buttons):
        if i < len(chip_set.chips):
            chip = chip_set.chips[i]
            chip_type_str = chip.type.value if hasattr(chip.type, "value") else str(chip.type)
            action_id_str = (
                chip.action_id.value
                if hasattr(chip.action_id, "value")
                else (str(chip.action_id) if chip.action_id else "none")
            )

            # Add icon prefix for action chips
            display_text = chip.text
            if chip_type_str == ChipType.ACTION.value and chip.action_id:
                icon = ACTION_ICONS.get(chip.action_id, "")
                display_text = f"{icon}{chip.text}"

            # Calculate and set accessibility ARIA label (Requirements 5.1, 9.1)
            aria_label = get_chip_aria_label(chip)

            btn_update = gr.Button(
                value=display_text,
                visible=True,
                elem_classes=[
                    "suggestion-chip",
                    f"chip-{chip_type_str}",
                ],
                variant="primary" if chip_type_str == ChipType.ACTION.value else "secondary",
                elem_id=f"chip-{i}-{chip_type_str}-{action_id_str}",
            )
            btn_update.aria_label = aria_label
            updates.append(btn_update)
        else:
            updates.append(gr.Button(value="", visible=False))

    return updates


def handle_chip_click(
    chip_text: str,
    chip_type: str | ChipType = "dialogue",
    action_id: str | ActionID | None = None,
    session_id: str = "default",
    textbox: Any = None,
) -> tuple[str, str | None]:
    """
    Handle suggestion chip click event.

    Args:
        chip_text: Display or raw text of the clicked chip
        chip_type: Type of chip (dialogue or action)
        action_id: Optional action identifier for action chips
        session_id: Current session identifier
        textbox: Optional Gradio textbox component reference

    Returns:
        Tuple of (populated_text, submit_trigger):
            - populated_text: Clean chip text without icon prefix
            - submit_trigger: "submit" for action chips, None for dialogue chips
    """
    clean_text = chip_text or ""
    for icon in ACTION_ICONS.values():
        if clean_text.startswith(icon):
            clean_text = clean_text[len(icon) :]
            break

    type_val = (
        chip_type.value
        if hasattr(chip_type, "value")
        else str(chip_type).lower() if chip_type else "dialogue"
    )
    act_val = (
        action_id.value
        if hasattr(action_id, "value")
        else str(action_id).lower() if action_id else None
    )

    if type_val == ChipType.ACTION.value:
        valid_action_ids = {a.value for a in ActionID}
        if act_val and act_val not in valid_action_ids:
            logger.warning(f"Unrecognized action_id '{action_id}', treating as dialogue")
            return clean_text, None

        return clean_text, "submit"

    return clean_text, None


def register_chip_handlers(
    chip_buttons: list[gr.Button],
    textbox: gr.Textbox,
    submit_btn: gr.Button,
    session_id: str = "default",
    app_state: MutableMapping | None = None,
) -> None:
    """
    Register click handlers for suggestion chip buttons.

    Args:
        chip_buttons: List of 6 chip button components
        textbox: Main input textbox component
        submit_btn: Submit button component
        session_id: Current session identifier
        app_state: Optional application state dictionary
    """
    action_submit_js = """
    (trigger) => {
        if (trigger === 'submit') {
            const sendBtn = document.querySelector('#send-message-btn') ||
                            Array.from(document.querySelectorAll('button')).find(b => b.innerText && b.innerText.trim() === 'Send');
            if (sendBtn) sendBtn.click();
        }
    }
    """
    for i, chip_btn in enumerate(chip_buttons):
        def _make_handler(chip_idx: int):
            def _handler(text: str, sid: str = session_id):
                # Retrieve session chip state to resolve true chip type and action_id
                target_state = get_session_state(sid, app_state)
                chip_set = target_state.get("chip_state", {}).get("current_chips")
                chip_type = "dialogue"
                action_id = None
                if chip_set and hasattr(chip_set, "chips") and chip_idx < len(chip_set.chips):
                    chip = chip_set.chips[chip_idx]
                    chip_type = chip.type
                    action_id = chip.action_id
                else:
                    # Fallback: detect from icon prefix in text
                    for act_id, icon in ACTION_ICONS.items():
                        if text and text.startswith(icon):
                            chip_type = ChipType.ACTION
                            action_id = act_id
                            break

                return handle_chip_click(
                    chip_text=text,
                    chip_type=chip_type,
                    action_id=action_id,
                    session_id=sid,
                    textbox=textbox,
                )
            return _handler

        click_ev = chip_btn.click(
            fn=_make_handler(i),
            inputs=[chip_btn],
            outputs=[textbox, submit_btn],
            show_progress=False,
        )
        if hasattr(click_ev, "then"):
            click_ev.then(
                fn=None,
                inputs=[submit_btn],
                js=action_submit_js,
                show_progress=False,
            )
