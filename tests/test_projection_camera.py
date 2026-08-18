from __future__ import annotations

from math import isfinite
from unittest import TestCase

from three_line_explorer.camera import CAMERA_SHOTS, make_camera_snapshot
from three_line_explorer.config import CameraShotId
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
