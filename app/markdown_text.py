"""Render a practical subset of Markdown into a tk.Text widget using tags.

Scoped to what an LLM actually emits in prose: headings, bold/italic, inline
code, fenced code blocks, bullet and numbered lists, block quotes, horizontal
rules and links. Anything unrecognized falls through as plain text, so a
malformed answer degrades gracefully instead of breaking the window.

Tags are created in ascending priority order. Tk resolves conflicting options
(notably `font`) by tag priority, not by the order tags are passed to insert(),
so emphasis tags must be created after the body tag to win over it.
"""
import re
import tkinter.font as tkfont
from typing import Optional, Sequence, Tuple

_MONO_CANDIDATES = ("Menlo", "SF Mono", "DejaVu Sans Mono", "Consolas",
                    "Courier New", "Courier")

PLAIN_INFO = "md_info"
PLAIN_ERROR = "md_error"


class MarkdownRenderer:
    BASE_FAMILY = "Arial"
    BASE_SIZE = 12
    HEADING_DELTA = {1: 6, 2: 4, 3: 2, 4: 1, 5: 0, 6: 0}
    LIST_DEPTHS = 3
    BULLETS = ("•", "◦", "▪")
    RULE_WIDTH = 48

    _FENCE = re.compile(r"^\s*(?P<mark>```+|~~~+)\s*[\w+-]*\s*$")
    _HEADING = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.*)$")
    _HR = re.compile(r"^\s*(?P<c>[-*_])\s*(?:(?P=c)\s*){2,}$")
    _QUOTE = re.compile(r"^\s*>\s?(?P<text>.*)$")
    _BULLET = re.compile(r"^(?P<indent>\s*)[-*+]\s+(?P<text>.*)$")
    _ORDERED = re.compile(r"^(?P<indent>\s*)(?P<num>\d{1,3})[.)]\s+(?P<text>.*)$")
    # Alternation order matters: *** before ** before *, so the longest
    # emphasis marker wins.
    _INLINE = re.compile(
        r"(?P<ct>`+)(?P<code>.+?)(?P=ct)"
        r"|(?P<m3>\*\*\*|___)(?P<b3>\S.*?)(?P=m3)"
        r"|(?P<m2>\*\*|__)(?P<b2>\S.*?)(?P=m2)"
        r"|(?P<m1>[*_])(?P<b1>\S.*?)(?P=m1)"
        r"|\[(?P<label>[^\]\n]+)\]\((?P<url>[^)\s]*)[^)]*\)",
        re.DOTALL,
    )

    def __init__(self):
        self._mono: Optional[str] = None

    # ------------------------------------------------------------------ #
    #  Tags                                                               #
    # ------------------------------------------------------------------ #

    def configure(self, widget) -> None:
        """Idempotent. Creation order sets priority — do not reshuffle."""
        base = (self.BASE_FAMILY, self.BASE_SIZE)
        mono = (self._mono_family(widget), self.BASE_SIZE - 1)
        tag = widget.tag_configure

        tag("md_body", font=base, spacing1=1, spacing3=3)
        tag("md_link", foreground="#1c7ed6", underline=True)
        tag("md_quote", lmargin1=18, lmargin2=18, foreground="#5f6b7a")
        tag("md_hr", foreground="#ced4da", spacing1=6, spacing3=6)
        for depth in range(self.LIST_DEPTHS):
            shift = depth * 24
            tag(f"md_bullet{depth}", lmargin1=18 + shift, lmargin2=34 + shift)
            tag(f"md_ordered{depth}", lmargin1=18 + shift, lmargin2=40 + shift)
        # After the body tag so their fonts win.
        tag("md_bold", font=base + ("bold",))
        tag("md_italic", font=base + ("italic",))
        tag("md_bold_italic", font=base + ("bold italic",))
        tag("md_code", font=mono, background="#f1f3f5", foreground="#c92a2a")
        tag("md_codeblock", font=mono, background="#f8f9fa", lmargin1=18,
            lmargin2=18, spacing1=3, spacing3=3)
        for level, delta in self.HEADING_DELTA.items():
            tag(f"md_h{level}",
                font=(self.BASE_FAMILY, self.BASE_SIZE + delta, "bold"),
                spacing1=8, spacing3=4)
        tag(PLAIN_INFO, font=(self.BASE_FAMILY, self.BASE_SIZE - 1),
            foreground="#6c757d")
        tag(PLAIN_ERROR, font=(self.BASE_FAMILY, self.BASE_SIZE, "bold"),
            foreground="#dc3545")

    def _mono_family(self, widget) -> str:
        if self._mono is None:
            try:
                available = set(tkfont.families(widget))
            except Exception:
                available = set()
            self._mono = next((f for f in _MONO_CANDIDATES if f in available),
                              "Courier")
        return self._mono

    # ------------------------------------------------------------------ #
    #  Block level                                                        #
    # ------------------------------------------------------------------ #

    def render(self, widget, markdown: str) -> None:
        """Append `markdown` to `widget`. The caller owns state= and clearing."""
        self.configure(widget)
        lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")

        index, wrote, gap = 0, False, False
        while index < len(lines):
            raw = lines[index]
            stripped = raw.strip()

            if not stripped:
                gap = wrote
                index += 1
                continue

            fence = self._FENCE.match(raw)
            if fence:
                body, index = self._collect_code(lines, index + 1,
                                                 fence.group("mark"))
                gap = self._gap(widget, gap)
                widget.insert("end", body + "\n", ("md_codeblock",))
                wrote = True
                continue

            gap = self._gap(widget, gap)
            wrote = True
            index += 1

            if self._HR.match(stripped):
                widget.insert("end", "─" * self.RULE_WIDTH + "\n", ("md_hr",))
                continue

            heading = self._HEADING.match(stripped)
            if heading:
                tag = f"md_h{min(len(heading.group('hashes')), 6)}"
                # font_locked: the heading font outranks inline emphasis, but
                # the markers are still consumed rather than shown.
                self._inline(widget, heading.group("text").strip(), (tag,),
                             font_locked=True)
                widget.insert("end", "\n", (tag,))
                continue

            quote = self._QUOTE.match(raw)
            if quote:
                tags = ("md_body", "md_quote")
                self._inline(widget, quote.group("text"), tags)
                widget.insert("end", "\n", tags)
                continue

            bullet = self._BULLET.match(raw)
            if bullet:
                depth = self._depth(bullet.group("indent"))
                tags = ("md_body", f"md_bullet{depth}")
                widget.insert("end", f"{self.BULLETS[depth]} ", tags)
                self._inline(widget, bullet.group("text"), tags)
                widget.insert("end", "\n", tags)
                continue

            ordered = self._ORDERED.match(raw)
            if ordered:
                depth = self._depth(ordered.group("indent"))
                tags = ("md_body", f"md_ordered{depth}")
                widget.insert("end", f"{ordered.group('num')}. ", tags)
                self._inline(widget, ordered.group("text"), tags)
                widget.insert("end", "\n", tags)
                continue

            self._inline(widget, stripped, ("md_body",))
            widget.insert("end", "\n", ("md_body",))

    def render_plain(self, widget, message: str, tag: str) -> None:
        """Insert `message` verbatim under a single tag (status / error text)."""
        self.configure(widget)
        widget.insert("end", message, (tag,))

    def _depth(self, indent: str) -> int:
        return min(len(indent.replace("\t", "  ")) // 2, self.LIST_DEPTHS - 1)

    def _gap(self, widget, pending: bool) -> bool:
        if pending:
            widget.insert("end", "\n", ("md_body",))
        return False

    def _collect_code(self, lines: Sequence[str], start: int,
                      mark: str) -> Tuple[str, int]:
        char = mark[0]
        body = []
        index = start
        while index < len(lines):
            candidate = lines[index].strip()
            if len(candidate) >= 3 and set(candidate) == {char}:
                return "\n".join(body), index + 1
            body.append(lines[index])
            index += 1
        return "\n".join(body), index  # unterminated fence: take the rest

    # ------------------------------------------------------------------ #
    #  Inline level                                                       #
    # ------------------------------------------------------------------ #

    def _inline(self, widget, text: str, base: Tuple[str, ...],
                font_locked: bool = False,
                styles: frozenset = frozenset()) -> None:
        cursor = 0
        for match in self._INLINE.finditer(text):
            if match.start() > cursor:
                self._emit(widget, text[cursor:match.start()], base, styles,
                           font_locked)
            cursor = match.end()

            if match.group("code") is not None:
                self._emit(widget, match.group("code"), base + ("md_code",),
                           styles, font_locked=True)
                continue

            for marker_group, body_group, added in (
                ("m3", "b3", ("bold", "italic")),
                ("m2", "b2", ("bold",)),
                ("m1", "b1", ("italic",)),
            ):
                marker = match.group(marker_group)
                if marker is None:
                    continue
                if not self._underscore_ok(text, match, marker):
                    # e.g. snake_case_name — not emphasis; show it as typed.
                    self._emit(widget, match.group(0), base, styles, font_locked)
                    break
                self._inline(widget, match.group(body_group), base, font_locked,
                             styles.union(added))
                break
            else:
                label = match.group("label")
                if label is not None:
                    self._emit(widget, label, base + ("md_link",), styles,
                               font_locked)

        if cursor < len(text):
            self._emit(widget, text[cursor:], base, styles, font_locked)

    def _emit(self, widget, chunk: str, base: Tuple[str, ...],
              styles: frozenset, font_locked: bool) -> None:
        if not chunk:
            return
        tags = base
        if not font_locked:
            font_tag = self._font_tag(styles)
            if font_tag:
                tags = tags + (font_tag,)
        widget.insert("end", chunk, tags)

    @staticmethod
    def _font_tag(styles: frozenset) -> Optional[str]:
        if "bold" in styles and "italic" in styles:
            return "md_bold_italic"
        if "bold" in styles:
            return "md_bold"
        if "italic" in styles:
            return "md_italic"
        return None

    @staticmethod
    def _underscore_ok(text: str, match, marker: str) -> bool:
        """Underscores only delimit emphasis at word boundaries, so
        identifiers like snake_case_name survive intact."""
        if "_" not in marker:
            return True
        before = text[match.start() - 1] if match.start() > 0 else " "
        after = text[match.end()] if match.end() < len(text) else " "
        return not (before.isalnum() or after.isalnum())
