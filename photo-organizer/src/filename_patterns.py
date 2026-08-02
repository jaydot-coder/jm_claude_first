from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from src.config import CustomPattern


@dataclass
class PatternMatch:
    pattern_name: str
    capture_dt: datetime | None  # None means "recognized filename, but no date in it"


_ParseFn = Callable[[re.Match], datetime | None]


def _date_time(date_group: str = "date", time_group: str = "time") -> _ParseFn:
    def parser(m: re.Match) -> datetime | None:
        try:
            date_part = m.group(date_group)
            time_part = m.group(time_group)
            return datetime.strptime(f"{date_part}{time_part}", "%Y%m%d%H%M%S")
        except (ValueError, IndexError):
            return None

    return parser


def _date_only(date_group: str = "date") -> _ParseFn:
    def parser(m: re.Match) -> datetime | None:
        try:
            return datetime.strptime(m.group(date_group), "%Y%m%d")
        except (ValueError, IndexError):
            return None

    return parser


def _iso_dotted_time(m: re.Match) -> datetime | None:
    try:
        return datetime(
            int(m.group("y")),
            int(m.group("mo")),
            int(m.group("d")),
            int(m.group("H")),
            int(m.group("mi")),
            int(m.group("s")),
        )
    except (ValueError, IndexError):
        return None


def _no_date(_: re.Match) -> None:
    return None


# Tried in order, first regex match wins. A match with a parser returning None is a
# deliberate "recognized, but no date available" short-circuit (e.g. default iPhone
# names) -- it stops the filename tier without pretending a date was found.
_BUILTIN_PATTERNS: list[tuple[str, re.Pattern, _ParseFn]] = [
    (
        "filename_kakaotalk",
        re.compile(r"^kakaotalk_(?P<date>\d{8})_(?P<time>\d{6})", re.IGNORECASE),
        _date_time(),
    ),
    (
        "filename_screenshot_android",
        re.compile(r"^screenshot_(?P<date>\d{8})-(?P<time>\d{6})", re.IGNORECASE),
        _date_time(),
    ),
    (
        "filename_screenshot_ios",
        re.compile(
            r"^(?P<y>\d{4})-(?P<mo>\d{2})-(?P<d>\d{2})[ _](?P<H>\d{2})\.(?P<mi>\d{2})\.(?P<s>\d{2})"
        ),
        _iso_dotted_time,
    ),
    (
        "filename_whatsapp",
        re.compile(r"^img-(?P<date>\d{8})-wa\d+", re.IGNORECASE),
        _date_only(),
    ),
    (
        "filename_galaxy",
        re.compile(r"^(?:img|vid|pano)?_?(?P<date>\d{8})_(?P<time>\d{6})", re.IGNORECASE),
        _date_time(),
    ),
    (
        "filename_iphone_default_no_date",
        re.compile(r"^img_\d{4}\.(heic|heif|jpe?g|png)$", re.IGNORECASE),
        _no_date,
    ),
]


def build_custom_patterns(custom: list[CustomPattern]) -> list[tuple[str, re.Pattern, _ParseFn]]:
    compiled = []
    for c in custom:
        regex = re.compile(c.regex)

        def parser(m: re.Match, group=c.group, fmt=c.format) -> datetime | None:
            try:
                return datetime.strptime(m.group(group), fmt)
            except (ValueError, IndexError):
                return None

        compiled.append((c.name, regex, parser))
    return compiled


def resolve_from_filename(
    filename: str, custom_patterns: list[tuple[str, re.Pattern, _ParseFn]] | None = None
) -> PatternMatch | None:
    """Try each known filename convention in order. Returns None if nothing recognized
    the filename at all; returns a PatternMatch (possibly with capture_dt=None) if a
    convention was recognized."""
    all_patterns = _BUILTIN_PATTERNS + list(custom_patterns or [])
    for name, regex, parser in all_patterns:
        m = regex.match(filename)
        if m:
            return PatternMatch(pattern_name=name, capture_dt=parser(m))
    return None
