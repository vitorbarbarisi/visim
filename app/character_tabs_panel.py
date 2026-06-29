"""Right side panel: per-character tabs with details and stroke-order buttons."""
import re
import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, Optional

import tkinterweb

from chinese_utils import is_chinese_char

_PLACEHOLDER_HTML = """
<html>
<head>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 20px;
            text-align: center;
            background-color: #f8f9fa;
        }
        h2 { color: #495057; margin-bottom: 15px; }
        p { color: #6c757d; line-height: 1.6; }
        .icon { font-size: 48px; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="icon">📝</div>
    <h2>Caracteres</h2>
    <p>Clique em uma palavra chinesa no canvas para ver cada caractere em abas separadas.</p>
    <p>Cada aba mostrará informações detalhadas sobre um caractere individual.</p>
</body>
</html>
"""


class CharacterTabsPanel:
    def __init__(self, paned: ttk.PanedWindow, api_client, webview_launcher, config,
                 tasks, on_chinese_click: Callable[[str], None]):
        self.paned = paned
        self.api = api_client
        self.webview = webview_launcher
        self.config = config
        self.tasks = tasks
        self.on_chinese_click = on_chinese_click

        self.frame = ttk.Frame(paned, relief="solid", borderwidth=1)
        self.visible = False
        self.last_sash_position: Optional[int] = None
        self.left_visible_ref: Callable[[], bool] = lambda: False
        self._request_seq = 0  # bumped per show() to discard stale async results
        self._focus_character: Optional[int] = None  # which character tab to open by default

        self._build()

    def set_left_visible_ref(self, ref: Callable[[], bool]) -> None:
        self.left_visible_ref = ref

    def _build(self) -> None:
        header = ttk.Frame(self.frame)
        header.pack(fill="x", padx=5, pady=5)
        self.title_label = ttk.Label(header, text="Caracteres",
                                     font=("Arial", 12, "bold"))
        self.title_label.pack(side="left")
        ttk.Button(header, text="×", width=3, command=self.hide).pack(side="right")

        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self._show_placeholder()

    def _show_placeholder(self) -> None:
        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)
        placeholder = ttk.Frame(self.notebook)
        self.notebook.add(placeholder, text="Selecione uma palavra")
        try:
            viewer = tkinterweb.HtmlFrame(placeholder, messages_enabled=False)
            viewer.pack(fill="both", expand=True, padx=10, pady=10)
            viewer.load_html(_PLACEHOLDER_HTML)
        except Exception as e:
            print(f"Error creating placeholder viewer: {e}")
            text = tk.Text(placeholder, wrap="word", padx=15, pady=15)
            text.pack(fill="both", expand=True)
            text.insert(
                "1.0",
                "Clique em uma palavra chinesa para analisar cada caractere individualmente.",
            )
            text.config(state="disabled")

    def show(self, word_data: Dict, focus_character: Optional[int] = None) -> None:
        if not self.visible:
            self.paned.add(self.frame, weight=1)
            self.visible = True
            self.frame.after_idle(self._restore_or_set_sash)
            self.paned.bind("<ButtonRelease-1>", self._on_sash_released)

        self.title_label.config(text=word_data['word'])

        self._request_seq += 1
        token = self._request_seq
        self._focus_character = focus_character

        for tab_id in self.notebook.tabs():
            self.notebook.forget(tab_id)

        word = word_data['word']
        chars = list(word)
        print(f"Creating tabs for characters: {chars}")
        for i, ch in enumerate(chars):
            self._create_character_tab(ch, i, word_data, token)

        # Select the focused character tab if specified
        if self._focus_character is not None and self._focus_character < len(self.notebook.tabs()):
            self.notebook.select(self._focus_character)

    def hide(self) -> None:
        if not self.visible:
            return
        try:
            sash_idx = 1 if self.left_visible_ref() else 0
            pos = self.paned.sashpos(sash_idx)
            self.last_sash_position = pos
            self.config.set_sash("right", pos)
        except tk.TclError:
            pass
        self.paned.remove(self.frame)
        self.visible = False

    def _on_sash_released(self, _event) -> None:
        try:
            sash_idx = 1 if self.left_visible_ref() else 0
            pos = self.paned.sashpos(sash_idx)
            self.last_sash_position = pos
            self.config.set_sash("right", pos)
        except tk.TclError:
            pass

    def _restore_or_set_sash(self) -> None:
        sash_idx = 1 if self.left_visible_ref() else 0
        if self.last_sash_position is not None:
            try:
                self.paned.sashpos(sash_idx, self.last_sash_position)
            except tk.TclError:
                pass
            return
        try:
            top = self.frame.winfo_toplevel()
            w = top.winfo_width()
            if w > 100:
                pos = self.config.sash_right if self.config.sash_right else int(w * 0.83)
                self.paned.sashpos(sash_idx, pos)
        except (tk.TclError, AttributeError):
            pass

    # --- Per-character tab ---

    def _create_character_tab(self, character: str, index: int,
                              word_data: Dict, token: int) -> None:
        char_frame = ttk.Frame(self.notebook)
        self.notebook.add(char_frame, text=character)

        char_url = (
            "https://stroke-order.learningweb.moe.edu.tw/searchW.jsp?"
            f"ID2=1&WORD={character}"
        )

        content_frame = ttk.Frame(char_frame)
        content_frame.pack(fill="both", expand=True, padx=5, pady=5)

        text = tk.Text(content_frame, wrap="word", font=("Arial", 12),
                       bg="white", fg="#212529", relief="solid",
                       borderwidth=1, padx=15, pady=15)
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._configure_tags(text)
        text.config(state="normal")
        text.insert("end", f"{character}\n", "character")
        text.insert("end", "Carregando…\n", "info")
        text.config(state="disabled")

        # Character info (and possible enrich) is slow — fetch off the main thread.
        self.tasks.submit(
            lambda: self.api.fetch_character_info(character),
            lambda data: self._populate_char_text(token, text, character, data),
        )

        def on_mousewheel(event):
            text.yview_scroll(int(-1 * (event.delta / 120)), "units")
        text.bind("<MouseWheel>", on_mousewheel)
        text.bind("<Button-4>", on_mousewheel)
        text.bind("<Button-5>", on_mousewheel)

        button_frame = ttk.Frame(char_frame)
        button_frame.pack(fill="x", padx=10, pady=(5, 10))

        copy_button = ttk.Button(button_frame, text="Copiar")

        def copy_to_clipboard():
            try:
                self.frame.clipboard_clear()
                self.frame.clipboard_append(character)
                try:
                    copy_button.config(text="Copiado!")
                    self.frame.after(800, lambda: copy_button.config(text="Copiar"))
                except Exception:
                    pass
            except Exception as e:
                print(f"Error copying character to clipboard: {e}")

        copy_button.configure(command=copy_to_clipboard)
        copy_button.pack(pady=2)

        def on_copy_shortcut(event):
            try:
                copy_to_clipboard()
            except Exception:
                pass
            return "break"
        text.bind("<Control-c>", on_copy_shortcut)
        text.bind("<Command-c>", on_copy_shortcut)

        ttk.Separator(button_frame, orient="horizontal").pack(fill="x", pady=(5, 10))
        ttk.Label(button_frame, text="Ordem de Traços - Taiwan MOE",
                  font=("Arial", 10, "bold"), foreground="#007bff").pack(pady=(0, 5))

        ttk.Button(button_frame, text="Abrir Janela de Traços",
                   command=lambda: self.webview.open_webview(character, char_url)
                   ).pack(pady=2)
        ttk.Button(button_frame, text="Abrir no Safari",
                   command=lambda: self.webview.open_safari(char_url)
                   ).pack(pady=2)

        ttk.Label(button_frame,
                  text="Use 'Janela de Traços' (webview) ou 'Safari' para visualizar a ordem dos traços",
                  font=("Arial", 9), foreground="#868e96", wraplength=250
                  ).pack(pady=(5, 0))

    def _populate_char_text(self, token: int, text: tk.Text,
                            character: str, character_data) -> None:
        if token != self._request_seq:
            return  # a newer word selection superseded this tab
        try:
            text.config(state="normal")
            text.delete("1.0", "end")
        except tk.TclError:
            return  # tab was destroyed

        if character_data:
            text.insert("end", f"{character}\n", "character")
            text.insert(
                "end",
                f"Frequência: {character_data.get('frequency', 'N/A')} | "
                f"Consultas: {character_data.get('calls', 'N/A')}\n\n",
                "stats",
            )
            text.insert("end",
                        f"{character_data.get('decomposition', 'N/A')}\n",
                        "decomp_title")
            text.insert("end",
                        f"{character_data.get('decomposition_meaning', 'N/A')}\n\n",
                        "decomp_text")
            self._insert_formatted(text,
                                   character_data.get('meaning', 'N/A') + "\n\n",
                                   "meaning")
            text.insert(
                "end",
                f"{character_data.get('related_words', 'Nenhuma palavra relacionada encontrada')}\n\n",
                "related",
            )
            appears_in = character_data.get('appears_in', '')
            if appears_in:
                text.insert("end", "Aparece em:\n", "appears_title")
                text.insert("end", f"{appears_in}\n\n", "appears_text")
        else:
            text.insert("end", f"{character}\n", "character")
            text.insert("end", "⚠️ Informações da API não disponíveis\n\n", "error")
            text.insert("end",
                        "Verifique se a API está executando em http://localhost:7998",
                        "info")

        try:
            self._make_chinese_clickable(text)
        except Exception as e:
            print(f"Error tagging Chinese characters as clickable: {e}")

        text.config(state="disabled")

    def _configure_tags(self, text: tk.Text) -> None:
        text.tag_configure("character", font=("Arial", 36, "bold"),
                           foreground="#2c3e50", justify="center")
        text.tag_configure("stats", font=("Arial", 10),
                           foreground="#6c757d", justify="center")
        text.tag_configure("decomp_title", font=("Arial", 14, "bold"),
                           foreground="#495057")
        text.tag_configure("decomp_text", font=("Arial", 12),
                           foreground="#212529")
        text.tag_configure("meaning", font=("Arial", 12), foreground="#212529")
        text.tag_configure("appears_title", font=("Arial", 11, "bold"),
                           foreground="#495057")
        text.tag_configure("appears_text", font=("Arial", 12), foreground="#212529")
        text.tag_configure("meaning_bold", font=("Arial", 12, "bold"),
                           foreground="#495057")
        text.tag_configure("related", font=("Arial", 11), foreground="#212529")
        text.tag_configure("error", font=("Arial", 12, "bold"),
                           foreground="#dc3545", justify="center")
        text.tag_configure("info", font=("Arial", 10),
                           foreground="#6c757d", justify="center")

    def _insert_formatted(self, text_widget: tk.Text, text: str,
                          base_tag: str) -> None:
        parts = re.split(r'\*\*(.*?)\*\*', text)
        for i, part in enumerate(parts):
            if not part:
                continue
            tag = base_tag if i % 2 == 0 else f"{base_tag}_bold"
            text_widget.insert("end", part, tag)

    def _make_chinese_clickable(self, text_widget: tk.Text) -> None:
        try:
            text_widget.tag_configure("hanzi_click", underline=0)
        except Exception:
            pass
        content = text_widget.get("1.0", "end-1c")
        line = 1
        col = 0
        run_start = None
        for ch in content:
            if ch == "\n":
                if run_start is not None:
                    text_widget.tag_add(
                        "hanzi_click",
                        f"{run_start[0]}.{run_start[1]}",
                        f"{line}.{col}",
                    )
                    run_start = None
                line += 1
                col = 0
                continue
            if is_chinese_char(ch):
                if run_start is None:
                    run_start = (line, col)
            elif run_start is not None:
                text_widget.tag_add(
                    "hanzi_click",
                    f"{run_start[0]}.{run_start[1]}",
                    f"{line}.{col}",
                )
                run_start = None
            col += 1
        if run_start is not None:
            try:
                text_widget.tag_add(
                    "hanzi_click",
                    f"{run_start[0]}.{run_start[1]}",
                    f"{line}.{col}",
                )
            except Exception:
                pass

        def on_click(event):
            try:
                idx = event.widget.index(f"@{event.x},{event.y}")
                word = self._extract_chinese_at(event.widget, idx)
                if word and word.strip():
                    self.on_chinese_click(word.strip())
            except Exception as e:
                print(f"Error handling hanzi click: {e}")

        text_widget.tag_bind("hanzi_click", "<Button-1>", on_click)
        text_widget.tag_bind("hanzi_click", "<Enter>",
                             lambda e: e.widget.config(cursor="hand2"))
        text_widget.tag_bind("hanzi_click", "<Leave>",
                             lambda e: e.widget.config(cursor="xterm"))

    def _extract_chinese_at(self, text_widget: tk.Text, index: str) -> str:
        try:
            ch = text_widget.get(index, f"{index} +1c")
            if not ch or not is_chinese_char(ch):
                return ""
            start = index
            while True:
                prev = text_widget.index(f"{start} -1c")
                prev_ch = text_widget.get(prev, f"{prev} +1c")
                if not prev_ch or not is_chinese_char(prev_ch) or prev == start:
                    break
                start = prev
            end = text_widget.index(f"{index} +1c")
            while True:
                next_ch = text_widget.get(end, f"{end} +1c")
                if not next_ch or not is_chinese_char(next_ch):
                    break
                end = text_widget.index(f"{end} +1c")
            return text_widget.get(start, end)
        except Exception:
            return ""
