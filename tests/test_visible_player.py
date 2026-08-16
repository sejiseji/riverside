from __future__ import annotations

from unittest import TestCase

from three_line_explorer.config import (
    DT,
    LANE_TURN_DELAY_SECONDS,
    LANE_Z,
    PLAYER_SIZE_X,
    PLAYER_SIZE_Z,
    STAGE_MAX_X,
    STAGE_MIN_X,
    VISIBLE_SIZE_X,
)
from three_line_explorer.geometry import AabbSolid
from three_line_explorer.math3d import AABB, Vec3
from three_line_explorer.player import (
    change_lane_by_world_step,
    create_player,
    player_bounds_at,
    player_max_x,
    player_min_x,
    request_lane_change_by_world_step,
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
    def test_player_bounds_use_contact_center_position(self) -> None:
        player = create_player()
        bounds = player_bounds_at(player.x, player.z)
        self.assertEqual(bounds.minimum.x, -PLAYER_SIZE_X * 0.5)
        self.assertEqual(bounds.maximum.x, PLAYER_SIZE_X * 0.5)
        self.assertEqual(bounds.minimum.y, 0.0)

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

    def test_requested_line_change_turns_before_lane_target_changes(self) -> None:
        player = create_player()

        request_lane_change_by_world_step(player, 1)
        self.assertEqual(player.target_lane_index, 1)
        self.assertEqual(player.pending_lane_step, 1)
        self.assertLess(player.target_yaw, 0.0)

        update_player(player, 0.0, dt=DT)
        self.assertEqual(player.target_lane_index, 1)

        frames = int(LANE_TURN_DELAY_SECONDS / DT) + 2
        for _ in range(frames):
            update_player(player, 0.0, dt=DT)

        self.assertEqual(player.target_lane_index, 2)
        self.assertGreater(player.z, LANE_Z[1])

    def test_forward_collision_stops_at_blocking_solid(self) -> None:
        player = create_player()
        blocker = _test_solid((28.0, 0.0, -8.0), (40.0, 30.0, 8.0))

        update_player(player, 1.0, dt=1.0, collision_provider=lambda _bounds: (blocker,))

        self.assertEqual(player.x, 28.0 - PLAYER_SIZE_X * 0.5)
        self.assertEqual(player.velocity_x, 0.0)
        self.assertEqual(player.facing, 1)

    def test_backward_collision_stops_at_blocking_solid(self) -> None:
        player = create_player()
        blocker = _test_solid((-40.0, 0.0, -8.0), (-28.0, 30.0, 8.0))

        update_player(player, -1.0, dt=1.0, collision_provider=lambda _bounds: (blocker,))

        self.assertEqual(player.x, -28.0 + PLAYER_SIZE_X * 0.5)
        self.assertEqual(player.velocity_x, 0.0)
        self.assertEqual(player.facing, -1)

    def test_forward_collision_ignores_solid_on_other_lane(self) -> None:
        player = create_player()
        other_lane_blocker = _test_solid((28.0, 0.0, 20.0), (40.0, 30.0, 34.0))

        update_player(
            player,
            1.0,
            dt=1.0,
            collision_provider=lambda _bounds: (other_lane_blocker,),
        )

        self.assertGreater(player.x, 28.0 - PLAYER_SIZE_X * 0.5)

    def test_lane_collision_stops_at_blocking_solid(self) -> None:
        player = create_player()
        blocker = _test_solid((-8.0, 0.0, 18.0), (8.0, 30.0, 40.0))
        change_lane_by_world_step(player, 1)

        update_player(player, 0.0, dt=1.0, collision_provider=lambda _bounds: (blocker,))

        self.assertEqual(player.z, 18.0 - PLAYER_SIZE_Z * 0.5)
        self.assertEqual(player.target_lane_index, 2)


def _test_solid(minimum: tuple[float, float, float], maximum: tuple[float, float, float]) -> AabbSolid:
    return AabbSolid(
        object_id=999,
        bounds=AABB(Vec3(*minimum), Vec3(*maximum)),
        side_color=1,
        top_color=1,
        outline_color=0,
    )
