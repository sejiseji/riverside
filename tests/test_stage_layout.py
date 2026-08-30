from __future__ import annotations

from unittest import TestCase

from three_line_explorer.config import (
    LANE_Z,
    PLAYER_SIZE_Z,
    RIVER_START_Z,
    STAGE_MAX_Z,
    STAGE_MIN_Z,
    VISIBLE_SIZE_Z,
)
from three_line_explorer.stage import Stage


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

    def test_prototype_stage_keeps_prop_count_small(self) -> None:
        stage = Stage.create_prototype()
        self.assertLessEqual(len(stage.solids), 12)
