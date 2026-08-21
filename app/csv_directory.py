"""Which CSV comes before or after the one that is open.

The files in `files/` are one per study day (2026_08_12.csv, 2026_08_13.csv, …),
so "previous"/"next" is just their name order. Listing is separated from the
index math so the math stays pure and unit-testable, and the navigator is
injected into the app rather than built there.
"""
import os
from typing import List, Optional, Sequence

CSV_EXT = ".csv"


def list_csv_paths(directory: str) -> List[str]:
    """Absolute paths of every .csv in `directory`, sorted by file name.

    A missing or unreadable directory yields an empty list: navigation should
    quietly do nothing, not raise in the middle of a keypress.
    """
    try:
        names = os.listdir(directory)
    except OSError:
        return []
    return [os.path.join(directory, name) for name in sorted(names)
            if name.lower().endswith(CSV_EXT)
            and os.path.isfile(os.path.join(directory, name))]


def neighbor(paths: Sequence[str], current: Optional[str],
             delta: int) -> Optional[str]:
    """The entry `delta` steps from `current`, wrapping around both ends.

    `current` absent from the list (a file just deleted, or the default
    files/words.csv that does not exist) is not an error: stepping forward from
    nowhere means the first file, backward means the last.
    """
    if not paths:
        return None
    try:
        index = list(paths).index(current)
    except ValueError:
        return paths[0] if delta > 0 else paths[-1]
    return paths[(index + delta) % len(paths)]


class CsvDirectoryNavigator:
    """Sibling-file navigation for whichever CSV is currently open."""

    def __init__(self, lister=list_csv_paths):
        self._list = lister

    def previous(self, current_path: Optional[str]) -> Optional[str]:
        return self._step(current_path, -1)

    def next(self, current_path: Optional[str]) -> Optional[str]:
        return self._step(current_path, 1)

    def _step(self, current_path: Optional[str], delta: int) -> Optional[str]:
        if not current_path:
            return None
        current = os.path.abspath(current_path)
        target = neighbor(self._list(os.path.dirname(current)), current, delta)
        # A folder holding a single CSV wraps onto itself; reopening it would
        # throw away the quiz state for no movement.
        return None if target == current else target
