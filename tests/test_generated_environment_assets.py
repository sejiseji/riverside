from __future__ import annotations

import unittest

from three_line_explorer.generated_environment_assets import (
    PARALLAX_SEQUENCES,
    PARALLAX_TILES,
    WORLD_SPRITES,
    ParallaxLayer,
    PixelMapSpec,
    WorldSpriteKind,
    allowed_source_chars,
    compile_rows,
    validate_all_assets,
    validate_pixel_map,
)


class GeneratedEnvironmentAssetTests(unittest.TestCase):
    def test_all_assets_validate(self) -> None:
        validate_all_assets()

    def test_parallax_pack_has_four_tiles_per_layer(self) -> None:
        expected_sizes = {
            ParallaxLayer.FAR: (64, 32),
            ParallaxLayer.MID: (64, 48),
            ParallaxLayer.NEAR: (64, 64),
        }
        self.assertEqual(len(PARALLAX_TILES), 12)

        for layer, expected_size in expected_sizes.items():
            sequence = PARALLAX_SEQUENCES[layer]
            self.assertEqual(len(sequence), 4)
            indexes = {
                PARALLAX_TILES[asset_id].sequence_index
                for asset_id in sequence
            }
            self.assertEqual(indexes, {0, 1, 2, 3})
            for asset_id in sequence:
                tile = PARALLAX_TILES[asset_id]
                self.assertEqual(
                    (tile.source.width, tile.source.height),
                    expected_size,
                )
                self.assertEqual(tile.source.transparent_color, 8)

    def test_world_pack_contains_required_objects(self) -> None:
        required = {
            "dead_tree_trunk",
            "mossy_rock",
            "weathered_sign",
            "jizo",
            "grass_tuft",
            "fern",
            "bracken",
            "butterbur",
            "horsetail",
            "sapling",
        }
        self.assertEqual(set(WORLD_SPRITES), required)

    def test_only_sign_is_inspectable_in_initial_pack(self) -> None:
        inspectable = {
            asset_id
            for asset_id, sprite in WORLD_SPRITES.items()
            if sprite.inspectable_text_key is not None
        }
        self.assertEqual(inspectable, {"weathered_sign"})
        self.assertEqual(
            WORLD_SPRITES["weathered_sign"].kind,
            WorldSpriteKind.SOLID_INSPECTABLE,
        )

    def test_collision_contract_matches_sprite_kind(self) -> None:
        for sprite in WORLD_SPRITES.values():
            collidable = sprite.kind in {
                WorldSpriteKind.SOLID,
                WorldSpriteKind.SOLID_INSPECTABLE,
            }
            if collidable:
                self.assertGreater(sprite.collision_half_x, 0)
                self.assertGreater(sprite.collision_half_z, 0)
            else:
                self.assertEqual(sprite.collision_half_x, 0)
                self.assertEqual(sprite.collision_half_z, 0)

    def test_sprite_anchor_is_on_visible_bottom(self) -> None:
        for sprite in WORLD_SPRITES.values():
            points = [
                (x, y)
                for y, row in enumerate(sprite.source.rows)
                for x, char in enumerate(row)
                if char != "."
            ]
            min_x = min(x for x, _ in points)
            max_x = max(x for x, _ in points)
            max_y = max(y for _, y in points)
            self.assertEqual(sprite.anchor_y, max_y)
            self.assertGreaterEqual(sprite.anchor_x, min_x)
            self.assertLessEqual(sprite.anchor_x, max_x)

    def test_local_transparent_color_only_reserves_its_own_digit(self) -> None:
        chars = allowed_source_chars(2)
        self.assertNotIn("2", chars)
        self.assertIn("8", chars)

        source = PixelMapSpec(
            asset_id="local_colkey_example",
            width=2,
            height=1,
            rows=(".8",),
            transparent_color=2,
        )
        validate_pixel_map(source)
        self.assertEqual(compile_rows(source), ["28"])

    def test_transparent_digit_cannot_be_visible_in_same_asset(self) -> None:
        source = PixelMapSpec(
            asset_id="invalid_visible_colkey",
            width=1,
            height=1,
            rows=("8",),
            transparent_color=8,
        )
        with self.assertRaises(ValueError):
            validate_pixel_map(source)

    def test_compiled_rows_contain_only_hex_digits(self) -> None:
        all_sources = [
            *(tile.source for tile in PARALLAX_TILES.values()),
            *(sprite.source for sprite in WORLD_SPRITES.values()),
        ]
        for source in all_sources:
            compiled = compile_rows(source)
            for row in compiled:
                self.assertFalse(set(row) - set("0123456789abcdef"))

    def test_source_maps_have_no_uppercase_or_whitespace(self) -> None:
        all_sources = [
            *(tile.source for tile in PARALLAX_TILES.values()),
            *(sprite.source for sprite in WORLD_SPRITES.values()),
        ]
        for source in all_sources:
            for row in source.rows:
                self.assertEqual(row, row.strip())
                self.assertEqual(row, row.lower())


if __name__ == "__main__":
    unittest.main()
