"""Tab overlay component for displaying tab and balance on Maya's avatar.

This module provides the visual overlay that shows the user's running tab
and remaining balance, with animated count-up effects when values change.
It also includes tip button functionality for adding gratuity.
"""

from typing import Optional, Literal
from ..config.logging_config import get_logger

logger = get_logger(__name__)

# Tip button constants
TIP_PERCENTAGES = (10, 15, 20)
TIP_BUTTON_HIGHLIGHT_COLOR = "#4CAF50"  # Green for selected button
TIP_BUTTON_DEFAULT_BG = "#333333"       # Dark gray for unselected buttons

# Color constants for balance display
COLOR_NORMAL = "#FFFFFF"      # White for balance >= $50
COLOR_LOW_FUNDS = "#FFA500"   # Orange for 0 < balance < $50
COLOR_DEPLETED = "#FF4444"    # Red for balance <= $0


def get_balance_color(balance: float) -> str:
    """Return the appropriate color based on balance level.
    
    Args:
        balance: Current user balance in dollars
        
    Returns:
        Hex color string:
        - '#FFFFFF' for balance >= $50 (normal)
        - '#FFA500' for 0 < balance < $50 (low funds warning)
        - '#FF4444' for balance <= $0 (depleted/negative)
        
    Requirements: 6.3, 6.4
    """
    if balance >= 50.0:
        return COLOR_NORMAL
    elif balance > 0:
        return COLOR_LOW_FUNDS
    else:
        return COLOR_DEPLETED


def create_tip_buttons_html(
    tab_amount: float,
    selected_percentage: Optional[int] = None,
    on_tip_click_callback: str = "handleTipClick"
) -> str:
    """Generate HTML for tip selection buttons.
    
    Creates three tip buttons (10%, 15%, 20%) that allow users to add
    gratuity to their tab. Buttons are disabled when tab is $0.
    
    Args:
        tab_amount: Current tab total (to determine if buttons should be enabled)
        selected_percentage: Currently selected tip percentage (10, 15, 20) or None
        on_tip_click_callback: JavaScript callback name for tip button clicks
        
    Returns:
        HTML string with three tip buttons:
        - Buttons disabled/hidden if tab_amount == 0
        - Selected button highlighted with #4CAF50 background color
        - Unselected buttons use default styling (#333333)
        - Visual state updates immediately on select/replace/toggle
        
    Requirements: 7.1, 7.7, 7.8
    """
    is_disabled = tab_amount <= 0
    display_style = "none" if is_disabled else "flex"
    
    buttons_html = []
    for percentage in TIP_PERCENTAGES:
        is_selected = selected_percentage == percentage
        bg_color = TIP_BUTTON_HIGHLIGHT_COLOR if is_selected else TIP_BUTTON_DEFAULT_BG
        border_color = TIP_BUTTON_HIGHLIGHT_COLOR if is_selected else "#555555"
        
        disabled_attr = 'disabled="disabled"' if is_disabled else ""
        cursor_style = "not-allowed" if is_disabled else "pointer"
        opacity = "0.5" if is_disabled else "1"
        
        button_html = f'''
        <button 
            class="tip-button" 
            data-percentage="{percentage}"
            onclick="{on_tip_click_callback}({percentage})"
            {disabled_attr}
            style="
                background: {bg_color};
                color: #FFFFFF;
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 14px;
                font-weight: 500;
                cursor: {cursor_style};
                opacity: {opacity};
                transition: background 0.2s, border-color 0.2s;
                min-width: 50px;
            "
        >{percentage}%</button>'''
        buttons_html.append(button_html)
    
    return f'''
    <div class="tip-buttons-row" style="
        display: {display_style};
        gap: 8px;
        margin-top: 8px;
        justify-content: center;
        align-items: center;
    ">
        {"".join(buttons_html)}
    </div>
    '''


def generate_tip_notification(percentage: int, tip_amount: float, _tab_total: float) -> str:
    """Generate notification message sent to Maya when user selects a tip.
    
    Creates a conversational message that conveys the user's tip selection
    intent, including both the percentage and calculated amount.
    
    Args:
        percentage: Selected tip percentage (10, 15, or 20)
        tip_amount: Calculated tip amount in dollars
        _tab_total: Current tab total in dollars
        
    Returns:
        Message conveying tip selection intent containing both percentage
        and amount values.
        
    Requirements: 7.11
    """
    return f"I'd like to add a {percentage}% tip (${tip_amount:.2f}) for your great service!"

def generate_tip_removal_notification() -> str:
    """Generate notification message sent to Maya when user removes tip.
    
    Creates a conversational message that conveys the user's intent
    to remove the previously selected tip.
    
    Returns:
        Message conveying tip removal intent.
        
    Requirements: 7.12
    """
    return "I've decided to remove the tip."


def create_tab_overlay_html(
    tab_amount: float,
    balance: float,
    prev_tab: float = 0.0,
    prev_balance: float = 1000.0,
    avatar_path: Optional[str] = None,
    tip_percentage: Optional[int] = None,
    tip_amount: float = 0.0,
    on_tip_click_callback: str = "handleTipClick"
) -> str:
    """Generate HTML/CSS/JS for tab overlay with animation and tip buttons.
    
    Creates an overlay positioned at the bottom-left of Maya's avatar
    showing the current tab and balance with count-up animations,
    plus tip selection buttons and tip/total display.
    
    Args:
        tab_amount: Current tab total (drinks only)
        balance: Current user balance
        prev_tab: Previous tab amount (for animation start value)
        prev_balance: Previous balance (for animation start value)
        avatar_path: Path to avatar image (optional)
        tip_percentage: Currently selected tip (10, 15, 20) or None
        tip_amount: Calculated tip amount
        on_tip_click_callback: JavaScript callback name for tip button clicks
        
    Returns:
        HTML string with embedded CSS and JavaScript for animations and tip buttons
        
    Requirements: 2.1, 2.3, 2.4, 5.1, 5.2, 5.3, 5.4, 6.1, 7.1, 7.3, 7.4
    """
    balance_color = get_balance_color(balance)
    avatar_src = avatar_path or "assets/bartender_avatar.jpg"
    
    # Generate tip buttons HTML
    tip_buttons_html = create_tip_buttons_html(
        tab_amount=tab_amount,
        selected_percentage=tip_percentage,
        on_tip_click_callback=on_tip_click_callback
    )
    
    # Calculate total with tip
    total_with_tip = tab_amount + tip_amount
    
    # Tip and total row - only shown when tip is selected
    tip_display_style = "flex" if tip_percentage is not None else "none"
    
    html = f'''
<div class="avatar-overlay-container" style="position: relative; display: inline-block; width: 100%; max-width: 600px;">
    <img src="file/{avatar_src}" alt="Maya the Bartender" style="width: 100%; height: auto; display: block; border-radius: 8px;">
    
    <div class="tab-overlay" style="
        position: absolute;
        bottom: 16px;
        left: 16px;
        background: rgba(0, 0, 0, 0.7);
        padding: 12px 16px;
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        gap: 8px;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        z-index: 10;
    ">
        <!-- Row 1: Tab and Balance -->
        <div class="tab-balance-row" style="
            display: flex;
            gap: 12px;
            align-items: center;
        ">
            <span class="tab-display" id="tab-display" style="
                color: #FFFFFF;
                font-size: 16px;
                font-weight: 600;
            " data-value="{tab_amount}" data-prev="{prev_tab}">Tab: ${tab_amount:.2f}</span>
            
            <span class="balance-display" id="balance-display" style="
                color: {balance_color};
                font-size: 16px;
                font-weight: 600;
            " data-value="{balance}" data-prev="{prev_balance}">Balance: ${balance:.2f}</span>
        </div>
        
        <!-- Row 2: Tip Buttons (hidden when tab is $0) -->
        {tip_buttons_html}
        
        <!-- Row 3: Tip and Total (hidden when no tip selected) -->
        <div class="tip-total-row" style="
            display: {tip_display_style};
            gap: 12px;
            align-items: center;
            justify-content: space-between;
            margin-top: 4px;
        ">
            <span class="tip-display" id="tip-display" style="
                color: #90EE90;
                font-size: 14px;
                font-weight: 500;
            " data-value="{tip_amount}">Tip: ${tip_amount:.2f}</span>
            
            <span class="total-display" id="total-display" style="
                color: #FFD700;
                font-size: 16px;
                font-weight: 700;
            " data-value="{total_with_tip}">Total: ${total_with_tip:.2f}</span>
        </div>
    </div>
</div>

<script>
(function() {{
    // Animation Queue Manager
    const AnimationQueue = {{
        queue: [],
        isRunning: false,
        maxDepth: 5,
        collapseWindowMs: 100,
        lastEnqueueTime: 0,
        callbacks: {{
            onAnimationStart: null,
            onAnimationComplete: null,
            onAnimationCancel: null
        }},
        
        enqueue: function(update) {{
            const now = Date.now();
            
            // Collapse strategy: if within 100ms of last update, merge
            if (this.queue.length > 0 && (now - this.lastEnqueueTime) < this.collapseWindowMs) {{
                // Update the last queued item's end values
                const lastItem = this.queue[this.queue.length - 1];
                lastItem.endTab = update.endTab;
                lastItem.endBalance = update.endBalance;
            }} else {{
                // Add new item to queue
                if (this.queue.length >= this.maxDepth) {{
                    // Drop oldest if at max depth
                    this.queue.shift();
                }}
                this.queue.push(update);
            }}
            
            this.lastEnqueueTime = now;
            
            if (!this.isRunning) {{
                this.processNext();
            }}
        }},
        
        processNext: function() {{
            if (this.queue.length === 0) {{
                this.isRunning = false;
                return;
            }}
            
            this.isRunning = true;
            const update = this.queue.shift();
            this.animate(update);
        }},
        
        animate: function(update) {{
            const duration = 500;
            const startTime = performance.now();
            
            const tabEl = document.getElementById('tab-display');
            const balanceEl = document.getElementById('balance-display');
            
            if (!tabEl || !balanceEl) {{
                this.processNext();
                return;
            }}
            
            // Trigger start callback
            if (this.callbacks.onAnimationStart) {{
                this.callbacks.onAnimationStart(update);
            }}
            
            // Apply pulse effect
            tabEl.style.transition = 'transform 250ms ease-out';
            balanceEl.style.transition = 'transform 250ms ease-out';
            tabEl.style.transform = 'scale(1.1)';
            balanceEl.style.transform = 'scale(1.1)';
            
            const self = this;
            
            function step(currentTime) {{
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
                // Linear interpolation
                const currentTab = update.startTab + (update.endTab - update.startTab) * progress;
                const currentBalance = update.startBalance + (update.endBalance - update.startBalance) * progress;
                
                tabEl.textContent = 'Tab: $' + currentTab.toFixed(2);
                balanceEl.textContent = 'Balance: $' + currentBalance.toFixed(2);
                
                // Update balance color based on current animated value
                balanceEl.style.color = getBalanceColor(currentBalance);
                
                // Scale back down at halfway point
                if (progress >= 0.5) {{
                    tabEl.style.transform = 'scale(1.0)';
                    balanceEl.style.transform = 'scale(1.0)';
                }}
                
                if (progress < 1) {{
                    requestAnimationFrame(step);
                }} else {{
                    // Animation complete
                    tabEl.dataset.value = update.endTab;
                    balanceEl.dataset.value = update.endBalance;
                    
                    if (self.callbacks.onAnimationComplete) {{
                        self.callbacks.onAnimationComplete(update);
                    }}
                    
                    self.processNext();
                }}
            }}
            
            requestAnimationFrame(step);
        }},
        
        cancelAll: function(finalTab, finalBalance) {{
            // Cancel running animation and render final values
            if (this.callbacks.onAnimationCancel) {{
                this.callbacks.onAnimationCancel();
            }}
            
            this.queue = [];
            this.isRunning = false;
            
            const tabEl = document.getElementById('tab-display');
            const balanceEl = document.getElementById('balance-display');
            
            if (tabEl && balanceEl) {{
                tabEl.textContent = 'Tab: $' + finalTab.toFixed(2);
                balanceEl.textContent = 'Balance: $' + finalBalance.toFixed(2);
                balanceEl.style.color = getBalanceColor(finalBalance);
                tabEl.style.transform = 'scale(1.0)';
                balanceEl.style.transform = 'scale(1.0)';
                tabEl.dataset.value = finalTab;
                balanceEl.dataset.value = finalBalance;
            }}
        }},
        
        getQueueLength: function() {{
            return this.queue.length;
        }}
    }};
    
    function getBalanceColor(balance) {{
        if (balance >= 50.0) {{
            return '{COLOR_NORMAL}';
        }} else if (balance > 0) {{
            return '{COLOR_LOW_FUNDS}';
        }} else {{
            return '{COLOR_DEPLETED}';
        }}
    }}
    
    // Initialize animation if values changed
    const tabEl = document.getElementById('tab-display');
    const balanceEl = document.getElementById('balance-display');
    
    if (tabEl && balanceEl) {{
        const prevTab = parseFloat(tabEl.dataset.prev) || 0;
        const currentTab = parseFloat(tabEl.dataset.value) || 0;
        const prevBalance = parseFloat(balanceEl.dataset.prev) || 1000;
        const currentBalance = parseFloat(balanceEl.dataset.value) || 1000;
        
        // Only animate if values actually changed
        if (prevTab !== currentTab || prevBalance !== currentBalance) {{
            AnimationQueue.enqueue({{
                startTab: prevTab,
                endTab: currentTab,
                startBalance: prevBalance,
                endBalance: currentBalance
            }});
        }}
    }}
    
    // Expose for external access
    window.TabOverlayAnimationQueue = AnimationQueue;
}})();
</script>
'''
    return html


# =============================================================================
# Python Animation Queue (for testing purposes)
# =============================================================================
# This mirrors the JavaScript AnimationQueue behavior for property-based testing

from dataclasses import dataclass, field
from typing import List, Callable, Optional
import time


@dataclass
class TabUpdate:
    """Represents a tab/balance update for animation."""
    start_tab: float
    end_tab: float
    start_balance: float
    end_balance: float
    timestamp: float = field(default_factory=time.time)


class AnimationQueue:
    """Python implementation of the animation queue for testing.
    
    This class mirrors the JavaScript AnimationQueue behavior to enable
    property-based testing of the queue logic.
    
    Requirements: 5.3
    """
    
    MAX_DEPTH = 5
    COLLAPSE_WINDOW_MS = 100
    
    def __init__(self):
        self._queue: List[TabUpdate] = []
        self._is_running: bool = False
        self._last_enqueue_time: float = 0
        
        # Callbacks
        self.on_animation_start: Optional[Callable[[TabUpdate], None]] = None
        self.on_animation_complete: Optional[Callable[[TabUpdate], None]] = None
        self.on_animation_cancel: Optional[Callable[[], None]] = None
    
    def enqueue(self, update: TabUpdate) -> None:
        """Add an update to the animation queue.
        
        Implements collapse strategy: updates within 100ms are merged.
        Queue max depth is 5 (oldest dropped if exceeded).
        """
        now = time.time() * 1000  # Convert to milliseconds
        
        # Collapse strategy: if within 100ms of last update, merge
        time_since_last = now - self._last_enqueue_time
        if self._queue and time_since_last < self.COLLAPSE_WINDOW_MS:
            # Update the last queued item's end values
            last_item = self._queue[-1]
            # Create new update with merged values
            merged = TabUpdate(
                start_tab=last_item.start_tab,
                end_tab=update.end_tab,
                start_balance=last_item.start_balance,
                end_balance=update.end_balance,
                timestamp=last_item.timestamp
            )
            self._queue[-1] = merged
        else:
            # Add new item to queue
            if len(self._queue) >= self.MAX_DEPTH:
                # Drop oldest if at max depth
                self._queue.pop(0)
            self._queue.append(update)
        
        self._last_enqueue_time = now
    
    def process_next(self) -> Optional[TabUpdate]:
        """Process and return the next update from the queue.
        
        Returns None if queue is empty.
        """
        if not self._queue:
            self._is_running = False
            return None
        
        self._is_running = True
        return self._queue.pop(0)
    
    def cancel_all(self) -> None:
        """Cancel all pending animations and clear the queue."""
        if self.on_animation_cancel:
            self.on_animation_cancel()
        
        self._queue.clear()
        self._is_running = False
    
    def get_queue_length(self) -> int:
        """Return the current queue length."""
        return len(self._queue)
    
    @property
    def is_running(self) -> bool:
        """Return whether an animation is currently running."""
        return self._is_running
    
    def reset(self) -> None:
        """Reset the queue to initial state (for testing)."""
        self._queue.clear()
        self._is_running = False
        self._last_enqueue_time = 0
