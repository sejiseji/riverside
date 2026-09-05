from __future__ import annotations

from unittest import TestCase

from three_line_explorer.blit_anchor import anchored_blt_origin, transformed_anchor


class BlitAnchorTests(TestCase):
    def test_anchor_round_trips_at_scaled_pyxel_center_pivot(self) -> None:
        for scale in (0.5, 0.85, 1.0, 1.5, 1.65):
            origin_x, origin_y = anchored_blt_origin(
                screen_x=160.0,
                screen_y=128.0,
                width=48,
                height=64,
                anchor_x=24.0,
                anchor_y=60.0,
                scale=scale,
            )

            anchor_x, anchor_y = transformed_anchor(
                origin_x=origin_x,
                origin_y=origin_y,
                width=48,
                height=64,
                anchor_x=24.0,
                anchor_y=60.0,
                scale=scale,
            )

            self.assertAlmostEqual(anchor_x, 160.0, delta=0.5)
            self.assertAlmostEqual(anchor_y, 128.0, delta=0.5)

    def test_scale_one_matches_top_left_anchor_math(self) -> None:
        self.assertEqual(
            anchored_blt_origin(
                screen_x=160.0,
                screen_y=128.0,
                width=48,
                height=64,
                anchor_x=24.0,
                anchor_y=60.0,
                scale=1.0,
            ),
            (136, 68),
        )

    def test_non_unit_scale_keeps_source_center_pivot_offset(self) -> None:
        self.assertEqual(
            anchored_blt_origin(
                screen_x=160.0,
                screen_y=128.0,
                width=48,
                height=64,
                anchor_x=24.0,
                anchor_y=60.0,
                scale=1.65,
            ),
            (136, 49),
        )
