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

        self.labels: Dict[str, ttk.Label] = {}
        for key, label_text in (
            ("word", "Palavra:"),
            ("pinyin", "Pinyin:"),
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
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def show(self, word_data: Dict, focus_character: Optional[int] = None) -> None:
        if not self.visible:
            self.paned.insert(0, self.frame, weight=2)
            self.visible = True
            self.frame.after_idle(self._set_initial_sash)
            self.paned.bind("<ButtonRelease-1>", self._on_sash_released)

        word = word_data['word']
        self.search_var.set(word)
        self._load_word(word, focus_character=focus_character)

    def hide(self) -> None:
        if not self.visible:
            return
        try:
            pos = self.paned.sashpos(0)
            self.last_sash_position = pos
            self.config.set_sash("left", pos)
        except tk.TclError:
            pass
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
            self.paned.insert(0, self.frame, weight=1)
            self.visible = True
            self.frame.after_idle(self._set_initial_sash)

        if any(is_chinese_char(ch) for ch in term):
            self._load_word(term)
        else:
            self._show_search_results(term)

    def _load_word(self, word: str, focus_character: Optional[int] = None) -> None:
        self._request_seq += 1
        token = self._request_seq
        self._focus_character = focus_character

        self.labels["word"].config(text=word)
        for key in ("pinyin", "calls", "confidence", "translations"):
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
            self.labels["word"].config(text=info.get('word', word))

            pinyin = info.get('pinyin', '') or ''
            if isinstance(pinyin, list):
                pinyin = ' '.join(pinyin)
            self.labels["pinyin"].config(text=pinyin if pinyin else 'N/A')

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
            self.labels["word"].config(text=word)
            self.labels["pinyin"].config(text='N/A')
            self.labels["calls"].config(text="N/A")
            self.labels["confidence"].config(text="N/A")
            self.labels["translations"].config(text='N/A')

        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        self.trees.clear()

        char_index = 0
        for idx, ch in enumerate(list(word)):
            if is_chinese_char(ch):
                self._add_char_tab(ch, token)
                if idx == self._focus_character:
                    # Open this tab once all tabs are created
                    # We'll select it after the loop
                    pass
                char_index += 1

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
        self.labels["word"].config(text=f'Resultados para "{term}"')

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
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        placeholder = ttk.Frame(self.notebook)
        self.notebook.add(placeholder, text="Selecione")
        ttk.Label(placeholder,
                  text="Clique em uma palavra para ver palavras relacionadas"
                  ).pack(pady=20)
        self.labels["word"].config(text="Selecione uma palavra")

    def _on_sash_released(self, _event) -> None:
        try:
            pos = self.paned.sashpos(0)
            self.last_sash_position = pos
            self.config.set_sash("left", pos)
        except tk.TclError:
            pass

    def _set_initial_sash(self) -> None:
        try:
            top = self.frame.winfo_toplevel()
            w = top.winfo_width()
            if w > 100:
                pos = self.config.sash_left if self.config.sash_left else int(w * 0.40)
                self.paned.sashpos(0, pos)
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
