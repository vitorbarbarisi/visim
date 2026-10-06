"""Top bar: previous file, the current file's name, next file.

Same shape as SentenceFeedbackPanel — the class builds its own frame and
exposes it, the app decides where to grid it — and the same injected-callback
style as MenuBuilder, so this never learns what a CSV is.
"""
import os
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

PREV_LABEL = "← Anterior"
NEXT_LABEL = "Próximo →"
# Matches SentenceFeedbackPanel's "Enviar" button so the top and bottom bars
# read as one family. Both labels fit: "← Anterior" is exactly 10 characters.
BUTTON_WIDTH = 10
# macOS renders ttk buttons through the native aqua theme, which draws no focus
# ring of its own and exposes no focuscolor/bordercolor/focusthickness to style
# one in — a focused button was indistinguishable from an idle one, which broke
# the keyboard-only flow (you could not see where Tab had landed). A plain
# tk.Frame behind the button does honour a background colour on every platform,
# so the ring is drawn as padding around the button. Blue on purpose: it is the
# same colour the canvas rings the selected word with.
FOCUS_RING = 3
FOCUS_COLOR = "blue"


class TopBar:
    def __init__(self, parent, on_prev: Callable[[], None],
                 on_next: Callable[[], None]):
        self.frame = ttk.Frame(parent, relief="solid", borderwidth=1,
                               padding=(8, 6))
        self._on_prev = on_prev
        self._on_next = on_next
        self._build()

    def _build(self) -> None:
        # Only the middle column stretches, so the file name stays centred in
        # the window regardless of how wide the buttons render.
        self.frame.columnconfigure(1, weight=1)

        self._idle_color = self._frame_background()

        self.prev_button, prev_ring = self._make_button(PREV_LABEL, self._on_prev)
        prev_ring.grid(row=0, column=0)

        self.title_var = tk.StringVar()
        self.title_label = ttk.Label(self.frame, textvariable=self.title_var,
                                     font=("Arial", 13, "bold"),
                                     anchor="center")
        self.title_label.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=8)

        self.next_button, next_ring = self._make_button(NEXT_LABEL, self._on_next)
        next_ring.grid(row=0, column=2)

    def _frame_background(self) -> str:
        """The bar's own background, so an unfocused ring disappears into it.

        Read from the theme rather than hardcoded: on macOS this is the dynamic
        systemWindowBackgroundColor, which follows light/dark mode on its own.
        """
        try:
            colour = ttk.Style().lookup("TFrame", "background")
        except tk.TclError:
            colour = ""
        return colour or self.frame.winfo_toplevel().cget("background")

    def _make_button(self, label: str, command: Callable[[], None]):
        ring = tk.Frame(self.frame, background=self._idle_color,
                        padx=FOCUS_RING, pady=FOCUS_RING)
        button = ttk.Button(ring, text=label, width=BUTTON_WIDTH,
                            command=command)
        button.pack()
        # ttk.Button only binds <space> by default. Enter has to be explicit or
        # the keyboard-only flow (Tab to the button, Enter to open) dead-ends.
        for seq in ("<Return>", "<KP_Enter>"):
            button.bind(seq, lambda _e, b=button: (b.invoke(), "break")[1])
        # The ring is padding that is always there; only its colour changes, so
        # lighting it up never nudges the layout.
        button.bind("<FocusIn>", lambda _e, r=ring: self._paint(r, FOCUS_COLOR))
        button.bind("<FocusOut>", lambda _e, r=ring: self._paint(r, self._idle_color))
        return button, ring

    def _paint(self, ring, colour: str) -> None:
        try:
            ring.configure(background=colour)
        except tk.TclError:
            pass  # widget torn down mid-teardown

    def set_file(self, path: Optional[str]) -> None:
        """Show the file's name without its extension — '2026_08_13.csv' reads
        as the study day it is, not as a file."""
        if not path:
            self.title_var.set("")
            return
        self.title_var.set(os.path.splitext(os.path.basename(path))[0])

    def focus_prev(self) -> None:
        self.prev_button.focus_set()

    def focus_next(self) -> None:
        self.next_button.focus_set()

    def owns_focus(self, widget) -> bool:
        return widget is self.prev_button or widget is self.next_button
