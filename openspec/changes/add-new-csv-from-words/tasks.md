## 1. Word parsing utility

- [ ] 1.1 Add `parse_word_list(raw_text: str) -> list[str]` helper that strips whitespace per line, removes quote characters (`"`, `'`, `“`, `”`, `‘`, `’`, `「`, `」`, `『`, `』`) anywhere in the line, and drops empty lines (place in `app/new_file_dialog.py` as a module-level function).
- [ ] 1.2 Cover the parser with manual examples documented inline (e.g., quoted vs unquoted lines, blank lines, tipographic quotes).

## 2. NewFileDialog modal

- [ ] 2.1 Create `app/new_file_dialog.py` with class `NewFileDialog(parent: tk.Misc)`.
- [ ] 2.2 Build the modal in `__init__`: `tk.Toplevel` with title "Novo arquivo", `transient(parent)`, `grab_set()`, and centered on the parent.
- [ ] 2.3 Add a `tk.Text` widget for the word list (height ~12, width ~40), a `ttk.Entry` for the file name pre-filled with `datetime.date.today().strftime("%Y_%m_%d")`, and **Criar** / **Cancelar** buttons.
- [ ] 2.4 Implement `ask() -> Optional[NewFileResult]` that calls `wait_window` and returns the user input or `None` on cancel. Define `NewFileResult` as a `dataclass` or `NamedTuple` with `words: list[str]` and `file_name: str`.
- [ ] 2.5 Validate on **Criar**: at least one parsed word, file name non-empty and free of `/` and `\`. On failure, show `messagebox.showerror` and keep the modal open.

## 3. CSV generation

- [ ] 3.1 Add `app/new_csv_builder.py` exporting `DELTA = 300` and `def build_word_rows(words: list[str], delta: int = DELTA) -> list[dict]` returning rows in the canonical `WordCanvasApp` dict shape (`word`, `size=64`, `position={x:50, y:index*delta}`, `hasPinyin=True`, `hasTranslation=True`, `pinyin=''`, `translation=''`, `tonePair=''`).
- [ ] 3.2 Add `def resolve_new_csv_path(repo_root: str, file_name: str) -> str` that returns `<repo_root>/files/<name>.csv` (appending `.csv` if missing), creating `files/` if absent.

## 4. Wire-up in MenuBuilder

- [ ] 4.1 In `app/menu_builder.py`, accept a new constructor callback `on_new_csv: Callable[[], None]`.
- [ ] 4.2 Insert a `Novo…` command in the `Arquivo` menu **above** the existing `Abrir…` entry, bound to `on_new_csv`.

## 5. Wire-up in WordCanvasApp

- [ ] 5.1 In `app/word_canvas_app.py`, implement `_new_csv()` that opens `NewFileDialog`, then on confirmation: builds rows via `new_csv_builder.build_word_rows`, resolves the target path, prompts to overwrite if the file exists (`messagebox.askyesno`), writes via `CsvWordRepository(path).save(rows)`, and finally calls `self._open_csv(path)`.
- [ ] 5.2 Pass `on_new_csv=self._new_csv` to `MenuBuilder` in `_build_ui`.

## 6. Smoke test

- [ ] 6.1 Run the app, click **Arquivo → Novo…**, paste the example list from the proposal, confirm with default file name, and verify: file `files/<today>.csv` exists with the expected content, canvas shows all words at positions `50,0`, `50,300`, …, title reflects the new file, recent list contains the new path.
- [ ] 6.2 Verify the negative paths: empty word list shows an error and keeps the modal open; file name with `/` shows an error; overwriting an existing file asks for confirmation and respects the answer.
