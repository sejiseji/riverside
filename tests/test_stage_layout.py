from __future__ import annotations

from unittest import TestCase

from three_line_explorer.config import LANE_Z, PLAYER_SIZE_Z
from three_line_explorer.stage import Stage


class StageLayoutTests(TestCase):
    def test_river_side_has_no_long_horizontal_solid(self) -> None:
        stage = Stage.create_prototype()
        for solid in stage.solids:
            size = solid.bounds.size
            if solid.bounds.minimum.z >= 44.0 and size.x > 100.0:
                self.fail(f"long horizontal river-side solid remains: {solid}")

    def test_riverbank_keeps_positive_z_lane_clear(self) -> None:
        stage = Stage.create_prototype()
        positive_lane_outer_edge = LANE_Z[-1] + PLAYER_SIZE_Z * 0.5
        for solid in stage.solids:
            if solid.bounds.maximum.z > positive_lane_outer_edge:
                self.assertGreaterEqual(solid.bounds.minimum.z, positive_lane_outer_edge)

    def test_riverbank_has_flat_water_panels(self) -> None:
        stage = Stage.create_prototype()
        water_panels = [
            solid
            for solid in stage.solids
            if solid.bounds.minimum.z >= 52.0
            and solid.bounds.size.y <= 1.0
            and solid.top_color == 12
        ]
        self.assertGreaterEqual(len(water_panels), 6)
