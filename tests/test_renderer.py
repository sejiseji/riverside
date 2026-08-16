from __future__ import annotations

from unittest import TestCase

from three_line_explorer.math3d import Vec3
from three_line_explorer.renderer import _face_sort_depth


class RendererTests(TestCase):
    def test_face_sort_depth_uses_nearest_point(self) -> None:
        points = (
            Vec3(0.0, 0.0, 40.0),
            Vec3(0.0, 0.0, 10.0),
            Vec3(0.0, 0.0, 20.0),
            Vec3(0.0, 0.0, 30.0),
        )

        self.assertEqual(_face_sort_depth(points), 10.0)
