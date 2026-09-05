from __future__ import annotations

from unittest import TestCase

from three_line_explorer.config import (
    LANE_Z,
    PLAYER_SIZE_Z,
    PLAYER_START_X,
    RIVER_START_Z,
    STAGE_MAX_X,
    STAGE_MIN_X,
    STAGE_MAX_Z,
    STAGE_MIN_Z,
    VISIBLE_SIZE_Z,
)
from three_line_explorer.stage import (
    AREA_LABELS,
    PROTOTYPE_DRIFT_PROP_SLOTS,
    PROTOTYPE_ENVIRONMENT_SPRITE_SLOTS,
    STAGE_AREAS,
    Stage,
    area_label_for_x,
    area_index_for_x,
    stage_area_for_label,
    story_area_index_for_x,
)


class StageLayoutTests(TestCase):
    def test_river_starts_outside_positive_z_lane_footprint(self) -> None:
        self.assertEqual(RIVER_START_Z, LANE_Z[-1] + PLAYER_SIZE_Z * 0.5)

    def test_river_extends_outward_without_adding_lanes(self) -> None:
        self.assertEqual(LANE_Z, (-36.0, 0.0, 36.0))
        self.assertGreaterEqual(STAGE_MAX_Z - RIVER_START_Z, 120.0)
        self.assertEqual(VISIBLE_SIZE_Z, STAGE_MAX_Z - STAGE_MIN_Z)

    def test_river_side_has_no_solid_outside_route(self) -> None:
        stage = Stage.create_prototype()
        for solid in stage.solids:
            if solid.bounds.maximum.z > RIVER_START_Z:
                self.fail(f"river-side solid remains outside route: {solid}")

    def test_river_side_inspectable_props_are_not_collision_solids(self) -> None:
        stage = Stage.create_prototype()
        self.assertGreaterEqual(len(stage.inspectable_props), 1)
        solid_ids = {solid.object_id for solid in stage.solids}
        river_props = [
            prop for prop in stage.inspectable_props if prop.object_id.startswith("river_prop_")
        ]
        self.assertGreaterEqual(len(river_props), 1)
        for prop in river_props:
            self.assertGreaterEqual(prop.bounds.minimum.z, RIVER_START_Z)
            self.assertNotIn(prop.render_object_id, solid_ids)

    def test_environment_sign_is_an_inland_inspectable_without_prop_sprite(self) -> None:
        stage = Stage.create_prototype()
        sign_sprite = next(
            sprite
            for sprite in stage.environment_sprites
            if sprite.sprite_id == "weathered_sign"
        )

        sign = next(
            prop
            for prop in stage.inspectable_props
            if prop.object_id == "environment_weathered_sign"
        )

        self.assertLess(sign.bounds.maximum.z, RIVER_START_Z)
        self.assertEqual(sign.text_key, "weathered_forest_sign")
        self.assertIsNone(sign.sprite_id)
        self.assertEqual(sign.render_object_id, sign_sprite.object_id)
        self.assertEqual(sign.bounds, sign_sprite.bounds)

    def test_prototype_stage_uses_environment_sprites_instead_of_debug_aabbs(self) -> None:
        stage = Stage.create_prototype()
        self.assertEqual(stage.solids, ())
        self.assertGreaterEqual(len(stage.environment_sprites), 1)
        self.assertGreaterEqual(len(stage.collision_solids), 1)
        self.assertLessEqual(len(stage.inspectable_props), 10)

    def test_debug_aabb_stage_is_kept_for_renderer_stress_checks(self) -> None:
        stage = Stage.create_render_test()
        self.assertGreaterEqual(len(stage.solids), 1)
        self.assertEqual(stage.inspectable_props, ())
        self.assertEqual(stage.environment_sprites, ())
        self.assertEqual(stage.collision_solids, ())

    def test_prototype_stage_is_extended_for_long_route(self) -> None:
        self.assertEqual(STAGE_MIN_X, -720.0)
        self.assertEqual(STAGE_MAX_X, 720.0)
        self.assertEqual(STAGE_MAX_X - STAGE_MIN_X, 1440.0)

    def test_stage_area_table_covers_A_to_R(self) -> None:
        self.assertEqual(AREA_LABELS, tuple("ABCDEFGHIJKLMNOPQR"))
        self.assertEqual(tuple(area.label for area in STAGE_AREAS), AREA_LABELS)
        self.assertEqual(STAGE_AREAS[0].x_min, STAGE_MIN_X)
        self.assertEqual(STAGE_AREAS[-1].x_max, STAGE_MAX_X)
        for left, right in zip(STAGE_AREAS, STAGE_AREAS[1:]):
            self.assertEqual(left.x_max, right.x_min)
            self.assertEqual(left.x_max - left.x_min, 80.0)

    def test_physical_area_label_for_x_uses_whole_stage(self) -> None:
        self.assertEqual(area_index_for_x(STAGE_MIN_X), 0)
        self.assertEqual(area_label_for_x(STAGE_MIN_X), "A")
        self.assertEqual(area_label_for_x(PLAYER_START_X), "J")
        self.assertEqual(area_label_for_x(STAGE_MAX_X), "R")

    def test_prototype_drift_props_are_placed_in_area_slots(self) -> None:
        stage = Stage.create_prototype()
        props = [
            prop for prop in stage.inspectable_props if prop.object_id.startswith("river_prop_")
        ]

        self.assertEqual(len(props), len(PROTOTYPE_DRIFT_PROP_SLOTS))
        for prop, slot in zip(props, PROTOTYPE_DRIFT_PROP_SLOTS):
            area = stage_area_for_label(slot.area_label)
            self.assertGreaterEqual(prop.bounds.minimum.x, area.x_min)
            self.assertLessEqual(prop.bounds.maximum.x, area.x_max)

    def test_prototype_environment_sprites_are_placed_in_area_slots(self) -> None:
        stage = Stage.create_prototype()

        self.assertEqual(len(stage.environment_sprites), len(PROTOTYPE_ENVIRONMENT_SPRITE_SLOTS))
        for sprite, slot in zip(stage.environment_sprites, PROTOTYPE_ENVIRONMENT_SPRITE_SLOTS):
            area = stage_area_for_label(slot.area_label)
            self.assertEqual(sprite.sprite_id, slot.sprite_id)
            self.assertGreaterEqual(sprite.bounds.minimum.x, area.x_min)
            self.assertLessEqual(sprite.bounds.maximum.x, area.x_max)

    def test_story_area_index_starts_from_player_route_start(self) -> None:
        self.assertEqual(story_area_index_for_x(PLAYER_START_X), 0)
        self.assertEqual(story_area_index_for_x(STAGE_MAX_X), 17)
