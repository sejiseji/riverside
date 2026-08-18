from __future__ import annotations

from unittest import TestCase

from three_line_explorer.camera import CAMERA_SHOTS, make_camera_snapshot
from three_line_explorer.config import CameraShotId
from three_line_explorer.math3d import Vec3
from three_line_explorer.renderer import _face_sort_depth, _object_sort_depths


class RendererTests(TestCase):
    def test_face_sort_depth_uses_nearest_point(self) -> None:
        points = (
            Vec3(0.0, 0.0, 40.0),
            Vec3(0.0, 0.0, 10.0),
            Vec3(0.0, 0.0, 20.0),
            Vec3(0.0, 0.0, 30.0),
        )

        self.assertEqual(_face_sort_depth(points), 10.0)

    def test_object_sort_depths_follow_camera_line_depth(self) -> None:
        shot_a = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], 0.0, 0.0)
        negative_z_depth, _ = _object_sort_depths(Vec3(0.0, 0.0, -36.0), shot_a)
        positive_z_depth, _ = _object_sort_depths(Vec3(0.0, 0.0, 36.0), shot_a)
        self.assertGreater(negative_z_depth, positive_z_depth)

        shot_b = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.FRONT_RIGHT_CLOSE], 0.0, 0.0)
        negative_z_depth, _ = _object_sort_depths(Vec3(0.0, 0.0, -36.0), shot_b)
        positive_z_depth, _ = _object_sort_depths(Vec3(0.0, 0.0, 36.0), shot_b)
        self.assertGreater(negative_z_depth, positive_z_depth)

        shot_c = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_LEFT_SHALLOW], 0.0, 0.0)
        negative_z_depth, _ = _object_sort_depths(Vec3(0.0, 0.0, -36.0), shot_c)
        positive_z_depth, _ = _object_sort_depths(Vec3(0.0, 0.0, 36.0), shot_c)
        self.assertGreater(positive_z_depth, negative_z_depth)

    def test_object_sort_depths_follow_camera_route_depth(self) -> None:
        shot_a = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], 0.0, 0.0)
        _, negative_x_depth = _object_sort_depths(Vec3(-40.0, 0.0, 0.0), shot_a)
        _, positive_x_depth = _object_sort_depths(Vec3(40.0, 0.0, 0.0), shot_a)
        self.assertGreater(positive_x_depth, negative_x_depth)

        shot_b = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.FRONT_RIGHT_CLOSE], 0.0, 0.0)
        _, negative_x_depth = _object_sort_depths(Vec3(-40.0, 0.0, 0.0), shot_b)
        _, positive_x_depth = _object_sort_depths(Vec3(40.0, 0.0, 0.0), shot_b)
        self.assertGreater(negative_x_depth, positive_x_depth)

        shot_c = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_LEFT_SHALLOW], 0.0, 0.0)
        _, negative_x_depth = _object_sort_depths(Vec3(-40.0, 0.0, 0.0), shot_c)
        _, positive_x_depth = _object_sort_depths(Vec3(40.0, 0.0, 0.0), shot_c)
        self.assertGreater(positive_x_depth, negative_x_depth)
