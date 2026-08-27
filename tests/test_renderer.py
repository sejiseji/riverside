from __future__ import annotations

from unittest import TestCase

from three_line_explorer import palette
from three_line_explorer.camera import CAMERA_SHOTS, make_camera_snapshot
from three_line_explorer.config import FLOOR_OBJECT_ID, RIVER_OBJECT_ID, CameraShotId
from three_line_explorer.math3d import Vec3
from three_line_explorer.player import create_player
from three_line_explorer.renderer import Renderer, _face_sort_depth, _object_sort_depths
from three_line_explorer.stage import Stage
from three_line_explorer.visible_volume import update_visible_volume


class RendererTests(TestCase):
    def test_face_sort_depth_uses_nearest_point(self) -> None:
        points = (
            Vec3(0.0, 0.0, 40.0),
            Vec3(0.0, 0.0, 10.0),
            Vec3(0.0, 0.0, 20.0),
            Vec3(0.0, 0.0, 30.0),
        )

        self.assertEqual(_face_sort_depth(points), 10.0)

    def test_ground_faces_are_split_into_walkway_and_river(self) -> None:
        renderer = Renderer.create()
        player = create_player()
        snapshot = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], player.x, player.z)

        renderer.build_scene(
            Stage(solids=(), zones=()),
            update_visible_volume(player.x),
            player,
            snapshot,
            show_volume=False,
            show_lanes=False,
        )

        ground_faces = {
            face.object_id: face.fill_color
            for face in renderer.render_faces
            if face.object_id in {FLOOR_OBJECT_ID, RIVER_OBJECT_ID}
        }
        self.assertEqual(ground_faces[FLOOR_OBJECT_ID], palette.FLOOR_FILL)
        self.assertEqual(ground_faces[RIVER_OBJECT_ID], palette.RIVER_FILL)

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
