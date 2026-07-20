"""Tkinter Canvas renderer for words, pinyin, translation and tone coloring."""
import tkinter as tk
from tkinter import font as tkfont
from typing import Dict, List, Optional, Tuple

from chinese_utils import TONE_COLORS


class CanvasRenderer:
    SHADOW_COLOR = "#12151d"      # glyph drop-shadow on the dark canvas
    SELECTION_COLOR = "#5aa7ff"   # selection border/tint

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self.word_objects: Dict[int, Dict] = {}
        self.selected_word_id: Optional[int] = None

    def _draw_glyph(self, x: float, y: float, text: str, size: int,
                    weight: str, fill: str, main_tag: str,
                    shadow_tag: str) -> Tuple[int, int]:
        """Draw text with a single drop-shadow copy (instead of a 24-item
        halo) — far fewer canvas items, so dragging stays fluid."""
        offset = max(2, size // 14)
        font = ("Arial", size, weight)
        shadow_id = self.canvas.create_text(
            int(x + offset), int(y + offset), text=text, font=font,
            fill=self.SHADOW_COLOR, tags=shadow_tag,
        )
        text_id = self.canvas.create_text(
            int(x), int(y), text=text, font=font,
            fill=fill, tags=main_tag,
        )
        return text_id, shadow_id

    # --- Public API ---

    def draw_all(self, words_data: List[Dict]) -> None:
        self.canvas.delete("all")
        self.word_objects = {}
        self.selected_word_id = None
        for i, word_data in enumerate(words_data):
            self._draw_word(i, word_data)
        self.update_scroll_region()

    def draw_one(self, word_id: int, word_data: Dict) -> None:
        self._draw_word(word_id, word_data)
        self.update_scroll_region()

    def redraw_word(self, word_id: int, word_data: Dict) -> None:
        word_obj = self.word_objects.get(word_id)
        if word_obj is None:
            self._draw_word(word_id, word_data)
            self.update_scroll_region()
            return

        was_selected = (self.selected_word_id == word_id)
        self._delete_word_visuals(word_obj)
        text_ids, outline_ids, character_positions = self._draw_word_with_tones(
            word_id,
            word_data['position']['x'],
            word_data['position']['y'],
            word_data['word'],
            word_data['size'],
            word_data.get('tonePair', ''),
        )
        word_obj.update({
            'text_id': text_ids[0] if text_ids else None,
            'text_ids': text_ids,
            'outline_ids': outline_ids,
            'character_positions': character_positions,
            'pinyin_text_id': None,
            'pinyin_text_ids': [],
            'pinyin_outline_ids': [],
            'translation_text_id': None,
            'translation_outline_ids': [],
            'selection_rect_id': None,
            'data': word_data,
        })

        x = word_data['position']['x']
        y = word_data['position']['y']
        size = word_data['size']
        if word_data.get('hasPinyin') and word_data.get('pinyin'):
            self._draw_pinyin(word_id, x, y - size - 5, word_data['pinyin'], int(size * 0.5))
        if word_data.get('hasTranslation') and word_data.get('translation'):
            self._draw_translation(word_id, x, y + size + 10,
                                   word_data['translation'], int(size * 0.5))

        if was_selected:
            self.select(word_id)
        self.update_scroll_region()

    def delete_word(self, word_id: int) -> None:
        word_obj = self.word_objects.pop(word_id, None)
        if word_obj:
            self._delete_word_visuals(word_obj)
        if self.selected_word_id == word_id:
            self.selected_word_id = None

    def move_word(self, word_id: int, dx: float, dy: float) -> None:
        for tag in (
            f"word_{word_id}",
            f"word_{word_id}_outline",
            f"word_{word_id}_selection",
            f"word_{word_id}_pinyin",
            f"word_{word_id}_pinyin_outline",
            f"word_{word_id}_translation",
            f"word_{word_id}_translation_outline",
        ):
            self.canvas.move(tag, dx, dy)
        # Keep per-character hit-test coordinates in sync with the visuals;
        # otherwise find_character_at() works against stale positions after
        # a drag and focuses the wrong character tab.
        word_obj = self.word_objects.get(word_id)
        if word_obj:
            for cp in word_obj.get('character_positions', []) or []:
                cp['x'] += dx
                cp['y'] += dy

    def select(self, word_id: int) -> None:
        self.clear_selection()
        word_obj = self.word_objects.get(word_id)
        if not word_obj:
            return
        bbox = self._compute_full_bbox(word_obj)
        if not bbox:
            return
        min_x, min_y, max_x, max_y = bbox
        rect_id = self.canvas.create_rectangle(
            min_x - 8, min_y - 8, max_x + 8, max_y + 8,
            outline=self.SELECTION_COLOR, width=2, dash=(6, 4),
            fill=self.SELECTION_COLOR, stipple="gray12",
            tags=f"word_{word_id}_selection",
        )
        for key in ('text_id', 'pinyin_text_id', 'translation_text_id'):
            tid = word_obj.get(key)
            if tid:
                try:
                    self.canvas.tag_lower(rect_id, tid)
                except tk.TclError:
                    pass
        word_obj['selection_rect_id'] = rect_id
        self.selected_word_id = word_id

    def clear_selection(self) -> None:
        if self.selected_word_id is None:
            return
        word_obj = self.word_objects.get(self.selected_word_id)
        if word_obj and word_obj.get('selection_rect_id'):
            try:
                self.canvas.delete(word_obj['selection_rect_id'])
            except Exception:
                pass
            word_obj['selection_rect_id'] = None
        self.selected_word_id = None

    def find_character_at(self, word_id: int, canvas_x: float,
                          canvas_y: float) -> Optional[int]:
        """Find which character index was clicked within a word.
        Returns the character index (0-based) or None if not found."""
        word_obj = self.word_objects.get(word_id)
        if not word_obj:
            return None
        char_positions = word_obj.get('character_positions', [])
        if not char_positions:
            return 0

        # Vertical tolerance scales with the rendered font size so large
        # words remain hittable across their full glyph height.
        size = int(word_obj.get('data', {}).get('size') or 36)
        y_tolerance = max(20, size)

        for char_info in char_positions:
            if (abs(canvas_x - char_info['x']) <= char_info['width'] / 2 + 10
                    and abs(canvas_y - char_info['y']) <= y_tolerance):
                return char_info['index']
        # If no exact match, return the closest by horizontal distance
        closest = min(char_positions, key=lambda c: abs(canvas_x - c['x']))
        return closest['index']

    def find_word_at(self, canvas_x: float, canvas_y: float) -> Optional[int]:
        items = self.canvas.find_overlapping(
            canvas_x - 1, canvas_y - 1, canvas_x + 1, canvas_y + 1
        )
        # find_overlapping returns items bottom-to-top; walk top-to-bottom so
        # the topmost word wins when words overlap. Every visual carries a
        # "word_{id}[_suffix]" tag, so the id can be parsed straight from it.
        for item in reversed(items):
            for tag in self.canvas.gettags(item):
                if not tag.startswith("word_"):
                    continue
                parts = tag.split("_")
                if len(parts) >= 2 and parts[1].isdigit():
                    word_id = int(parts[1])
                    if word_id in self.word_objects:
                        return word_id
        return None

    def update_scroll_region(self) -> None:
        bbox = self.canvas.bbox("all")
        if bbox:
            padding = 50
            self.canvas.configure(scrollregion=(
                bbox[0] - padding, bbox[1] - padding,
                bbox[2] + padding, bbox[3] + padding,
            ))
        else:
            self.canvas.configure(scrollregion=(0, 0, 2000, 2000))

    # --- Private helpers ---

    def _draw_word(self, word_id: int, word_data: Dict) -> None:
        x = word_data['position']['x']
        y = word_data['position']['y']
        word = word_data['word']
        size = word_data['size']
        tone_pair = word_data.get('tonePair', '')

        text_ids, outline_ids, character_positions = self._draw_word_with_tones(
            word_id, x, y, word, size, tone_pair
        )
        self.word_objects[word_id] = {
            'text_id': text_ids[0] if text_ids else None,
            'text_ids': text_ids,
            'outline_ids': outline_ids,
            'character_positions': character_positions,
            'pinyin_text_id': None,
            'pinyin_text_ids': [],
            'pinyin_outline_ids': [],
            'translation_text_id': None,
            'translation_outline_ids': [],
            'selection_rect_id': None,
            'data': word_data,
        }
        if word_data.get('hasPinyin') and word_data.get('pinyin'):
            self._draw_pinyin(word_id, x, y - size - 5,
                              word_data['pinyin'], int(size * 0.5))
        if word_data.get('hasTranslation') and word_data.get('translation'):
            self._draw_translation(word_id, x, y + size + 10,
                                   word_data['translation'], int(size * 0.5))

    def _delete_word_visuals(self, word_obj: Dict) -> None:
        ids: List[int] = []
        if word_obj.get('text_id'):
            ids.append(word_obj['text_id'])
        ids.extend(word_obj.get('text_ids', []) or [])
        ids.extend(word_obj.get('outline_ids', []) or [])
        if word_obj.get('selection_rect_id'):
            ids.append(word_obj['selection_rect_id'])
        if word_obj.get('pinyin_text_id'):
            ids.append(word_obj['pinyin_text_id'])
        ids.extend(word_obj.get('pinyin_text_ids', []) or [])
        ids.extend(word_obj.get('pinyin_outline_ids', []) or [])
        if word_obj.get('translation_text_id'):
            ids.append(word_obj['translation_text_id'])
        ids.extend(word_obj.get('translation_outline_ids', []) or [])

        for tid in ids:
            try:
                self.canvas.delete(tid)
            except Exception:
                pass

    def _compute_full_bbox(self, word_obj: Dict
                           ) -> Optional[Tuple[int, int, int, int]]:
        # The word glyphs anchor the bbox; pinyin syllables (all of them, not
        # just the first) and the translation then expand it so the selection
        # rectangle wraps everything that is drawn for the word.
        main_ids: List[int] = list(word_obj.get('text_ids') or [])
        if not main_ids and word_obj.get('text_id'):
            main_ids.append(word_obj['text_id'])

        bbox: Optional[List[int]] = None
        for tid in main_ids:
            tb = self.canvas.bbox(tid)
            if tb:
                if bbox is None:
                    bbox = list(tb)
                else:
                    bbox[0] = min(bbox[0], tb[0])
                    bbox[1] = min(bbox[1], tb[1])
                    bbox[2] = max(bbox[2], tb[2])
                    bbox[3] = max(bbox[3], tb[3])
        if not bbox:
            return None

        extra_ids: List[int] = list(word_obj.get('pinyin_text_ids') or [])
        if word_obj.get('translation_text_id'):
            extra_ids.append(word_obj['translation_text_id'])
        for tid in extra_ids:
            tb = self.canvas.bbox(tid)
            if tb:
                bbox[0] = min(bbox[0], tb[0])
                bbox[1] = min(bbox[1], tb[1])
                bbox[2] = max(bbox[2], tb[2])
                bbox[3] = max(bbox[3], tb[3])
        return tuple(bbox)  # type: ignore[return-value]

    def _draw_word_with_tones(self, word_id: int, x: int, y: int,
                              word: str, size: int, tone_pair: str
                              ) -> Tuple[List[int], List[int], List[Dict]]:
        if not tone_pair or not word:
            return self._draw_text_centered(word_id, x, y, word, size, "white")

        tones = [ch for ch in tone_pair if ch in '12345']
        chars = list(word)

        canvas_font = tkfont.Font(family="Arial", size=size, weight="bold")
        total_width = canvas_font.measure(word)
        if total_width <= 0:
            return self._draw_text_centered(word_id, x, y, word, size, "white")

        left_edge = x - total_width / 2
        text_ids: List[int] = []
        outline_ids: List[int] = []
        character_positions: List[Dict] = []
        for idx, ch in enumerate(chars):
            prefix_width = canvas_font.measure(word[:idx])
            char_width = canvas_font.measure(ch)
            char_center_x = left_edge + prefix_width + (char_width / 2)
            tone = tones[idx] if idx < len(tones) else None
            color = TONE_COLORS.get(tone, 'white') if tone else 'white'

            character_positions.append({
                'index': idx,
                'char': ch,
                'x': char_center_x,
                'y': y,
                'width': char_width,
            })

            text_id, shadow_id = self._draw_glyph(
                char_center_x, y, ch, size, "bold", color,
                f"word_{word_id}", f"word_{word_id}_outline",
            )
            text_ids.append(text_id)
            outline_ids.append(shadow_id)
        return text_ids, outline_ids, character_positions

    def _draw_text_centered(self, word_id: int, x: int, y: int,
                            word: str, size: int, color: str
                            ) -> Tuple[List[int], List[int], List[Dict]]:
        text_id, shadow_id = self._draw_glyph(
            x, y, word, size, "bold", color,
            f"word_{word_id}", f"word_{word_id}_outline",
        )
        outline_ids: List[int] = [shadow_id]
        canvas_font = tkfont.Font(family="Arial", size=size, weight="bold")
        total_width = canvas_font.measure(word)
        left_edge = x - total_width / 2
        character_positions: List[Dict] = []
        for idx, ch in enumerate(word):
            prefix_width = canvas_font.measure(word[:idx])
            char_width = canvas_font.measure(ch)
            char_center_x = left_edge + prefix_width + (char_width / 2)
            character_positions.append({
                'index': idx,
                'char': ch,
                'x': char_center_x,
                'y': y,
                'width': char_width,
            })
        return [text_id], outline_ids, character_positions

    def _draw_pinyin(self, word_id: int, x: int, y: int,
                     pinyin: str, size: int) -> None:
        try:
            self.canvas.delete(f"word_{word_id}_pinyin")
            self.canvas.delete(f"word_{word_id}_pinyin_outline")
        except Exception:
            pass

        word_obj = self.word_objects.get(word_id, {})
        word_data = word_obj.get('data') or {}
        tone_pair = word_data.get('tonePair') or ''
        word_text = word_data.get('word') or ''

        syllables = [s for s in (pinyin or '').split() if s]
        tones = [ch for ch in tone_pair if ch in '12345']
        chars = list(word_text)

        if chars and syllables:
            main_size = int(word_data.get('size') or 0)
            try:
                canvas_font = tkfont.Font(family="Arial", size=main_size, weight="bold")
                total_width = canvas_font.measure(word_text)
            except Exception:
                total_width = 0

            if total_width > 0:
                left_edge = x - total_width / 2
                char_centers: List[int] = []
                for idx, ch in enumerate(chars):
                    prefix_width = canvas_font.measure(word_text[:idx])
                    char_width = canvas_font.measure(ch)
                    char_centers.append(int(left_edge + prefix_width + char_width / 2))

                count = min(len(chars), len(syllables))

                drawn_colors: List[str] = []
                for tid in word_obj.get('text_ids') or []:
                    try:
                        drawn_colors.append(self.canvas.itemcget(tid, 'fill'))
                    except Exception:
                        drawn_colors.append('white')

                try:
                    base_font = tkfont.Font(family="Arial", size=size, weight="bold")
                    char_w = [canvas_font.measure(ch) for ch in chars[:count]]
                    syll_w = [base_font.measure(s) for s in syllables[:count]]
                    scales = [(char_w[i] * 0.9) / max(1, syll_w[i]) for i in range(count)]
                    scale = min(scales) if scales else 1.0
                    scale = max(0.6, min(1.0, scale))
                    adj_size = max(8, int(size * scale))
                except Exception:
                    adj_size = size

                pinyin_text_ids: List[int] = []
                pinyin_outline_ids: List[int] = []
                for i in range(count):
                    syll = syllables[i]
                    if i < len(drawn_colors) and drawn_colors[i]:
                        color = drawn_colors[i]
                    else:
                        tone = tones[i] if i < len(tones) else None
                        color = TONE_COLORS.get(tone, 'white') if tone else 'white'
                    cx = char_centers[i] if i < len(char_centers) else x

                    text_id, shadow_id = self._draw_glyph(
                        cx, y, syll, adj_size, "bold", color,
                        f"word_{word_id}_pinyin",
                        f"word_{word_id}_pinyin_outline",
                    )
                    pinyin_text_ids.append(text_id)
                    pinyin_outline_ids.append(shadow_id)
                word_obj['pinyin_text_id'] = pinyin_text_ids[0] if pinyin_text_ids else None
                word_obj['pinyin_text_ids'] = pinyin_text_ids
                word_obj['pinyin_outline_ids'] = pinyin_outline_ids
                return

        # Fallback: single white pinyin centered
        text_id, shadow_id = self._draw_glyph(
            x, y, pinyin, max(8, int(size * 0.9)), "bold", "white",
            f"word_{word_id}_pinyin", f"word_{word_id}_pinyin_outline",
        )
        word_obj['pinyin_text_id'] = text_id
        word_obj['pinyin_text_ids'] = [text_id]
        word_obj['pinyin_outline_ids'] = [shadow_id]

    def _draw_translation(self, word_id: int, x: int, y: int,
                          translation: str, size: int) -> None:
        text_id, shadow_id = self._draw_glyph(
            x, y, translation, size, "normal", "#ffe999",
            f"word_{word_id}_translation",
            f"word_{word_id}_translation_outline",
        )
        word_obj = self.word_objects.get(word_id)
        if word_obj is not None:
            word_obj['translation_text_id'] = text_id
            word_obj['translation_outline_ids'] = [shadow_id]
