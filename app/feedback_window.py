"""Pop-up window that shows the teacher's feedback with Markdown formatting.

Owns a single reusable Toplevel: repeated submits refresh it in place instead
of stacking windows, and closing it is fine — the next show rebuilds it.

Deliberately does not take keyboard focus. The student stays in the sentence
field so they can keep writing while reading the correction.
"""
import tkinter as tk
from tkinter import ttk

from markdown_text import PLAIN_ERROR, PLAIN_INFO, MarkdownRenderer
from scroll_utils import wheel_step


class FeedbackWindow:
    TITLE = "Feedback do professor"
    GEOMETRY = "780x560"
    MIN_WIDTH = 420
    MIN_HEIGHT = 260

    def __init__(self, parent, renderer=None):
        self.parent = parent
        self.renderer = renderer or MarkdownRenderer()
        self.window = None
        self.text = None

    # ------------------------------------------------------------------ #
    #  What the panel calls                                               #
    # ------------------------------------------------------------------ #

    def show_markdown(self, markdown: str) -> None:
        self._show(markdown, None)

    def show_info(self, message: str) -> None:
        self._show(message, PLAIN_INFO)

    def show_error(self, message: str) -> None:
        self._show(message, PLAIN_ERROR)

    def close(self, _event=None) -> None:
        window, self.window, self.text = self.window, None, None
        if window is not None:
            try:
                window.destroy()
            except tk.TclError:
                pass

    # ------------------------------------------------------------------ #
    #  Internals                                                          #
    # ------------------------------------------------------------------ #

    def _show(self, message: str, plain_tag) -> None:
        self._ensure_window()
        if self.text is None:
            return
        try:
            self.text.config(state="normal")
            self.text.delete("1.0", "end")
            if plain_tag:
                self.renderer.render_plain(self.text, message, plain_tag)
            else:
                self.renderer.render(self.text, message)
            self.text.mark_set("insert", "1.0")
            self.text.see("1.0")
            self.text.config(state="disabled")
            self.window.deiconify()
            self.window.lift()  # lift, never focus — see module docstring
        except tk.TclError:
            self.close()

    def _ensure_window(self) -> None:
        if self.window is not None:
            try:
                if self.window.winfo_exists():
                    return
            except tk.TclError:
                pass
        self.close()
        self._build()

    def _build(self) -> None:
        self.window = tk.Toplevel(self.parent)
        self.window.title(self.TITLE)
        self.window.geometry(self.GEOMETRY)
        self.window.minsize(self.MIN_WIDTH, self.MIN_HEIGHT)
        # transient: stays above the app and follows it when minimized, so the
        # feedback can't get lost behind the main window.
        try:
            self.window.transient(self.parent)
        except tk.TclError:
            pass
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.bind("<Escape>", self.close)

        body = ttk.Frame(self.window)
        body.pack(fill="both", expand=True)

        self.text = tk.Text(body, wrap="word", bg="white", fg="#212529",
                            relief="flat", borderwidth=0, padx=22, pady=18,
                            state="disabled", cursor="arrow",
                            takefocus=False)
        scrollbar = ttk.Scrollbar(body, orient="vertical",
                                  command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        self.text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.text.bind(sequence, self._on_mousewheel)
        for sequence in ("<Command-c>", "<Control-c>"):
            self.text.bind(sequence, self._on_copy_shortcut)
        self.text.bind("<Escape>", self.close)

        footer = ttk.Frame(self.window, padding=(10, 8))
        footer.pack(fill="x")
        ttk.Button(footer, text="Fechar", width=10,
                   command=self.close).pack(side="right")

    def _on_mousewheel(self, event):
        step = wheel_step(event)
        if step is None:
            return None
        self.text.yview_scroll(step, "units")
        return "break"

    def _on_copy_shortcut(self, _event) -> str:
        try:
            selection = self.text.get("sel.first", "sel.last")
        except tk.TclError:
            return "break"  # nothing selected
        if selection:
            self.text.clipboard_clear()
            self.text.clipboard_append(selection)
        return "break"
