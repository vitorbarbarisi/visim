"""File menubar with recent files submenu."""
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Callable


class MenuBuilder:
    def __init__(self, root: tk.Tk, config,
                 on_open_csv: Callable[[str], None],
                 on_new_csv: Callable[[], None]):
        self.root = root
        self.config = config
        self.on_open_csv = on_open_csv
        self.on_new_csv = on_new_csv

        self.menubar = tk.Menu(root)
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(label="Novo…", command=self.on_new_csv)
        self.file_menu.add_command(label="Abrir…", command=self._open_dialog)
        self.recent_menu = tk.Menu(self.file_menu, tearoff=0)
        self.file_menu.add_cascade(label="Reabrir recente", menu=self.recent_menu)
        self.populate_recent()
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Sair", command=root.quit)
        self.menubar.add_cascade(label="Arquivo", menu=self.file_menu)
        root.config(menu=self.menubar)

    def populate_recent(self) -> None:
        try:
            self.recent_menu.delete(0, "end")
        except Exception:
            return
        if not self.config.recent_csv_paths:
            self.recent_menu.add_command(label="Vazio", state="disabled")
        else:
            for p in self.config.recent_csv_paths:
                self.recent_menu.add_command(
                    label=os.path.basename(p),
                    command=lambda p=p: self._reopen(p),
                )
        self.recent_menu.add_separator()
        self.recent_menu.add_command(label="Limpar lista", command=self._clear)

    def _open_dialog(self) -> None:
        filetypes = [("CSV", "*.csv"), ("Todos os arquivos", "*.*")]
        files_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "files")
        initial = files_dir if os.path.isdir(files_dir) else os.path.dirname(__file__)
        path = filedialog.askopenfilename(title="Abrir CSV",
                                          initialdir=initial,
                                          filetypes=filetypes)
        if path:
            self.on_open_csv(os.path.abspath(path))

    def _reopen(self, path: str) -> None:
        if not path or not os.path.isfile(path):
            self.config.remove_recent(path)
            self.populate_recent()
            messagebox.showwarning(
                "Arquivo não encontrado",
                "O arquivo recente não está mais disponível.",
            )
            return
        self.on_open_csv(os.path.abspath(path))

    def _clear(self) -> None:
        self.config.clear_recent()
        self.populate_recent()
