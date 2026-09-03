"""Validation helpers for source-defined Pyxel color maps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


HEX_DIGITS: Final = "0123456789abcdef"


@dataclass(frozen=True, slots=True)
class PixelMapSource:
    width: int
    height: int
    rows: tuple[str, ...]
    transparent_color: int | None


def valid_source_chars(transparent_color: int | None) -> frozenset[str]:
    if transparent_color is None:
        return frozenset(HEX_DIGITS)

    digit = palette_digit(transparent_color)
    return frozenset("." + HEX_DIGITS.replace(digit, ""))


def palette_digit(index: int) -> str:
    if index < 0 or index > 15:
        raise ValueError(f"Pyxel palette index must be 0..15, got {index}")
    return f"{index:x}"


def validate_pixel_map(
    *,
    asset_id: str,
    rows: tuple[str, ...],
    width: int,
    height: int,
    transparent_color: int | None,
) -> None:
    if width <= 0:
        raise ValueError(f"{asset_id}: width must be positive, got {width}")
    if height <= 0:
        raise ValueError(f"{asset_id}: height must be positive, got {height}")

    allowed = valid_source_chars(transparent_color)
    if len(rows) != height:
        raise ValueError(f"{asset_id}: expected {height} rows, got {len(rows)}")

    visible_count = 0
    for y, row in enumerate(rows):
        if len(row) != width:
            raise ValueError(f"{asset_id}: row {y} must be {width} chars, got {len(row)}")
        invalid = set(row) - allowed
        if invalid:
            raise ValueError(f"{asset_id}: invalid chars at row {y}: {sorted(invalid)}")
        if transparent_color is None:
            visible_count += len(row)
        else:
            visible_count += sum(char != "." for char in row)

    if visible_count == 0:
        raise ValueError(f"{asset_id}: pixel map is fully transparent")


def compile_pixel_rows(
    rows: tuple[str, ...],
    transparent_color: int | None,
) -> list[str]:
    if transparent_color is None:
        return list(rows)
    return [row.replace(".", palette_digit(transparent_color)) for row in rows]
