"""Left side panel: word details + related-words tabs per character."""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Optional

from chinese_utils import is_chinese_char


class WordInfoPanel:
    def __init__(self, paned: ttk.PanedWindow, api_client,
                 on_related_double_click: Callable[[str], None]):
        self.paned = paned
        self.api = api_client
        self.on_related_double_click = on_related_double_click

        self.frame = ttk.Frame(paned, relief="solid", borderwidth=1)
        self.visible = False
        self.last_sash_position: Optional[int] = None

        self._build()

    def _build(self) -> None:
        header = ttk.Frame(self.frame)
        header.pack(fill="x", padx=5, pady=5)
        self.title_label = ttk.Label(header, text="Informações da Palavra",
                                     font=("Arial", 12, "bold"))
        self.title_label.pack(side="left")
        ttk.Button(header, text="×", width=3, command=self.hide).pack(side="right")

        content = ttk.Frame(self.frame)
        content.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        info = ttk.LabelFrame(content, text="Detalhes", padding=10)
        info.pack(fill="x", pady=(0, 10))

        self.labels: Dict[str, ttk.Label] = {}
        for key, label_text in (
            ("word", "Palavra:"),
            ("calls", "Calls:"),
            ("confidence", "Confidence Level:"),
            ("translations", "Traduções:"),
        ):
            row = ttk.Frame(info)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=label_text, font=("Arial", 10, "bold")).pack(side="left")
            value = ttk.Label(row, text="", font=("Arial", 10))
            value.pack(side="left", padx=(10, 0))
            self.labels[key] = value

        related = ttk.LabelFrame(content, text="Palavras Relacionadas", padding=10)
        related.pack(fill="both", expand=True)
        self.notebook = ttk.Notebook(related)
        self.notebook.pack(fill="both", expand=True)
        self.trees: Dict[str, ttk.Treeview] = {}

        self._show_placeholder()

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

    def show(self, word_data: Dict) -> None:
        if not self.visible:
            self.paned.insert(0, self.frame, weight=1)
            self.visible = True
            self.frame.after_idle(self._set_initial_sash)

        self.title_label.config(text=f"Informações: {word_data['word']}")

        word = word_data['word']
        info = self.api.fetch_word_info(word)
        if info:
            self.labels["word"].config(text=info.get('word', word))
            self.labels["calls"].config(text=str(info.get('calls', 'N/A')))
            self.labels["confidence"].config(text=str(info.get('confidence_level', 'N/A')))
            translations = info.get('translation', '')
            if isinstance(translations, list):
                translations = '; '.join(translations)
            self.labels["translations"].config(
                text=f'"{translations}"' if translations else 'N/A'
            )
        else:
            self.labels["word"].config(text=word)
            self.labels["calls"].config(text="N/A")
            self.labels["confidence"].config(text="N/A")
            self.labels["translations"].config(
                text=f'"{word_data.get("translation", "N/A")}"'
            )

        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        self.trees.clear()

        for ch in list(word):
            if is_chinese_char(ch):
                self._add_char_tab(ch)

    def hide(self) -> None:
        if not self.visible:
            return
        try:
            self.last_sash_position = self.paned.sashpos(0)
        except tk.TclError:
            pass
        self.paned.remove(self.frame)
        self.visible = False

    def _set_initial_sash(self) -> None:
        try:
            top = self.frame.winfo_toplevel()
            w = top.winfo_width()
            if w > 100:
                self.paned.sashpos(0, int(w * 0.2))
        except (tk.TclError, AttributeError):
            pass

    def _add_char_tab(self, character: str) -> None:
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

        results = self.api.search_related_words(character)
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
