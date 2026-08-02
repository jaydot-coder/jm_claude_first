"""Converts the limited markdown subset used by the blog-writer agent into HTML that
survives a copy-paste into the Naver blog editor.

Deliberately not a general markdown implementation: the agent is instructed to emit only
the syntax listed in prompts/naver-blog-format.md, and a focused converter keeps the
output predictable (Naver silently drops most structural HTML, so the styling has to be
inline on every element).
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

HIGHLIGHT_COLOR = "#FFE400"

# Placeholder left in the HTML stream where a photo belongs. page.py swaps these for a
# thumbnail (preview) or a visible "[사진 N]" marker (clipboard copy).
_SLOT_TOKEN = "<!--IMAGE_SLOT:{index}-->"
_SLOT_TOKEN_RE = re.compile(r"<!--IMAGE_SLOT:(\d+)-->")

_IMAGE_LINE = re.compile(r"^\[이미지:\s*(?P<body>.+?)\]\s*$")
_HEADING = re.compile(r"^(?P<hashes>#{1,3})\s+(?P<text>.+?)\s*$")
_HR = re.compile(r"^\s*---+\s*$")
_QUOTE = re.compile(r"^>\s*(?P<text>.*?)\s*$")

_CODE_SPAN = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_HIGHLIGHT = re.compile(r"==(.+?)==")
_STRIKE = re.compile(r"~~(.+?)~~")

_HEADING_STYLE = {
    1: "font-size:1.2em;font-weight:bold;text-align:center;",
    2: "font-size:1.1em;font-weight:bold;text-align:center;",
    3: "font-size:1.05em;font-weight:bold;text-align:center;",
}
_PARAGRAPH_STYLE = "text-align:center;"


@dataclass
class ConvertResult:
    title: str
    body_html: str
    slot_bodies: list[str] = field(default_factory=list)


def _inline(text: str) -> str:
    """Escape the text, then apply inline markers. Code spans are stashed first so that
    markers inside them are shown literally rather than being interpreted."""
    stash: list[str] = []

    def _stash_code(m: re.Match) -> str:
        stash.append(m.group(1))
        return f"\x00{len(stash) - 1}\x00"

    text = _CODE_SPAN.sub(_stash_code, text)
    text = html.escape(text, quote=False)

    text = _BOLD.sub(r'<strong style="font-weight:bold;">\1</strong>', text)
    text = _HIGHLIGHT.sub(
        rf'<span style="background-color:{HIGHLIGHT_COLOR};">\1</span>', text
    )
    text = _STRIKE.sub(r"<del>\1</del>", text)

    def _unstash(m: re.Match) -> str:
        code = html.escape(stash[int(m.group(1))], quote=False)
        return f'<code style="font-family:monospace;">{code}</code>'

    return re.sub(r"\x00(\d+)\x00", _unstash, text)


def convert(markdown: str) -> ConvertResult:
    title = ""
    parts: list[str] = []
    slot_bodies: list[str] = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        image_match = _IMAGE_LINE.match(line)
        if image_match:
            parts.append(_SLOT_TOKEN.format(index=len(slot_bodies)))
            slot_bodies.append(image_match.group("body").strip())
            continue

        if _HR.match(line):
            parts.append("<hr />")
            continue

        heading_match = _HEADING.match(line)
        if heading_match:
            level = len(heading_match.group("hashes"))
            text = heading_match.group("text")
            if level == 1 and not title:
                title = text
            parts.append(
                f'<h{level} style="{_HEADING_STYLE[level]}">{_inline(text)}</h{level}>'
            )
            continue

        quote_match = _QUOTE.match(line)
        if quote_match:
            text = quote_match.group("text")
            if not text:
                continue
            # blockquoteStyle="bold": Naver renders bare bold text more cleanly than a
            # bordered blockquote, matching the existing preview-blog.mjs behaviour.
            parts.append(
                f'<p style="{_PARAGRAPH_STYLE}">'
                f'<strong style="font-weight:bold;">{_inline(text)}</strong></p>'
            )
            continue

        parts.append(f'<p style="{_PARAGRAPH_STYLE}">{_inline(line)}</p>')

    return ConvertResult(title=title, body_html="\n".join(parts), slot_bodies=slot_bodies)


def replace_slots(body_html: str, replacement_for_index) -> str:
    """Swap each slot token for whatever `replacement_for_index(i)` returns."""
    return _SLOT_TOKEN_RE.sub(lambda m: replacement_for_index(int(m.group(1))), body_html)
