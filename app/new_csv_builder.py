"""Build canonical word-row dicts and resolve target paths for new CSVs."""
import os
from typing import Dict, List

# Vertical step and first-column x come from files/400.csv; the horizontal
# step between columns comes from files/tone_pairs.csv.
DELTA = 300
COLUMN_DELTA = 260
ORIGIN_X = 50


def grid_position(index: int, columns: int = 1, delta: int = DELTA,
                  column_delta: int = COLUMN_DELTA,
                  origin_x: int = ORIGIN_X) -> Dict[str, int]:
    """Canvas position of the index-th word, filling the grid row by row."""
    columns = max(1, columns)
    row, col = divmod(index, columns)
    return {'x': origin_x + col * column_delta, 'y': row * delta}


def build_word_rows(words: List[str], columns: int = 1,
                    delta: int = DELTA) -> List[Dict]:
    return [
        {
            'word': w,
            'size': 64,
            'position': grid_position(i, columns, delta),
            'hasPinyin': True,
            'hasTranslation': True,
            'pinyin': '',
            'translation': '',
            'tonePair': '',
        }
        for i, w in enumerate(words)
    ]


def resolve_new_csv_path(repo_root: str, file_name: str) -> str:
    files_dir = os.path.join(repo_root, "files")
    os.makedirs(files_dir, exist_ok=True)
    name = file_name if file_name.lower().endswith(".csv") else f"{file_name}.csv"
    return os.path.join(files_dir, name)
