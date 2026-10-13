"""Modal dialog for creating a new CSV from a pasted list of mandarin words."""
import datetime
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import List, Optional

_QUOTE_CHARS = '"\'“”‘’「」『』'

MIN_COLUMNS = 1
MAX_COLUMNS = 9


def parse_word_list(raw_text: str) -> List[str]:
    """Return one word per line, with quotes stripped and blank lines dropped.

    Examples:
      '"著"\n"當"' -> ['著', '當']  (quoted)
      '著\n當'    -> ['著', '當']    (unquoted)
      '著\n\n當'  -> ['著', '當']    (blank line ignored)
      '“著”' -> ['著']             (tipographic quotes)
    """
    words: List[str] = []
    for line in (raw_text or "").splitlines():
        cleaned = ''.join(ch for ch in line if ch not in _QUOTE_CHARS).strip()
        if cleaned:
            words.append(cleaned)
    return words


def parse_columns(raw: str) -> Optional[int]:
    """Return the column count if `raw` is an integer within range, else None."""
    try:
        value = int((raw or "").strip())
    except ValueError:
        return None
    return value if MIN_COLUMNS <= value <= MAX_COLUMNS else None


@dataclass
class NewFileResult:
    words: List[str]
    file_name: str
    columns: int = 1


class NewFileDialog:
    def __init__(self, parent: tk.Misc):
        self.parent = parent
        self.result: Optional[NewFileResult] = None

        self.top = tk.Toplevel(parent)
        self.top.title("Novo arquivo")
        self.top.transient(parent)
        self.top.resizable(False, False)

        self._build()
        self._center_on_parent()

        self.top.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self._grab_when_visible()

    def _grab_when_visible(self) -> None:
        # On macOS Tk a grab taken before the window is actually mapped routes
        # events to nowhere: the mouse-up that ends a text selection is lost
        # (selection keeps following the pointer) and neither keys nor buttons
        # reach the dialog. Waiting for visibility first makes the grab stick
        # to a real window, and focus_force pulls keyboard focus off the main
        # window, which transient() alone does not do.
        try:
            self.top.wait_visibility()
            self.top.lift()
            self.top.focus_force()
            self.top.grab_set()
            self.text.focus_set()
        except tk.TclError:
            pass

    def ask(self) -> Optional[NewFileResult]:
        self.top.wait_window()
        return self.result

    # --- UI construction ---

    def _build(self) -> None:
        container = ttk.Frame(self.top, padding=12)
        container.pack(fill="both", expand=True)

        ttk.Label(container,
                  text="Palavras (uma por linha; aspas são ignoradas):"
                  ).pack(anchor="w")

        text_frame = ttk.Frame(container)
        text_frame.pack(fill="both", expand=True, pady=(4, 10))

        self.text = tk.Text(text_frame, width=40, height=12, wrap="word")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical",
                                  command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        self.text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Label(container, text="Nome do arquivo:").pack(anchor="w")
        self.name_var = tk.StringVar(
            value=datetime.date.today().strftime("%Y_%m_%d")
        )
        name_entry = ttk.Entry(container, textvariable=self.name_var, width=40)
        name_entry.pack(fill="x", pady=(4, 10))

        columns_row = ttk.Frame(container)
        columns_row.pack(fill="x", pady=(0, 10))
        ttk.Label(columns_row, text="Número de colunas:").pack(side="left")
        self.columns_var = tk.StringVar(value=str(MIN_COLUMNS))
        ttk.Spinbox(columns_row, from_=MIN_COLUMNS, to=MAX_COLUMNS,
                    textvariable=self.columns_var, width=3, state="readonly"
                    ).pack(side="left", padx=(6, 0))

        btns = ttk.Frame(container)
        btns.pack(fill="x")
        ttk.Button(btns, text="Cancelar", command=self._on_cancel
                   ).pack(side="right")
        ttk.Button(btns, text="Criar", command=self._on_create
                   ).pack(side="right", padx=(0, 6))

    def _center_on_parent(self) -> None:
        try:
            self.top.update_idletasks()
            pw = self.parent.winfo_width()
            ph = self.parent.winfo_height()
            px = self.parent.winfo_rootx()
            py = self.parent.winfo_rooty()
            w = self.top.winfo_reqwidth()
            h = self.top.winfo_reqheight()
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 3)
            self.top.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    # --- Event handlers ---

    def _on_create(self) -> None:
        raw_text = self.text.get("1.0", "end-1c")
        words = parse_word_list(raw_text)
        if not words:
            messagebox.showerror(
                "Lista vazia",
                "Adicione pelo menos uma palavra (uma por linha).",
                parent=self.top,
            )
            return

        name = (self.name_var.get() or "").strip()
        if not name:
            messagebox.showerror(
                "Nome inválido",
                "Informe um nome para o arquivo.",
                parent=self.top,
            )
            return
        if '/' in name or '\\' in name:
            messagebox.showerror(
                "Nome inválido",
                "O nome não pode conter '/' ou '\\'.",
                parent=self.top,
            )
            return

        columns = parse_columns(self.columns_var.get())
        if columns is None:
            messagebox.showerror(
                "Número de colunas inválido",
                f"Escolha entre {MIN_COLUMNS} e {MAX_COLUMNS} colunas.",
                parent=self.top,
            )
            return

        self.result = NewFileResult(words=words, file_name=name,
                                    columns=columns)
        self.top.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.top.destroy()
