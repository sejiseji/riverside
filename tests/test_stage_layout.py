from __future__ import annotations

from unittest import TestCase

from three_line_explorer.config import (
    LANE_Z,
    PLAYER_SIZE_Z,
    PLAYER_START_X,
    RIVER_START_Z,
    STAGE_MAX_Z,
    STAGE_MIN_Z,
    VISIBLE_SIZE_Z,
)
from three_line_explorer.stage import Stage, story_area_index_for_x


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

        sign = next(
            prop
            for prop in stage.inspectable_props
            if prop.object_id == "environment_weathered_sign"
        )

        self.assertLess(sign.bounds.maximum.z, RIVER_START_Z)
        self.assertEqual(sign.text_key, "weathered_forest_sign")
        self.assertIsNone(sign.sprite_id)

    def test_prototype_stage_keeps_prop_count_small(self) -> None:
        stage = Stage.create_prototype()
        self.assertLessEqual(len(stage.solids), 12)
        self.assertLessEqual(len(stage.inspectable_props), 10)

    def test_story_area_index_starts_from_player_route_start(self) -> None:
        self.assertEqual(story_area_index_for_x(PLAYER_START_X), 0)
        self.assertEqual(story_area_index_for_x(480.0), 17)
