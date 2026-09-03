from __future__ import annotations

from unittest import TestCase

from three_line_explorer.pixel_map_source import (
    HEX_DIGITS,
    compile_pixel_rows,
    palette_digit,
    valid_source_chars,
    validate_pixel_map,
)


class PixelMapSourceTests(TestCase):
    def test_valid_source_chars_exclude_reserved_transparent_digit(self) -> None:
        chars = valid_source_chars(8)

        self.assertIn(".", chars)
        self.assertIn("7", chars)
        self.assertIn("9", chars)
        self.assertNotIn("8", chars)

    def test_opaque_source_chars_allow_all_palette_digits_but_no_dot(self) -> None:
        chars = valid_source_chars(None)

        self.assertEqual(chars, frozenset(HEX_DIGITS))
        self.assertNotIn(".", chars)

    def test_transparent_map_rejects_reserved_visible_color(self) -> None:
        with self.assertRaises(ValueError):
            validate_pixel_map(
                asset_id="bad_prop",
                rows=("18", ".."),
                width=2,
                height=2,
                transparent_index=8,
            )

    def test_transparent_map_compiles_dots_to_reserved_color(self) -> None:
        rows = ("1.", ".7")

        compiled = compile_pixel_rows(rows, 8)

        self.assertEqual(compiled, ["18", "87"])

    def test_opaque_map_rejects_dot(self) -> None:
        with self.assertRaises(ValueError):
            validate_pixel_map(
                asset_id="bad_sky",
                rows=("1.", "77"),
                width=2,
                height=2,
                transparent_index=None,
            )

    def test_uppercase_hex_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_pixel_map(
                asset_id="bad_case",
                rows=("1A", "77"),
                width=2,
                height=2,
                transparent_index=None,
            )

    def test_fully_transparent_map_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_pixel_map(
                asset_id="empty",
                rows=("..", ".."),
                width=2,
                height=2,
                transparent_index=8,
            )

    def test_palette_digit_range(self) -> None:
        self.assertEqual(palette_digit(10), "a")
        with self.assertRaises(ValueError):
            palette_digit(16)
