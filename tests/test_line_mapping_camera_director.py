from __future__ import annotations

from unittest import TestCase

from three_line_explorer.camera import (
    CAMERA_SHOTS,
    compute_lane_screen_x,
    compute_lane_screen_y,
    compute_move_screen_x_delta,
    make_camera_snapshot,
    update_stable_lane_orientation,
    update_stable_move_orientation,
)
from three_line_explorer.camera_director import CameraDirector
from three_line_explorer.config import CameraShotId
from three_line_explorer.player import create_player
from three_line_explorer.stage import Stage


class LineMappingTests(TestCase):
    def test_initial_camera_projection_matches_screen_axes(self) -> None:
        player = create_player()

        shot_a = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], player.x, player.z)
        shot_b = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.FRONT_RIGHT_CLOSE], player.x, player.z)
        shot_c = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_LEFT_SHALLOW], player.x, player.z)

        a_lane_x = compute_lane_screen_x(shot_a, player.x)
        b_lane_x = compute_lane_screen_x(shot_b, player.x)
        c_lane_x = compute_lane_screen_x(shot_c, player.x)
        a_lane_y = compute_lane_screen_y(shot_a, player.x)
        b_lane_y = compute_lane_screen_y(shot_b, player.x)
        c_lane_y = compute_lane_screen_y(shot_c, player.x)

        self.assertGreater(a_lane_x[2] - a_lane_x[0], 0.0)
        self.assertLess(b_lane_x[2] - b_lane_x[0], 0.0)
        self.assertGreater(c_lane_x[2] - c_lane_x[0], 0.0)
        self.assertGreater(a_lane_y[2] - a_lane_y[0], 0.0)
        self.assertGreater(b_lane_y[2] - b_lane_y[0], 0.0)
        self.assertLess(c_lane_y[2] - c_lane_y[0], 0.0)
        self.assertGreater(compute_move_screen_x_delta(shot_a, player.x, player.z), 0.0)
        self.assertGreater(compute_move_screen_x_delta(shot_b, player.x, player.z), 0.0)
        self.assertLess(compute_move_screen_x_delta(shot_c, player.x, player.z), 0.0)

    def test_horizontal_move_mapping_uses_hysteresis(self) -> None:
        self.assertEqual(update_stable_move_orientation(1, 20.0), 1)
        self.assertEqual(update_stable_move_orientation(1, 0.0), 1)
        self.assertEqual(update_stable_move_orientation(1, -20.0), -1)

        self.assertEqual(update_stable_move_orientation(-1, -20.0), -1)
        self.assertEqual(update_stable_move_orientation(-1, 0.0), -1)
        self.assertEqual(update_stable_move_orientation(-1, 20.0), 1)

    def test_vertical_lane_mapping_uses_hysteresis(self) -> None:
        self.assertEqual(update_stable_lane_orientation(1, (20.0, 10.0, 0.0)), 1)
        self.assertEqual(update_stable_lane_orientation(1, (0.0, 0.0, 0.0)), 1)
        self.assertEqual(update_stable_lane_orientation(1, (0.0, 10.0, 20.0)), -1)

        self.assertEqual(update_stable_lane_orientation(-1, (0.0, 10.0, 20.0)), -1)
        self.assertEqual(update_stable_lane_orientation(-1, (0.0, 0.0, 0.0)), -1)
        self.assertEqual(update_stable_lane_orientation(-1, (20.0, 10.0, 0.0)), 1)


class CameraDirectorTests(TestCase):
    def test_forced_zone_discards_manual_and_restores_last_manual(self) -> None:
        stage = Stage.create_prototype()
        director = CameraDirector()
        default_rule, _ = stage.active_camera_rule(0.0, 1)

        self.assertEqual(
            director.resolve(default_rule, CameraShotId.REAR_LEFT_SHALLOW, CameraShotId.REAR_RIGHT_LOW),
            CameraShotId.REAR_LEFT_SHALLOW,
        )

        forced_rule, forced_label = stage.active_camera_rule(160.0, 1)
        self.assertEqual(forced_label, "FORCED_B")
        self.assertEqual(
            director.resolve(forced_rule, CameraShotId.REAR_RIGHT_LOW, CameraShotId.REAR_LEFT_SHALLOW),
            CameraShotId.FRONT_RIGHT_CLOSE,
        )
        self.assertEqual(director.last_manual_shot, CameraShotId.REAR_LEFT_SHALLOW)

        restored = director.resolve(default_rule, None, CameraShotId.FRONT_RIGHT_CLOSE)
        self.assertEqual(restored, CameraShotId.REAR_LEFT_SHALLOW)

    def test_allowed_zone_excludes_front_right_close(self) -> None:
        stage = Stage.create_prototype()
        director = CameraDirector()
        rule, label = stage.active_camera_rule(-200.0, 1)
        self.assertEqual(label, "ALLOW_A_C")
        self.assertEqual(
            director.resolve(rule, CameraShotId.FRONT_RIGHT_CLOSE, CameraShotId.REAR_RIGHT_LOW),
            CameraShotId.REAR_RIGHT_LOW,
        )
