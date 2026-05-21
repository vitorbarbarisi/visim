"""Build canonical word-row dicts and resolve target paths for new CSVs."""
import os
from typing import Dict, List

DELTA = 300


def build_word_rows(words: List[str], delta: int = DELTA) -> List[Dict]:
    return [
        {
            'word': w,
            'size': 64,
            'position': {'x': 50, 'y': i * delta},
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
