#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Word Canvas — main orchestrator wiring panels, renderer, and services."""
import os
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List, Optional

from api_client import WordApiClient
from audio_service import AudioService
from canvas_renderer import CanvasRenderer
from character_tabs_panel import CharacterTabsPanel
from csv_repository import CsvWordRepository
from menu_builder import MenuBuilder
from new_csv_builder import build_word_rows, resolve_new_csv_path
from new_file_dialog import NewFileDialog
from task_runner import TaskRunner
from user_config import UserConfig
from webview_launcher import WebviewLauncher
from word_info_panel import WordInfoPanel


class WordCanvasApp:
    DEFAULT_CSV_REL = os.path.join("files", "words.csv")

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Word Canvas")
        self.root.geometry("1200x600")

        self.config = UserConfig()
        default_csv = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), self.DEFAULT_CSV_REL
        )
        self.current_csv_path = self.config.last_csv_path or default_csv
        self._update_title()

        self.words_data: List[Dict] = []
        self.selected_word_id: Optional[int] = None
        self.drag_data: Dict = {"x": 0, "y": 0, "item": None}

        self.api = WordApiClient()
        self.audio = AudioService()
        self.webview = WebviewLauncher()
        self.tasks = TaskRunner(self.root)

        self._build_ui()
        self._load_words(self.current_csv_path)
        self.renderer.draw_all(self.words_data)

    # --- UI ---

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.menu = MenuBuilder(
            self.root, self.config,
            on_open_csv=self._open_csv,
            on_new_csv=self._new_csv,
        )

        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.grid(row=0, column=0,
                             sticky=(tk.W, tk.E, tk.N, tk.S),
                             padx=5, pady=5)

        self.word_panel = WordInfoPanel(
            self.main_paned, self.api, self.config, self.tasks,
            on_related_double_click=self.add_word_to_canvas,
        )

        canvas_frame = ttk.Frame(self.main_paned)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_frame, bg="#f0f0f0",
                                scrollregion=(0, 0, 2000, 2000))
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL,
                            command=self.canvas.yview)
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.canvas.configure(yscrollcommand=vsb.set)
        hsb = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL,
                            command=self.canvas.xview)
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.canvas.configure(xscrollcommand=hsb.set)
        self.main_paned.add(canvas_frame, weight=2)

        self.web_panel = CharacterTabsPanel(
            self.main_paned, self.api, self.webview, self.config, self.tasks,
            on_chinese_click=self.add_word_to_canvas,
        )
        self.web_panel.set_left_visible_ref(lambda: self.word_panel.visible)

        self.renderer = CanvasRenderer(self.canvas)

        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.bind(seq, self._on_mousewheel)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        # Right-click context menu. Button-2 is the right button on macOS Tk;
        # Button-3 is right on X11/Windows — bind both to be safe.
        for seq in ("<Button-2>", "<Button-3>"):
            self.canvas.bind(seq, self._on_canvas_right_click)
        self.root.bind("<KeyPress>", self._on_key_press)
        self.root.bind("<Command-s>", self._on_play_audio_shortcut)
        self.root.focus_set()
        self.root.bind("<Configure>", self._on_resize)

    def _update_title(self) -> None:
        try:
            base = os.path.basename(self.current_csv_path) if self.current_csv_path else ""
            self.root.title(f"Word Canvas - Drag & Drop — {base}")
        except Exception:
            self.root.title("Word Canvas - Drag & Drop")

    # --- CSV handling ---

    def _open_csv(self, path: str) -> None:
        self.current_csv_path = os.path.abspath(path)
        print(f"Abrindo CSV: {self.current_csv_path}")
        self.config.add_recent(path)
        self.config.set_last_csv_path(self.current_csv_path)
        self._update_title()
        self.menu.populate_recent()
        self._load_words(self.current_csv_path)
        self.renderer.draw_all(self.words_data)

    def _new_csv(self) -> None:
        result = NewFileDialog(self.root).ask()
        if result is None:
            return

        repo_root = os.path.dirname(os.path.dirname(__file__))
        target_path = resolve_new_csv_path(repo_root, result.file_name)

        if os.path.exists(target_path):
            confirm = messagebox.askyesno(
                "Sobrescrever",
                f"O arquivo '{os.path.basename(target_path)}' já existe. Sobrescrever?",
            )
            if not confirm:
                return

        rows = build_word_rows(result.words)
        try:
            CsvWordRepository(target_path).save(rows)
        except Exception as e:
            messagebox.showerror("Erro ao salvar",
                                 f"Não foi possível criar o arquivo: {e}")
            return

        self._open_csv(target_path)

    def _load_words(self, path: str) -> None:
        self.current_csv_path = os.path.abspath(path)
        try:
            self.words_data = CsvWordRepository(self.current_csv_path).load()
            print(f"Loaded {len(self.words_data)} words from CSV: {self.current_csv_path}")
        except FileNotFoundError:
            messagebox.showerror("Error", f"CSV file not found: {self.current_csv_path}")
            self.words_data = []
        except Exception as e:
            messagebox.showerror("Error", f"Error loading CSV: {str(e)}")
            print(f"Detailed error: {e}")
            self.words_data = []

    def _save_words(self) -> None:
        try:
            print(f"Salvando CSV em: {self.current_csv_path}")
            CsvWordRepository(self.current_csv_path).save(self.words_data)
        except Exception as e:
            print(f"Error saving CSV: {str(e)}")

    # --- Canvas events ---

    def _on_mousewheel(self, event) -> None:
        # X11 reports wheel as Button-4/5; Windows uses ±120 multiples; macOS
        # reports small deltas (±1..3) that int(delta/120) truncated to zero,
        # which made wheel/trackpad scrolling a no-op on Mac.
        num = getattr(event, 'num', None)
        if num == 4:
            step = -1
        elif num == 5:
            step = 1
        elif abs(event.delta) >= 120:
            step = -int(event.delta / 120)
        elif event.delta:
            step = -1 if event.delta > 0 else 1
        else:
            return
        self.canvas.yview_scroll(step, "units")

    def _on_canvas_click(self, event) -> None:
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        word_id = self.renderer.find_word_at(x, y)
        if word_id is not None:
            char_index = self.renderer.find_character_at(word_id, x, y)
            self._select_word(word_id, focus_character=char_index)
            self.drag_data = {"x": x, "y": y, "item": word_id}
        else:
            self._clear_selection()

    def _on_canvas_drag(self, event) -> None:
        if self.drag_data["item"] is None:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        dx = x - self.drag_data["x"]
        dy = y - self.drag_data["y"]
        if dx == 0 and dy == 0:
            return
        word_id = self.drag_data["item"]
        self.renderer.move_word(word_id, dx, dy)
        self.words_data[word_id]['position']['x'] += dx
        self.words_data[word_id]['position']['y'] += dy
        self.renderer.update_scroll_region()
        self.drag_data["x"] = x
        self.drag_data["y"] = y

    def _on_canvas_release(self, event) -> None:
        if self.drag_data["item"] is not None:
            self._save_words()
        self.drag_data["item"] = None

    def _on_canvas_right_click(self, event) -> None:
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        word_id = self.renderer.find_word_at(x, y)
        if word_id is None:
            return
        # Select the word first so the toggles act on it (and the panels
        # reflect it), mirroring a left-click.
        char_index = self.renderer.find_character_at(word_id, x, y)
        self._select_word(word_id, focus_character=char_index)

        word_data = self.words_data[word_id]
        # The check state is embedded directly in each item's label rather than
        # using add_checkbutton/variable: macOS renders native menus and its
        # checkbutton indicators are unreliable (they can render the wrong
        # entry's state). A leading "✓ " vs padding is deterministic everywhere.
        def _label(text: str, on: bool) -> str:
            return f"✓ {text}" if on else f"    {text}"

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(
            label=_label("Tradução", bool(word_data.get('hasTranslation'))),
            command=lambda: self._toggle_translation(word_id),
        )
        menu.add_command(
            label=_label("Pinyin", bool(word_data.get('hasPinyin'))),
            command=lambda: self._toggle_pinyin(word_id),
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _typing_in_text_widget(self) -> bool:
        """True when keyboard focus is inside an Entry/Text widget (Palavra
        quiz, search box, …). Root-level <KeyPress> bindings still fire while
        the user types there, so plain-letter shortcuts must stand down."""
        try:
            focus = self.root.focus_get()
        except (tk.TclError, KeyError):
            return False
        return isinstance(focus, (tk.Entry, tk.Text))

    def _on_key_press(self, event) -> Optional[str]:
        if event.keysym in ('Tab', 'ISO_Left_Tab'):
            is_shift = (event.keysym == 'ISO_Left_Tab') or bool(event.state & 0x1)
            self._select_next_word(forward=not is_shift)
            return "break"

        # Typing "p"/"t"/"+"/"-"/backspace into the quiz or search fields must
        # edit text, not toggle canvas state or delete the selected word.
        if self._typing_in_text_widget():
            return None

        if self.selected_word_id is None:
            return None
        word_id = self.selected_word_id
        if not (0 <= int(word_id) < len(self.words_data)):
            self._clear_selection()
            return None

        ks = event.keysym
        if (ks in ('plus', 'equal') or event.char == '+'
                or (event.state & 0x4 and ks in ('equal', 'plus'))):
            self._change_size(word_id, 2)
        elif (ks == 'minus' or event.char == '-'
              or (event.state & 0x4 and ks == 'minus')):
            self._change_size(word_id, -2)
        elif ks.lower() == 'p':
            self._toggle_pinyin(word_id)
        elif ks.lower() == 't':
            self._toggle_translation(word_id)
        elif ks in ('Delete', 'BackSpace'):
            # macOS keyboards emit BackSpace for the main delete key; the
            # 'Delete' keysym alone required fn+delete, so word removal was
            # effectively unreachable on a Mac laptop keyboard.
            self._delete_word(word_id)
        return None

    def _on_play_audio_shortcut(self, event) -> Optional[str]:
        # Dedicated Cmd+S binding — kept separate from _on_key_press's plain-key
        # checks so typing an "s" while filling in the Palavra quiz field never
        # triggers playback.
        word_id = self.selected_word_id
        if word_id is None or not (0 <= int(word_id) < len(self.words_data)):
            return None
        if self.word_panel.is_audio_shortcut_enabled():
            self.audio.play(self.words_data[word_id]['word'])
        return "break"

    def _on_resize(self, event) -> None:
        if event.widget == self.root:
            self.root.after_idle(self.renderer.update_scroll_region)

    # --- Selection ---

    def _select_word(self, word_id: int, focus_character: Optional[int] = None) -> None:
        if word_id not in self.renderer.word_objects:
            return
        if not (0 <= int(word_id) < len(self.words_data)):
            return
        self.renderer.select(word_id)
        self.selected_word_id = word_id
        try:
            word_data = self.words_data[word_id]
            self.word_panel.show(word_data, focus_character=focus_character, word_id=word_id)
            self.web_panel.show(word_data, focus_character=focus_character)
        except Exception:
            pass

    def _clear_selection(self) -> None:
        self.renderer.clear_selection()
        self.selected_word_id = None

    def _select_next_word(self, forward: bool = True) -> None:
        try:
            if not self.words_data or not self.renderer.word_objects:
                return
            available = sorted(
                int(k) for k in self.renderer.word_objects.keys()
                if 0 <= int(k) < len(self.words_data)
            )
            if not available:
                return
            if (self.selected_word_id is None
                    or int(self.selected_word_id) not in available):
                target = 0 if forward else len(available) - 1
            else:
                current = available.index(int(self.selected_word_id))
                delta = 1 if forward else -1
                target = (current + delta) % len(available)
            self._select_word(available[target])
        except Exception:
            pass

    # --- Word manipulation ---

    def add_word_to_canvas(self, word: str, size: int = 36) -> None:
        x, y = self._compute_insertion_position(size)
        new_word = {
            'word': word, 'size': size,
            'position': {'x': x, 'y': y},
            'hasPinyin': False, 'hasTranslation': False,
            'pinyin': '', 'translation': '', 'tonePair': '',
        }
        new_id = len(self.words_data)
        self.words_data.append(new_word)
        self.renderer.draw_one(new_id, new_word)
        self._save_words()
        try:
            self._select_word(new_id)
        except Exception:
            pass

    def _compute_insertion_position(self, size: int) -> tuple:
        try:
            if (self.selected_word_id is not None
                    and self.selected_word_id in self.renderer.word_objects
                    and 0 <= int(self.selected_word_id) < len(self.words_data)):
                base = self.words_data[self.selected_word_id]
                base_x = base['position']['x']
                base_y = base['position']['y']
                x = int(base_x + max(40, base['size'] + 20))
                y = int(base_y)
                return x, y

            sr = self.canvas.cget("scrollregion") or "0 0 2000 2000"
            parts = ([int(float(p)) for p in sr.split()]
                     if isinstance(sr, str) else [0, 0, 2000, 2000])
            x1, y1, x2, y2 = parts if len(parts) == 4 else (0, 0, 2000, 2000)
            xv = self.canvas.xview()
            yv = self.canvas.yview()
            vl = x1 + (x2 - x1) * (xv[0] if xv else 0.0)
            vr = x1 + (x2 - x1) * (xv[1] if xv else 1.0)
            vt = y1 + (y2 - y1) * (yv[0] if yv else 0.0)
            vb = y1 + (y2 - y1) * (yv[1] if yv else 1.0)
            return int((vl + vr) / 2), int((vt + vb) / 2)
        except Exception:
            return 100, 100

    def _change_size(self, word_id: int, delta: int) -> None:
        word_data = self.words_data[word_id]
        new_size = max(8, min(120, word_data['size'] + delta))
        if new_size == word_data['size']:
            return
        word_data['size'] = new_size
        self.renderer.redraw_word(word_id, word_data)
        self._save_words()

    def _toggle_pinyin(self, word_id: int) -> None:
        word_data = self.words_data[word_id]
        word_data['hasPinyin'] = not word_data['hasPinyin']
        if word_data['hasPinyin']:
            self._fetch_word_data(word_id)
        else:
            self.renderer.redraw_word(word_id, word_data)
            self._save_words()

    def _toggle_translation(self, word_id: int) -> None:
        word_data = self.words_data[word_id]
        word_data['hasTranslation'] = not word_data['hasTranslation']
        if word_data['hasTranslation']:
            self._fetch_word_data(word_id)
        else:
            self.renderer.redraw_word(word_id, word_data)
            self._save_words()

    def _delete_word(self, word_id: int) -> None:
        if word_id not in self.renderer.word_objects:
            return
        if not (0 <= int(word_id) < len(self.words_data)):
            return
        try:
            del self.words_data[word_id]
        except Exception:
            return
        self.selected_word_id = None
        # words after the deleted index shift down by one; the panel's
        # per-word quiz state is keyed by index and must shift with them.
        self.word_panel.on_word_deleted(word_id)
        self.renderer.draw_all(self.words_data)
        self._save_words()

    def _fetch_word_data(self, word_id: int) -> None:
        word_data = self.words_data[word_id]
        word = word_data['word']

        def done(info):
            if not (0 <= word_id < len(self.words_data)):
                return
            if self.words_data[word_id].get('word') != word:
                return  # word at this id changed while the fetch was in flight

            pinyin_value = _extract_pinyin(info)
            translation_value = _extract_translation(info)
            tone_pair_value = _extract_tone_pair(info)

            if pinyin_value:
                word_data['pinyin'] = pinyin_value
            else:
                print(f"word-api sem pinyin para: {word}")
            if translation_value:
                word_data['translation'] = translation_value
            else:
                print(f"word-api sem tradução para: {word}")
            if tone_pair_value:
                word_data['tonePair'] = tone_pair_value

            self.renderer.redraw_word(word_id, word_data)
            self._save_words()

        self.tasks.submit(lambda: self.api.fetch_word_info(word), done)


def _extract_pinyin(info: Optional[Dict]) -> Optional[str]:
    if not isinstance(info, dict):
        return None
    if 'pinyin' in info:
        raw = info.get('pinyin')
        if isinstance(raw, list):
            return ' '.join(str(x) for x in raw if x)
        if raw is not None:
            return str(raw).strip()
    if 'pinyin_with_tone_marks' in info:
        return str(info.get('pinyin_with_tone_marks') or '').strip()
    if 'pinyin_tone_marks' in info:
        return str(info.get('pinyin_tone_marks') or '').strip()
    return None


def _extract_translation(info: Optional[Dict]) -> Optional[str]:
    if not isinstance(info, dict):
        return None
    raw = (info.get('translation')
           or info.get('translations')
           or info.get('english')
           or info.get('meaning'))
    if raw is None:
        return None
    if isinstance(raw, list):
        seen: List[str] = []
        for item in raw:
            s = str(item).strip()
            if s and s not in seen:
                seen.append(s)
        return '; '.join(seen)
    return str(raw).strip()


def _extract_tone_pair(info: Optional[Dict]) -> Optional[str]:
    if not isinstance(info, dict):
        return None
    raw = (info.get('tone_pairs') or info.get('tone_pair')
           or info.get('tonePairs') or info.get('tonepair'))
    if raw is None:
        return None
    filtered = ''.join(ch for ch in str(raw).strip() if ch in '12345')
    return filtered[:4] if filtered else ''


def main():
    root = tk.Tk()
    WordCanvasApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
