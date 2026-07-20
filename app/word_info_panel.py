"""Left side panel: word details + related-words tabs per character."""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Optional

from chinese_utils import is_chinese_char


class WordInfoPanel:
    def __init__(self, paned: ttk.PanedWindow, api_client, config, tasks,
                 on_related_double_click: Callable[[str], None]):
        self.paned = paned
        self.api = api_client
        self.config = config
        self.tasks = tasks
        self.on_related_double_click = on_related_double_click

        self.frame = ttk.Frame(paned, relief="solid", borderwidth=1)
        self.visible = False
        self.last_sash_position: Optional[int] = None
        self._search_results: list = []
        self._request_seq = 0  # bumped per load/search to discard stale async results
        self._focus_character: Optional[int] = None  # which character tab to open by default
        self._current_word_id: Optional[int] = None  # canvas word_id backing the current view, if any
        # In-memory per-canvas-word quiz state, so revisiting a word restores
        # exactly what the user left: {word_id: {'confirmed', 'typed_text', 'error'}}
        self._word_states: Dict[int, dict] = {}

        self._build()

    def _build(self) -> None:
        header = ttk.Frame(self.frame)
        header.pack(fill="x", padx=5, pady=5)

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(header, textvariable=self.search_var,
                                      font=("Arial", 11, "bold"))
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.bind("<Return>", lambda _e: self._search())
        self.search_entry.insert(0, "Buscar palavra…")
        self.search_entry.bind("<FocusIn>", self._on_entry_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_entry_focus_out)

        ttk.Button(header, text="⌕", width=3, command=self._search).pack(side="left", padx=(4, 0))
        ttk.Button(header, text="×", width=3, command=self.hide).pack(side="right")

        content = ttk.Frame(self.frame)
        content.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        info = ttk.LabelFrame(content, text="Detalhes", padding=10)
        info.pack(fill="x", pady=(0, 10))

        style = ttk.Style()
        style.configure("WordError.TEntry", fieldbackground="#fde0e0")

        self.labels: Dict[str, ttk.Label] = {}
        self._word_error = False
        self._pinyin_visible = False
        self._pinyin_value = ""
        self._current_word: Optional[str] = None  # the correct answer for the Palavra quiz

        # --- Palavra: blank quiz entry that becomes a static label once the
        # user types the exact word. Entry/button and the display label share
        # the same row and are toggled via pack()/pack_forget(). ---
        word_row = ttk.Frame(info)
        word_row.pack(fill="x", pady=3)
        ttk.Label(word_row, text="Palavra:", font=("Arial", 10, "bold")).pack(side="left", anchor="n")
        self.word_edit_var = tk.StringVar()
        self.word_entry = ttk.Entry(word_row, textvariable=self.word_edit_var,
                                    font=("Arial", 10))
        self.word_entry.bind("<Return>", lambda _e: self._on_word_confirm())
        self.word_entry.bind("<KeyRelease>", self._on_word_entry_changed)
        self.word_confirm_btn = ttk.Button(word_row, text="⚡", width=3,
                                           command=self._on_word_confirm)
        self.word_display_label = ttk.Label(word_row, text="", font=("Arial", 10))

        # --- Pinyin: hidden by default, revealed via eye-toggle button ---
        pinyin_row = ttk.Frame(info)
        pinyin_row.pack(fill="x", pady=3)
        ttk.Label(pinyin_row, text="Pinyin:", font=("Arial", 10, "bold")).pack(side="left", anchor="n")
        pinyin_value = ttk.Label(pinyin_row, text="", font=("Arial", 10))
        pinyin_value.pack(side="left", padx=(10, 4))
        self.labels["pinyin"] = pinyin_value
        self.pinyin_toggle_btn = ttk.Button(pinyin_row, text="👁", width=3,
                                            command=self._toggle_pinyin_visibility)
        self.pinyin_toggle_btn.pack(side="left")

        for key, label_text in (
            ("calls", "Calls:"),
            ("confidence", "Confidence Level:"),
            ("translations", "Traduções:"),
        ):
            row = ttk.Frame(info)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label_text, font=("Arial", 10, "bold")).pack(side="left", anchor="n")
            if key == "translations":
                value = ttk.Label(row, text="", font=("Arial", 10),
                                  justify="left", anchor="nw", wraplength=200)
                value.pack(side="left", padx=(10, 0), fill="x", expand=True)
                value.bind("<Configure>",
                           lambda e: e.widget.config(wraplength=max(50, e.width - 4)))
            else:
                value = ttk.Label(row, text="", font=("Arial", 10))
                value.pack(side="left", padx=(10, 0))
            self.labels[key] = value

        related = ttk.LabelFrame(content, text="Palavras Relacionadas", padding=10)
        related.pack(fill="both", expand=True)
        self.notebook = ttk.Notebook(related)
        self.notebook.pack(fill="both", expand=True)
        self.trees: Dict[str, ttk.Treeview] = {}

        self._show_placeholder()

    # ------------------------------------------------------------------ #
    #  Search entry placeholder helpers                                    #
    # ------------------------------------------------------------------ #

    def _on_entry_focus_in(self, _event) -> None:
        if self.search_var.get() == "Buscar palavra…":
            self.search_entry.delete(0, "end")

    def _on_entry_focus_out(self, _event) -> None:
        if not self.search_var.get().strip():
            self.search_entry.insert(0, "Buscar palavra…")

    # ------------------------------------------------------------------ #
    #  Palavra field: inline edit + validation                            #
    # ------------------------------------------------------------------ #

    def _on_word_confirm(self) -> None:
        if self._current_word is None:
            return
        typed = self.word_edit_var.get().strip()
        if not typed:
            return
        if typed == self._current_word:
            self._show_word_confirmed()
        else:
            self._mark_word_error()
            self._persist_word_state(typed_text=typed, error=True, confirmed=False)

    def _on_word_entry_changed(self, _event=None) -> None:
        if self._word_error:
            self._clear_word_error()
        self._persist_word_state(
            typed_text=self.word_edit_var.get(), error=False, confirmed=False,
        )

    def _mark_word_error(self) -> None:
        self._word_error = True
        self.word_confirm_btn.config(text="✕")
        self.word_entry.configure(style="WordError.TEntry")

    def _clear_word_error(self) -> None:
        self._word_error = False
        self.word_confirm_btn.config(text="⚡")
        self.word_entry.configure(style="TEntry")

    def _persist_word_state(self, **updates) -> None:
        """Remember the quiz state for the canvas word currently shown, so
        navigating away and back restores exactly what the user left."""
        if self._current_word_id is None:
            return
        state = self._word_states.setdefault(
            self._current_word_id,
            {'confirmed': False, 'typed_text': '', 'error': False, 'pinyin_visible': False},
        )
        state.update(updates)

    def _enter_word_edit_mode(self, restore_state: Optional[dict] = None) -> None:
        """Show the editable Palavra entry (the quiz state), blank by default
        or restored to whatever the user had left it at for this word."""
        self.word_display_label.pack_forget()
        self.word_entry.pack(side="left", padx=(10, 4), fill="x", expand=True)
        self.word_confirm_btn.pack(side="left")

        # Lock pinyin behind the correct answer so it can't be used to cheat.
        self._pinyin_visible = False
        self._refresh_pinyin_label()
        self.pinyin_toggle_btn.config(state="disabled")

        typed = restore_state.get('typed_text', '') if restore_state else ''
        self.word_edit_var.set(typed)
        if restore_state and restore_state.get('error'):
            self._mark_word_error()
        else:
            self._clear_word_error()
        self.word_entry.focus_set()
        self.word_entry.icursor(tk.END)

    def _render_confirmed_label(self, pinyin_visible: bool) -> None:
        """Show the static Palavra label with the given pinyin visibility."""
        self._word_error = False
        self.word_entry.pack_forget()
        self.word_confirm_btn.pack_forget()
        self.word_display_label.config(text=self._current_word)
        self.word_display_label.pack(side="left", padx=(10, 0))

        self._pinyin_visible = pinyin_visible
        self._refresh_pinyin_label()
        self.pinyin_toggle_btn.config(state="normal")

    def _show_word_confirmed(self) -> None:
        """Called the instant the typed guess matches — the reward moment:
        reveal pinyin regardless of any earlier preference for this word."""
        self._render_confirmed_label(pinyin_visible=True)
        self._persist_word_state(
            confirmed=True, typed_text=self._current_word, error=False,
            pinyin_visible=True,
        )

    def is_audio_shortcut_enabled(self) -> bool:
        """Whether the 's' pronunciation shortcut should fire right now.

        Blocked while the currently selected word's Palavra quiz hasn't been
        answered correctly yet, so hearing the audio can't be used to skip
        the recall check.
        """
        if not self.visible or self._current_word_id is None:
            return True
        state = self._word_states.get(self._current_word_id)
        return bool(state and state.get('confirmed'))

    # ------------------------------------------------------------------ #
    #  Pinyin field: hidden by default, eye-toggle reveals it              #
    # ------------------------------------------------------------------ #

    def _toggle_pinyin_visibility(self) -> None:
        self._pinyin_visible = not self._pinyin_visible
        self._refresh_pinyin_label()
        self._persist_word_state(pinyin_visible=self._pinyin_visible)

    def _refresh_pinyin_label(self) -> None:
        if self._pinyin_visible:
            self.labels["pinyin"].config(text=self._pinyin_value or "N/A")
            self.pinyin_toggle_btn.config(text="🙈")
        else:
            masked = "•" * 8 if self._pinyin_value else ""
            self.labels["pinyin"].config(text=masked)
            self.pinyin_toggle_btn.config(text="👁")

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def show(self, word_data: Dict, focus_character: Optional[int] = None,
             word_id: Optional[int] = None) -> None:
        if not self.visible:
            self.paned.insert(0, self.frame, weight=3)
            self.visible = True
            self.frame.after_idle(self._apply_left_sash)
            # add="+" so this panel's handlers don't clobber the right panel's.
            self.paned.bind("<ButtonRelease-1>", self._on_sash_released, add="+")
            self.paned.bind("<Configure>", self._on_paned_configure, add="+")

        word = word_data['word']
        self.search_var.set(word)
        self._load_word(word, focus_character=focus_character, word_id=word_id)

    def hide(self) -> None:
        if not self.visible:
            return
        self._save_sash_fraction()
        self.paned.remove(self.frame)
        self.visible = False

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #

    def _search(self) -> None:
        term = self.search_var.get().strip()
        if not term or term == "Buscar palavra…":
            return
        if not self.visible:
            self.paned.insert(0, self.frame, weight=3)
            self.visible = True
            self.frame.after_idle(self._apply_left_sash)
            self.paned.bind("<ButtonRelease-1>", self._on_sash_released, add="+")
            self.paned.bind("<Configure>", self._on_paned_configure, add="+")

        if any(is_chinese_char(ch) for ch in term):
            self._load_word(term)
        else:
            self._show_search_results(term)

    def _load_word(self, word: str, focus_character: Optional[int] = None,
                   word_id: Optional[int] = None) -> None:
        self._request_seq += 1
        token = self._request_seq
        self._focus_character = focus_character

        self._current_word = word
        self._current_word_id = word_id
        state = self._word_states.get(word_id) if word_id is not None else None
        if state and state.get('confirmed'):
            self._render_confirmed_label(pinyin_visible=state.get('pinyin_visible', True))
        else:
            self._enter_word_edit_mode(restore_state=state)

        self._pinyin_value = "…"
        self._refresh_pinyin_label()
        for key in ("calls", "confidence", "translations"):
            self.labels[key].config(text="…")
        self._reset_tabs(loading_text="Carregando…")

        self.tasks.submit(
            lambda: self.api.fetch_word_info(word),
            lambda info: self._apply_word_info(token, word, info),
        )

    def _apply_word_info(self, token: int, word: str, info) -> None:
        if token != self._request_seq:
            return  # a newer load/search superseded this one

        if info:
            # The API may return a normalized form of the word; keep the quiz
            # target in sync with whatever ended up being displayed.
            self._current_word = info.get('word', word)

            pinyin = info.get('pinyin', '') or ''
            if isinstance(pinyin, list):
                pinyin = ' '.join(pinyin)
            self._pinyin_value = pinyin
            self._refresh_pinyin_label()

            self.labels["calls"].config(text=str(info.get('calls', 'N/A')))
            self.labels["confidence"].config(text=str(info.get('confidence_level', 'N/A')))
            translations = info.get('translations') or []
            if not translations:
                primary = info.get('translation', '')
                translations = [primary] if primary else []
            self.labels["translations"].config(
                text='; '.join(translations) if translations else 'N/A'
            )
        else:
            self._pinyin_value = ''
            self._refresh_pinyin_label()
            self.labels["calls"].config(text="N/A")
            self.labels["confidence"].config(text="N/A")
            self.labels["translations"].config(text='N/A')

        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        self.trees.clear()

        for ch in list(word):
            if is_chinese_char(ch):
                self._add_char_tab(ch, token)

        # Select the focused character tab if specified
        if self._focus_character is not None and self._focus_character < len(self.notebook.tabs()):
            self.notebook.select(self._focus_character)

    def _reset_tabs(self, loading_text: Optional[str] = None) -> None:
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        self.trees.clear()
        if loading_text:
            placeholder = ttk.Frame(self.notebook)
            self.notebook.add(placeholder, text="…")
            ttk.Label(placeholder, text=loading_text).pack(pady=20)

    def _show_search_results(self, term: str) -> None:
        self._request_seq += 1
        token = self._request_seq

        for label in self.labels.values():
            label.config(text="")
        self._pinyin_value = ''
        self._refresh_pinyin_label()
        self._current_word = None
        self._current_word_id = None
        self._enter_word_edit_mode()

        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        self.trees.clear()
        self._search_results = []

        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Resultados")

        filter_row = ttk.Frame(tab)
        filter_row.pack(fill="x", padx=5, pady=(5, 0))

        ttk.Label(filter_row, text="Confidence:", font=("Arial", 10)).pack(side="left")
        self.confidence_filter = ttk.Combobox(
            filter_row, state="readonly", width=6, values=["Todos"],
        )
        self.confidence_filter.set("Todos")
        self.confidence_filter.pack(side="left", padx=(4, 12))
        self.confidence_filter.bind("<<ComboboxSelected>>",
                                    lambda _e: self._populate_results_tree())

        ttk.Label(filter_row, text="Tom:", font=("Arial", 10)).pack(side="left")
        self.tone_filter = ttk.Combobox(
            filter_row, state="readonly", width=6, values=["Todos"],
        )
        self.tone_filter.set("Todos")
        self.tone_filter.pack(side="left", padx=(4, 0))
        self.tone_filter.bind("<<ComboboxSelected>>",
                              lambda _e: self._populate_results_tree())

        table_frame = ttk.Frame(tab)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)

        tree = ttk.Treeview(
            table_frame,
            columns=("pinyin", "translation", "calls", "confidence", "tone"),
            show="tree headings", height=15,
        )
        tree.heading("#0", text="Palavra")
        tree.heading("pinyin", text="Pinyin")
        tree.heading("translation", text="Tradução")
        tree.heading("calls", text="Calls")
        tree.heading("confidence", text="Confidence")
        tree.heading("tone", text="Tom")
        tree.column("#0", width=80, anchor="w")
        tree.column("pinyin", width=100, anchor="w")
        tree.column("translation", width=150, anchor="w")
        tree.column("calls", width=60, anchor="center")
        tree.column("confidence", width=80, anchor="center")
        tree.column("tone", width=60, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tree.bind("<Double-Button-1>", self._on_result_double_click)
        self.trees["__results__"] = tree
        tree.insert("", "end", text="Carregando…", values=("", "", "", "", ""))

        self.tasks.submit(
            lambda: self.api.search(term),
            lambda results: self._apply_search_results(token, results),
        )

    def _apply_search_results(self, token: int, results) -> None:
        if token != self._request_seq:
            return
        results = results or []
        results.sort(key=lambda x: x.get('calls', 0), reverse=True)
        self._search_results = results

        confidences = sorted({str(r.get('confidence_level', ''))
                              for r in results if r.get('confidence_level') not in (None, '')})
        tones = sorted({str(r.get('tone_pair', ''))
                       for r in results if r.get('tone_pair') not in (None, '')})
        try:
            self.confidence_filter.config(values=["Todos"] + confidences)
            self.tone_filter.config(values=["Todos"] + tones)
        except tk.TclError:
            return

        self._populate_results_tree()

    def _populate_results_tree(self) -> None:
        tree = self.trees.get("__results__")
        if tree is None:
            return
        tree.delete(*tree.get_children())

        conf = self.confidence_filter.get()
        tone = self.tone_filter.get()

        rows = [
            item for item in self._search_results
            if (conf == "Todos" or str(item.get('confidence_level', '')) == conf)
            and (tone == "Todos" or str(item.get('tone_pair', '')) == tone)
        ]

        if rows:
            for item in rows:
                tree.insert("", "end",
                            text=item.get('word', ''),
                            values=(
                                item.get('pinyin', ''),
                                item.get('translation', ''),
                                item.get('calls', ''),
                                item.get('confidence_level', ''),
                                item.get('tone_pair', ''),
                            ))
        else:
            tree.insert("", "end",
                        text="Nenhum resultado",
                        values=("", "", "", "", ""))

    def _on_result_double_click(self, event) -> None:
        tree = event.widget
        sel = tree.selection()
        if not sel:
            return
        word = tree.item(sel[0])['text']
        if word and word != "Nenhum resultado":
            self.search_var.set(word)
            self._load_word(word)

    def _show_placeholder(self) -> None:
        for label in self.labels.values():
            label.config(text="")
        self._pinyin_value = ''
        self._refresh_pinyin_label()
        self._current_word = None
        self._current_word_id = None
        self._enter_word_edit_mode()
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        placeholder = ttk.Frame(self.notebook)
        self.notebook.add(placeholder, text="Selecione")
        ttk.Label(placeholder,
                  text="Clique em uma palavra para ver palavras relacionadas"
                  ).pack(pady=20)

    def _on_sash_released(self, _event) -> None:
        self._save_sash_fraction()

    def _on_paned_configure(self, _event) -> None:
        # Reapply the sash from the stored fraction against the paned's CURRENT
        # width. This keeps proportions stable across window resizes and fixes
        # the initial layout when winfo_width() was still stale at first show.
        if self.visible:
            self._apply_left_sash()

    def _save_sash_fraction(self) -> None:
        try:
            pos = self.paned.sashpos(0)
            w = self.paned.winfo_width()
            if w > 100 and pos > 0:
                self.last_sash_position = pos
                self.config.set_sash("left", pos / w)
        except (tk.TclError, AttributeError):
            pass

    def _apply_left_sash(self) -> None:
        try:
            w = self.paned.winfo_width()
            if w > 100:
                fraction = self.config.sash_left if self.config.sash_left else 0.50
                self.paned.sashpos(0, int(w * fraction))
        except (tk.TclError, AttributeError):
            pass

    def _add_char_tab(self, character: str, token: int) -> None:
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=character)

        table_frame = ttk.Frame(tab)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)

        tree = ttk.Treeview(
            table_frame,
            columns=("pinyin", "translation", "calls", "confidence"),
            show="tree headings", height=15,
        )
        tree.heading("#0", text="Palavra")
        tree.heading("pinyin", text="Pinyin")
        tree.heading("translation", text="Tradução")
        tree.heading("calls", text="Calls")
        tree.heading("confidence", text="Confidence")
        tree.column("#0", width=80, anchor="w")
        tree.column("pinyin", width=100, anchor="w")
        tree.column("translation", width=150, anchor="w")
        tree.column("calls", width=60, anchor="center")
        tree.column("confidence", width=80, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tree.bind("<Double-Button-1>", self._on_related_double_click)
        self.trees[character] = tree
        tree.insert("", "end", text="Carregando…", values=("", "", "", ""))

        self.tasks.submit(
            lambda: self.api.search(character),
            lambda results: self._fill_char_tree(token, tree, results),
        )

    def _fill_char_tree(self, token: int, tree, results) -> None:
        if token != self._request_seq:
            return
        try:
            tree.delete(*tree.get_children())
        except tk.TclError:
            return  # tab was destroyed
        if results:
            results.sort(key=lambda x: x.get('calls', 0), reverse=True)
            for item in results:
                tree.insert("", "end",
                            text=item.get('word', ''),
                            values=(
                                item.get('pinyin', ''),
                                item.get('translation', ''),
                                item.get('calls', ''),
                                item.get('confidence_level', ''),
                            ))
        else:
            tree.insert("", "end",
                        text="Nenhuma palavra relacionada",
                        values=("", "", "", ""))

    def _on_related_double_click(self, event) -> None:
        tree = event.widget
        sel = tree.selection()
        if not sel:
            return
        word = tree.item(sel[0])['text']
        if word:
            self.on_related_double_click(word)
