"""Pure scroll/viewport math for Tk widgets.

Nothing here imports tkinter: everything takes and returns plain numbers, so
the geometry can be unit-tested headlessly without building a widget.
"""
from typing import Optional, Sequence, Tuple

DEFAULT_SCROLLREGION = (0.0, 0.0, 2000.0, 2000.0)


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


def parse_scrollregion(raw, default: Tuple[float, ...] = DEFAULT_SCROLLREGION
                       ) -> Tuple[float, float, float, float]:
    """A canvas `scrollregion` as four floats: (x1, y1, x2, y2).

    Tk hands it back as the string "x1 y1 x2 y2", but an unset region is "" and
    a caller may pass a sequence. Anything unparseable falls back to `default`.
    """
    if isinstance(raw, str):
        try:
            parts = [float(p) for p in raw.split()]
        except ValueError:
            parts = []
    elif isinstance(raw, Sequence):
        try:
            parts = [float(p) for p in raw]
        except (TypeError, ValueError):
            parts = []
    else:
        parts = []
    if len(parts) != 4:
        return tuple(float(v) for v in default)  # type: ignore[return-value]
    return parts[0], parts[1], parts[2], parts[3]


def view_bounds(region: Sequence[float], xview: Sequence[float],
                yview: Sequence[float]) -> Tuple[float, float, float, float]:
    """Canvas coordinates the viewport currently shows: (left, top, right,
    bottom), derived from Tk's xview()/yview() fractions.

    Careful: the size implied here understates the real viewport whenever the
    scrollregion is smaller than the window, because Tk caps the upper fraction
    at 1.0. Fine for finding a centre point; not usable to decide visibility.
    """
    x1, y1, x2, y2 = region
    span_x, span_y = x2 - x1, y2 - y1
    return (
        x1 + span_x * (xview[0] if xview else 0.0),
        y1 + span_y * (yview[0] if yview else 0.0),
        x1 + span_x * (xview[1] if len(xview) > 1 else 1.0),
        y1 + span_y * (yview[1] if len(yview) > 1 else 1.0),
    )


def is_fully_visible(view_start: float, view_size: float, target_start: float,
                     target_end: float, epsilon: float = 1.0) -> bool:
    """Whether [target_start, target_end] fits inside the viewport on one axis.
    `epsilon` absorbs sub-pixel noise so something flush against an edge is not
    judged clipped."""
    return (target_start >= view_start - epsilon
            and target_end <= view_start + view_size + epsilon)


def align_start_fraction(region_start: float, region_end: float,
                         view_start: float, view_size: float,
                         target_start: float, target_end: float,
                         ring_pad: float = 0.0, margin: float = 0.0,
                         epsilon: float = 1.0) -> Optional[float]:
    """Fraction for {x,y}view_moveto that puts `target_start` at the leading
    edge of the viewport, or None when this axis needs no scrolling.

    `ring_pad` inflates the target for the visibility test only (a decoration
    drawn outside the reported bbox still has to fit). `margin` is the gap left
    before the target once scrolled.
    """
    span = region_end - region_start
    # view_size <= 1 covers an unmapped canvas, where winfo_height() is 1, and
    # rules out negative sizes left over from subtracting the border inset.
    if span <= 0 or view_size <= 1:
        return None
    if is_fully_visible(view_start, view_size, target_start - ring_pad,
                        target_end + ring_pad, epsilon):
        return None
    # Clamping here is not a safety net — it is how this agrees with Tk's own
    # `confine`. When the window is larger than the region, Tk parks the view at
    # region_start no matter what fraction it is handed, and max() collapses the
    # allowed range to exactly that point.
    max_origin = max(region_start, region_end - view_size)
    origin = min(max(target_start - margin, region_start), max_origin)
    if abs(origin - view_start) < 1.0:
        return None  # already there; don't emit a no-op moveto
    return (origin - region_start) / span
