"""CSV-backed repository for word data."""
import csv
import os
from typing import Dict, List


class CsvWordRepository:
    FIELDS = [
        'word', 'size', 'position_x', 'position_y',
        'has_pinyin', 'has_translation',
        'pinyin', 'translation', 'tone_pair',
    ]

    def __init__(self, path: str):
        self.path = os.path.abspath(path)

    def load(self) -> List[Dict]:
        words: List[Dict] = []
        with open(self.path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                word_raw = row.get('word')
                if not word_raw or (isinstance(word_raw, str) and not word_raw.strip()):
                    continue
                try:
                    position_x = int(float(row.get('position_x') or 0))
                    position_y = int(float(row.get('position_y') or 0))
                    size = int(float(row.get('size') or 36))
                except (ValueError, KeyError) as e:
                    print(f"Error parsing numeric values for word "
                          f"'{row.get('word', 'unknown')}': {e}")
                    continue

                words.append({
                    'word': _to_str(row.get('word')),
                    'size': size,
                    'position': {'x': position_x, 'y': position_y},
                    'hasPinyin': _to_bool(row.get('has_pinyin', 'false')),
                    'hasTranslation': _to_bool(row.get('has_translation', 'false')),
                    'pinyin': _to_str(row.get('pinyin')),
                    'translation': _to_str(row.get('translation')),
                    'tonePair': _to_str(row.get('tone_pair')),
                })
        return words

    def save(self, words_data: List[Dict]) -> None:
        dir_path = os.path.dirname(self.path)
        if dir_path and not os.path.isdir(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        with open(self.path, 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(self.FIELDS)
            for w in words_data:
                writer.writerow([
                    w['word'],
                    w['size'],
                    w['position']['x'],
                    w['position']['y'],
                    str(w['hasPinyin']).lower(),
                    str(w['hasTranslation']).lower(),
                    w.get('pinyin', ''),
                    w.get('translation', ''),
                    w.get('tonePair', ''),
                ])


def _to_str(value) -> str:
    if value is None:
        return ''
    return value.strip() if isinstance(value, str) else str(value).strip()


def _to_bool(value) -> bool:
    return str(value).strip().lower() == 'true'
