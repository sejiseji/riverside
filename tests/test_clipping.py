from __future__ import annotations

from unittest import TestCase

from three_line_explorer.clipping import (
    clip_camera_polygon_near,
    clip_segment_aabb,
    intersect_aabb,
)
from three_line_explorer.math3d import AABB, Vec3


class ClippingTests(TestCase):
    def test_aabb_intersection_none_inside_and_partial(self) -> None:
        volume = AABB(Vec3(0.0, 0.0, 0.0), Vec3(10.0, 10.0, 10.0))
        outside = AABB(Vec3(11.0, 0.0, 0.0), Vec3(12.0, 1.0, 1.0))
        inside = AABB(Vec3(1.0, 1.0, 1.0), Vec3(2.0, 2.0, 2.0))
        partial = AABB(Vec3(-1.0, 1.0, 1.0), Vec3(4.0, 3.0, 3.0))

        self.assertIsNone(intersect_aabb(outside, volume))
        self.assertEqual(intersect_aabb(inside, volume), inside)
        clipped = intersect_aabb(partial, volume)
        self.assertEqual(clipped, AABB(Vec3(0.0, 1.0, 1.0), Vec3(4.0, 3.0, 3.0)))

    def test_segment_clips_to_aabb(self) -> None:
        volume = AABB(Vec3(0.0, 0.0, 0.0), Vec3(10.0, 10.0, 10.0))
        clipped = clip_segment_aabb(Vec3(-5.0, 5.0, 5.0), Vec3(5.0, 5.0, 5.0), volume)
        self.assertEqual(clipped, (Vec3(0.0, 5.0, 5.0), Vec3(5.0, 5.0, 5.0)))

    def test_near_polygon_clip_keeps_closed_polygon(self) -> None:
        polygon = (
            Vec3(-1.0, -1.0, 2.0),
            Vec3(1.0, -1.0, 2.0),
            Vec3(1.0, 1.0, 8.0),
            Vec3(-1.0, 1.0, 8.0),
        )
        clipped = clip_camera_polygon_near(polygon, 4.0)
        self.assertGreaterEqual(len(clipped), 3)
        self.assertTrue(all(point.z >= 4.0 for point in clipped))
