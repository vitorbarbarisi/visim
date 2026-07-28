"""Cross-platform mouse-wheel delta normalization for Tk widgets."""
from typing import Optional


def wheel_step(event) -> Optional[int]:
    """Scroll units for a wheel event, or None when there is nothing to scroll.

    X11 reports the wheel as Button-4/5; Windows uses ±120 multiples; macOS
    reports small deltas (±1..3) that int(delta/120) truncates to zero, which
    is what made wheel/trackpad scrolling a no-op on Mac.
    """
    num = getattr(event, 'num', None)
    if num == 4:
        return -1
    if num == 5:
        return 1
    delta = getattr(event, 'delta', 0)
    if abs(delta) >= 120:
        return -int(delta / 120)
    if delta:
        return -1 if delta > 0 else 1
    return None
