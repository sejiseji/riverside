from __future__ import annotations

from unittest import TestCase

from three_line_explorer.config import RIVER_START_Z
from three_line_explorer.stage import Stage


class StageLayoutTests(TestCase):
    def test_river_side_has_no_solid_outside_route(self) -> None:
        stage = Stage.create_prototype()
        for solid in stage.solids:
            if solid.bounds.maximum.z > RIVER_START_Z:
                self.fail(f"river-side solid remains outside route: {solid}")

    def test_prototype_stage_keeps_prop_count_small(self) -> None:
        stage = Stage.create_prototype()
        self.assertLessEqual(len(stage.solids), 12)
