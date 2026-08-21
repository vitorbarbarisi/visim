"""Keyboard navigation order: the two file buttons bracket the canvas words.

Pure — nothing here imports tkinter, so the ring can be unit-tested on plain
ints without building a widget (same reasoning as scroll_utils).

The ring is [PREV] + words + [NEXT], traversed circularly, which is what makes
the whole app reachable with Tab and Enter alone: tabbing off the last word
lands on "Próximo", shift-tabbing off the first lands on "Anterior".
"""
from typing import Optional, Sequence, Union

PREV = 'prev'
NEXT = 'next'

Stop = Union[int, str]


def build(word_ids: Sequence[int]) -> list:
    """The full traversal order, buttons included."""
    return [PREV] + list(word_ids) + [NEXT]


def advance(word_ids: Sequence[int], current: Optional[Stop],
            forward: bool = True) -> Optional[Stop]:
    """The next stop after `current`, wrapping at both ends.

    With `current` outside the ring (nothing selected, or a stale index left
    over from a file that was just closed) this deliberately lands on a WORD,
    not a button: pressing Tab with an empty selection has always meant "start
    at the first word", and the buttons should not steal that.
    """
    ring = build(word_ids)
    if current is None or current not in ring:
        if not word_ids:
            return PREV if forward else NEXT
        return word_ids[0] if forward else word_ids[-1]
    index = ring.index(current)
    return ring[(index + (1 if forward else -1)) % len(ring)]
