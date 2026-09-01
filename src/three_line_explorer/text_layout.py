from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import math
import unicodedata

from three_line_explorer.inspection_texts import InspectionText


TextMeasure = Callable[[str], int]

NO_LINE_START = frozenset(
    "、。，．・：；？！"
    "ー〜…‥"
    "）〕］｝〉》」』】"
    "ぁぃぅぇぉっゃゅょゎ"
    "ァィゥェォッャュョヮヵヶ"
)
NO_LINE_END = frozenset("（〔［｛〈《「『【")


@dataclass(frozen=True, slots=True)
class PreparedInspectionPage:
    lines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PreparedInspectionText:
    title: str
    pages: tuple[PreparedInspectionPage, ...]


@dataclass(slots=True)
class InspectionTextLayoutCache:
    texts: Mapping[str, InspectionText]
    max_width: int
    max_lines: int
    measure: TextMeasure
    _cache: dict[str, PreparedInspectionText] = field(default_factory=dict)

    def get(self, text_key: str) -> PreparedInspectionText | None:
        cached = self._cache.get(text_key)
        if cached is not None:
            return cached
        source = self.texts.get(text_key)
        if source is None:
            return None
        prepared = prepare_inspection_text(
            source,
            self.max_width,
            self.max_lines,
            self.measure,
        )
        self._cache[text_key] = prepared
        return prepared


def estimate_text_width(text: str, font_size: int) -> int:
    half_units = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        east_asian_width = unicodedata.east_asian_width(char)
        half_units += 2 if east_asian_width in {"F", "W", "A"} else 1
    return math.ceil(half_units * font_size / 2)


def create_text_measure(font: object, font_size: int) -> TextMeasure:
    text_width = getattr(font, "text_width", None)
    if callable(text_width):
        return lambda text: int(text_width(text))
    return lambda text: estimate_text_width(text, font_size)


def wrap_japanese_text(
    text: str,
    max_width: int,
    measure: TextMeasure,
) -> tuple[str, ...]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    result: list[str] = []
    for paragraph in normalized.split("\n"):
        if paragraph == "":
            result.append("")
            continue
        current = ""
        for char in paragraph:
            candidate = current + char
            if not current or measure(candidate) <= max_width:
                current = candidate
                continue
            if char in NO_LINE_START:
                carry = current[-1] + char
                current = current[:-1]
                while current and current[-1] in NO_LINE_END:
                    carry = current[-1] + carry
                    current = current[:-1]
                if current:
                    result.append(current)
                current = carry
                continue
            carry = ""
            while current and current[-1] in NO_LINE_END:
                carry = current[-1] + carry
                current = current[:-1]
            if current:
                result.append(current)
            current = carry + char
        if current:
            result.append(current)
    return tuple(result)


def prepare_inspection_text(
    source: InspectionText,
    max_width: int,
    max_lines: int,
    measure: TextMeasure,
) -> PreparedInspectionText:
    prepared_pages: list[PreparedInspectionPage] = []
    for raw_page in source.pages:
        wrapped_lines = wrap_japanese_text(raw_page, max_width, measure)
        if not wrapped_lines:
            wrapped_lines = ("",)
        for start in range(0, len(wrapped_lines), max_lines):
            prepared_pages.append(
                PreparedInspectionPage(wrapped_lines[start : start + max_lines])
            )
    if not prepared_pages:
        prepared_pages.append(PreparedInspectionPage(("",)))
    return PreparedInspectionText(source.title, tuple(prepared_pages))
