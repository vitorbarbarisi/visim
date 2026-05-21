"""Utilities for Chinese character detection and tone color mapping."""

TONE_COLORS = {
    '1': '#90ee90',
    '2': '#add8e6',
    '3': '#d2b48c',
    '4': '#ffc0cb',
    '5': '#d3d3d3',
}


def is_chinese_char(ch: str) -> bool:
    if not ch:
        return False
    code = ord(ch)
    if 0x4E00 <= code <= 0x9FFF:
        return True
    if 0x3400 <= code <= 0x4DBF:
        return True
    if 0xF900 <= code <= 0xFAFF:
        return True
    if 0x20000 <= code <= 0x3134F:
        return True
    return False
