"""Scroll a Tk canvas so a selected word is fully visible, leading-edge aligned.

Kept out of WordCanvasApp because it carries its own coalescing state and only
needs a canvas plus a way to ask for a word's bounding box — injected as a
callable, so this never has to know CanvasRenderer exists.
"""
import tkinter as tk
from typing import Callable, Optional, Tuple

from scroll_utils import align_start_fraction, parse_scrollregion

# CanvasRenderer.select() draws its ring at bbox ± 5 with width=2, so the
# outermost pixel sits at bbox - 6. word_bbox() excludes the ring, so the
# visibility test has to inflate by that much or a word judged "visible" can
# still have its ring clipped.
RING_PAD = 6
# Where the word lands once scrolled: bbox_top - 12 goes to the viewport edge.
# 6 for the ring plus 6 of breathing room. Comfortably inside the 50px of
# padding update_scroll_region() leaves around the content, so even the topmost
# word gets the full margin instead of being clamped.
LEAD_MARGIN = 12

BboxProvider = Callable[[int], Optional[Tuple[int, int, int, int]]]


class ViewportScroller:
    def __init__(self, canvas, bbox_provider: BboxProvider,
                 margin: int = LEAD_MARGIN, ring_pad: int = RING_PAD):
        self._canvas = canvas
        self._bbox_of = bbox_provider
        self._margin = margin
        self._ring_pad = ring_pad
        self._pending: Optional[int] = None
        self._scheduled = False

    def ensure_visible_soon(self, word_id: int) -> None:
        """Queue a scroll for the next idle moment. Last request wins, so a
        burst of Tab presses collapses into one scroll — to whichever word
        ended up selected."""
        self._pending = word_id
        if self._scheduled:
            return
        self._scheduled = True
        try:
            self._canvas.after_idle(self._flush)
        except tk.TclError:
            self._scheduled = False  # canvas already gone

    def _flush(self) -> None:
        self._scheduled = False
        word_id, self._pending = self._pending, None
        if word_id is not None:
            self.ensure_visible_now(word_id)

    def ensure_visible_now(self, word_id: int) -> None:
        """Scroll immediately. Public so tests can drive it without pumping the
        event loop."""
        try:
            # Selecting a word for the first time makes the side panels insert
            # themselves, which shrinks the canvas. A plain after_idle callback
            # still reads the pre-insert width — only settling here gets the
            # real one.
            self._canvas.update_idletasks()
            bbox = self._bbox_of(word_id)
            if not bbox:
                return
            # tk.Canvas defaults to highlightthickness=3, so winfo_width()
            # overstates the drawable area by twice the inset and the first
            # drawable pixel is at canvasx(inset), not canvasx(0).
            inset = (int(self._canvas.cget("highlightthickness"))
                     + int(self._canvas.cget("borderwidth")))
            x1, y1, x2, y2 = parse_scrollregion(
                self._canvas.cget("scrollregion"))
            view_x = self._canvas.canvasx(inset)
            view_y = self._canvas.canvasy(inset)
            view_w = max(0, self._canvas.winfo_width() - 2 * inset)
            view_h = max(0, self._canvas.winfo_height() - 2 * inset)
        except tk.TclError:
            return  # canvas destroyed mid-teardown

        min_x, min_y, max_x, max_y = bbox
        # Axes are judged independently: a word that is off the bottom but fine
        # horizontally must not also lurch sideways.
        fraction_x = align_start_fraction(x1, x2, view_x, view_w, min_x, max_x,
                                          self._ring_pad, self._margin)
        fraction_y = align_start_fraction(y1, y2, view_y, view_h, min_y, max_y,
                                          self._ring_pad, self._margin)
        try:
            if fraction_x is not None:
                self._canvas.xview_moveto(fraction_x)
            if fraction_y is not None:
                self._canvas.yview_moveto(fraction_y)
        except tk.TclError:
            pass
