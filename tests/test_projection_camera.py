from __future__ import annotations

from math import isfinite
from unittest import TestCase

from three_line_explorer.camera import (
    CAMERA_SHOTS,
    apply_left_edge_camera_blend,
    compute_move_screen_x_delta,
    left_edge_camera_blend_factor,
    make_camera_snapshot,
)
from three_line_explorer.config import (
    CameraShotId,
    LEFT_EDGE_CAMERA_BLEND_START_X,
    LEFT_EDGE_CAMERA_TARGET_DISTANCE,
    STAGE_MIN_X,
)
from three_line_explorer.math3d import Vec3
from three_line_explorer.projection import project_world_point, world_to_camera


class ProjectionCameraTests(TestCase):
    def test_camera_pivot_projects_to_screen_center(self) -> None:
        snapshot = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], 0.0, 0.0)
        projected = project_world_point(snapshot, snapshot.pivot)
        self.assertIsNotNone(projected)
        assert projected is not None
        self.assertAlmostEqual(projected.x, snapshot.screen_center_x)
        self.assertAlmostEqual(projected.y, snapshot.screen_center_y)

    def test_camera_basis_projects_right_and_up(self) -> None:
        snapshot = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], 0.0, 0.0)
        center = project_world_point(snapshot, snapshot.pivot)
        right = project_world_point(snapshot, snapshot.pivot + snapshot.right * 10.0)
        up = project_world_point(snapshot, snapshot.pivot + snapshot.up * 10.0)
        assert center is not None and right is not None and up is not None
        self.assertGreater(right.x, center.x)
        self.assertLess(up.y, center.y)

    def test_camera_basis_is_orthogonal(self) -> None:
        snapshot = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], 0.0, 0.0)
        self.assertAlmostEqual(snapshot.forward.dot(snapshot.right), 0.0, places=6)
        self.assertAlmostEqual(snapshot.forward.dot(snapshot.up), 0.0, places=6)
        self.assertAlmostEqual(snapshot.right.dot(snapshot.up), 0.0, places=6)

    def test_near_plane_rejects_behind_points(self) -> None:
        snapshot = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], 0.0, 0.0)
        camera_point = Vec3(0.0, 0.0, -5.0)
        world_point = (
            snapshot.position
            + snapshot.right * camera_point.x
            + snapshot.up * camera_point.y
            + snapshot.forward * camera_point.z
        )
        self.assertIsNone(project_world_point(snapshot, world_point))

    def test_all_shots_generate_finite_camera_space(self) -> None:
        for shot_id, params in CAMERA_SHOTS.items():
            snapshot = make_camera_snapshot(params, 0.0, 0.0, shot_id=shot_id)
            camera_point = world_to_camera(snapshot, snapshot.pivot)
            self.assertTrue(isfinite(camera_point.z))
            self.assertGreater(camera_point.z, 0.0)

    def test_right_side_wide_shot_stays_on_right_side(self) -> None:
        snapshot = make_camera_snapshot(
            CAMERA_SHOTS[CameraShotId.RIGHT_SIDE_WIDE],
            0.0,
            0.0,
            shot_id=CameraShotId.RIGHT_SIDE_WIDE,
        )

        self.assertGreater(snapshot.position.z, snapshot.pivot.z)
        self.assertLess(abs(snapshot.position.x - snapshot.pivot.x), 40.0)

    def test_left_edge_camera_blend_starts_partway_to_stage_edge(self) -> None:
        self.assertEqual(left_edge_camera_blend_factor(0.0), 0.0)
        self.assertEqual(left_edge_camera_blend_factor(LEFT_EDGE_CAMERA_BLEND_START_X), 0.0)
        self.assertEqual(left_edge_camera_blend_factor(STAGE_MIN_X), 1.0)

    def test_left_edge_camera_blend_orbits_and_zooms(self) -> None:
        base = CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW]
        mid_x = (LEFT_EDGE_CAMERA_BLEND_START_X + STAGE_MIN_X) * 0.5
        blended = apply_left_edge_camera_blend(base, mid_x)
        final = apply_left_edge_camera_blend(base, STAGE_MIN_X)
        final_snapshot = make_camera_snapshot(final, STAGE_MIN_X, 0.0)

        self.assertLess(blended.distance, base.distance)
        self.assertLess(final.distance, blended.distance)
        self.assertEqual(final.distance, LEFT_EDGE_CAMERA_TARGET_DISTANCE)
        self.assertNotEqual(blended.azimuth, base.azimuth)
        self.assertGreater(final_snapshot.position.z, final_snapshot.pivot.z)
        self.assertGreater(compute_move_screen_x_delta(final_snapshot, STAGE_MIN_X, 0.0), 0.0)
