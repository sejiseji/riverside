from __future__ import annotations

from unittest import TestCase

from three_line_explorer.inspection_prop_sprites import (
    ATLAS_H,
    ATLAS_W,
    CELL_H,
    CELL_W,
    SPRITE_DEFINITIONS,
    SPRITE_ORDER,
    TRANSPARENT_DIGIT,
    build_prop_sprite_atlas,
    calculate_sprite_scale,
    compile_sprite_rows,
    validate_all_sprites,
    validate_sprite_rows,
    visible_bounds,
)


class InspectionPropSpriteTests(TestCase):
    def test_all_source_sprites_are_valid(self) -> None:
        validate_all_sprites()

    def test_atlas_dimensions(self) -> None:
        self.assertEqual(CELL_W, 32)
        self.assertEqual(CELL_H, 24)
        self.assertEqual(ATLAS_W, CELL_W * len(SPRITE_ORDER))
        self.assertEqual(ATLAS_H, CELL_H)

    def test_compile_rows_converts_authoring_dots_to_transparent_digit(self) -> None:
        first = SPRITE_DEFINITIONS[SPRITE_ORDER[0]]

        compiled = compile_sprite_rows(first.rows)

        self.assertNotIn(".", "".join(compiled))
        self.assertIn(TRANSPARENT_DIGIT, compiled[0])

    def test_reserved_transparent_digit_is_not_allowed_as_source_color(self) -> None:
        rows = tuple(["." * CELL_W] * CELL_H)
        bad_rows = rows[:12] + ("." * 12 + TRANSPARENT_DIGIT + "." * 19,) + rows[13:]

        with self.assertRaises(ValueError):
            validate_sprite_rows(SPRITE_ORDER[0], bad_rows)

    def test_visible_bounds_detects_bottom_anchor(self) -> None:
        for definition in SPRITE_DEFINITIONS.values():
            min_x, min_y, max_x, max_y = visible_bounds(definition.rows)
            self.assertGreaterEqual(min_x, 0)
            self.assertGreaterEqual(min_y, 0)
            self.assertLess(max_x, CELL_W)
            self.assertLess(max_y, CELL_H)

    def test_build_atlas_writes_all_sprite_cells(self) -> None:
        pyxel = FakePyxel()

        atlas = build_prop_sprite_atlas(pyxel)

        self.assertEqual(pyxel.image.size, (ATLAS_W, ATLAS_H))
        self.assertEqual(len(pyxel.image.set_calls), len(SPRITE_ORDER))
        for index, sprite_id in enumerate(SPRITE_ORDER):
            region = atlas.regions[sprite_id]
            self.assertEqual(region.u, index * CELL_W)
            self.assertEqual(region.v, 0)
            self.assertEqual(region.width, CELL_W)
            self.assertEqual(region.height, CELL_H)
            self.assertGreater(region.world_width, 0.0)

    def test_sprite_scale_is_clamped(self) -> None:
        self.assertEqual(
            calculate_sprite_scale(100.0, 100.0, 32.0, 32, minimum=0.5, maximum=1.5),
            1.0,
        )
        self.assertEqual(
            calculate_sprite_scale(100.0, 1000.0, 32.0, 32, minimum=0.5, maximum=1.5),
            0.5,
        )
        self.assertEqual(
            calculate_sprite_scale(1000.0, 10.0, 32.0, 32, minimum=0.5, maximum=1.5),
            1.5,
        )


class FakeImage:
    def __init__(self, width: int, height: int) -> None:
        self.size = (width, height)
        self.clear_color: int | None = None
        self.set_calls: list[tuple[int, int, list[str]]] = []

    def cls(self, color: int) -> None:
        self.clear_color = color

    def set(self, x: int, y: int, rows: list[str]) -> None:
        self.set_calls.append((x, y, rows))


class FakePyxel:
    def Image(self, width: int, height: int) -> FakeImage:
        self.image = FakeImage(width, height)
        return self.image
