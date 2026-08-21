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

        self.prev_button = self._make_button(PREV_LABEL, self._on_prev)
        self.prev_button.grid(row=0, column=0)

        self.title_var = tk.StringVar()
        self.title_label = ttk.Label(self.frame, textvariable=self.title_var,
                                     font=("Arial", 13, "bold"),
                                     anchor="center")
        self.title_label.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=8)

        self.next_button = self._make_button(NEXT_LABEL, self._on_next)
        self.next_button.grid(row=0, column=2)

    def _make_button(self, label: str, command: Callable[[], None]) -> ttk.Button:
        button = ttk.Button(self.frame, text=label, width=BUTTON_WIDTH,
                            command=command)
        # ttk.Button only binds <space> by default. Enter has to be explicit or
        # the keyboard-only flow (Tab to the button, Enter to open) dead-ends.
        for seq in ("<Return>", "<KP_Enter>"):
            button.bind(seq, lambda _e, b=button: (b.invoke(), "break")[1])
        return button

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
