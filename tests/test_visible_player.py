from __future__ import annotations

from unittest import TestCase

from three_line_explorer.config import (
    DT,
    LANE_Z,
    PLAYER_SIZE_X,
    STAGE_MAX_X,
    STAGE_MIN_X,
    VISIBLE_SIZE_X,
)
from three_line_explorer.player import (
    change_lane_by_world_step,
    create_player,
    player_max_x,
    player_min_x,
    update_player,
)
from three_line_explorer.visible_volume import update_visible_volume


class VisibleVolumeTests(TestCase):
    def test_center_tracks_player_in_middle(self) -> None:
        volume = update_visible_volume(0.0)
        self.assertEqual(volume.center_x, 0.0)

    def test_left_and_right_clamp_to_stage(self) -> None:
        left = update_visible_volume(STAGE_MIN_X)
        right = update_visible_volume(STAGE_MAX_X)
        self.assertEqual(left.bounds.minimum.x, STAGE_MIN_X)
        self.assertEqual(right.bounds.maximum.x, STAGE_MAX_X)
        self.assertEqual(left.center_x, STAGE_MIN_X + VISIBLE_SIZE_X * 0.5)
        self.assertEqual(right.center_x, STAGE_MAX_X - VISIBLE_SIZE_X * 0.5)

    def test_player_can_leave_visible_center_near_edge(self) -> None:
        player = create_player()
        player.x = player_max_x()
        volume = update_visible_volume(player.x)
        self.assertNotEqual(player.x, volume.center_x)
        self.assertLessEqual(player.x + PLAYER_SIZE_X * 0.5, STAGE_MAX_X)


class PlayerTests(TestCase):
    def test_player_accelerates_and_clamps_to_stage(self) -> None:
        player = create_player()
        update_player(player, 1.0, dt=DT)
        self.assertGreater(player.x, 0.0)
        self.assertEqual(player.facing, 1)

        player.x = STAGE_MAX_X
        update_player(player, 1.0, dt=DT)
        self.assertEqual(player.x, player_max_x())

        player.x = STAGE_MIN_X
        update_player(player, -1.0, dt=DT)
        self.assertEqual(player.x, player_min_x())

    def test_line_target_clamps_and_z_moves_continuously(self) -> None:
        player = create_player()
        change_lane_by_world_step(player, 10)
        self.assertEqual(player.target_lane_index, 2)
        before_z = player.z
        update_player(player, 0.0, dt=DT)
        self.assertGreater(player.z, before_z)
        self.assertLess(player.z, LANE_Z[2])

        change_lane_by_world_step(player, -10)
        self.assertEqual(player.target_lane_index, 0)
        before_z = player.z
        update_player(player, 0.0, dt=DT)
        self.assertLess(player.z, before_z)
