from __future__ import annotations

from unittest import TestCase

from three_line_explorer.config import ENVIRONMENT_OBJECT_ID_BASE
from three_line_explorer.environment_sprites import (
    build_environment_sprite_atlas,
    make_environment_sprite_instance,
)
from three_line_explorer.generated_environment_assets import WORLD_SPRITES
from three_line_explorer.stage import Stage


class EnvironmentSpriteTests(TestCase):
    def test_atlas_contains_all_generated_world_sprites(self) -> None:
        atlas = build_environment_sprite_atlas(FakePyxel())

        self.assertEqual(set(atlas.regions), set(WORLD_SPRITES))
        self.assertGreater(atlas.image.width, 0)
        self.assertGreater(atlas.image.height, 0)
        self.assertEqual(len(atlas.image.set_calls), len(WORLD_SPRITES))

    def test_collidable_sprite_instance_gets_collision_bounds(self) -> None:
        sprite = make_environment_sprite_instance(
            object_id=ENVIRONMENT_OBJECT_ID_BASE + 1,
            sprite_id="mossy_rock",
            x=10.0,
            z=-20.0,
        )

        self.assertIsNotNone(sprite.collision_bounds)
        assert sprite.collision_bounds is not None
        self.assertLess(sprite.collision_bounds.minimum.x, 10.0)
        self.assertGreater(sprite.collision_bounds.maximum.x, 10.0)

    def test_non_collidable_sprite_instance_has_no_collision_bounds(self) -> None:
        sprite = make_environment_sprite_instance(
            object_id=ENVIRONMENT_OBJECT_ID_BASE + 5,
            sprite_id="grass_tuft",
            x=10.0,
            z=-50.0,
        )

        self.assertIsNone(sprite.collision_bounds)

    def test_stage_collision_candidates_include_environment_solids(self) -> None:
        stage = Stage.create_prototype()
        sign = next(
            sprite
            for sprite in stage.environment_sprites
            if sprite.sprite_id == "weathered_sign"
        )

        candidates = stage.candidate_collision_solids(sign.bounds)

        self.assertIn(sign.object_id, {solid.object_id for solid in candidates})
        self.assertNotIn(sign.object_id, {solid.object_id for solid in stage.solids})


class FakeImage:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.clear_color: int | None = None
        self.set_calls: list[tuple[int, int, tuple[str, ...]]] = []

    def cls(self, color: int) -> None:
        self.clear_color = color

    def set(self, x: int, y: int, rows: list[str]) -> None:
        self.set_calls.append((x, y, tuple(rows)))


class FakePyxel:
    Image = FakeImage
