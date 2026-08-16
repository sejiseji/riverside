from __future__ import annotations

from math import pi
from unittest import TestCase

from three_line_explorer.math3d import (
    Vec3,
    clamp,
    half_life_alpha,
    move_toward,
    shortest_angle_delta,
    smootherstep,
)


class Math3DTests(TestCase):
    def test_vec3_dot_cross_and_normalize(self) -> None:
        x = Vec3(1.0, 0.0, 0.0)
        y = Vec3(0.0, 1.0, 0.0)
        self.assertEqual(x.dot(y), 0.0)
        self.assertEqual(x.cross(y), Vec3(0.0, 0.0, 1.0))
        self.assertEqual(Vec3(0.0, 0.0, 0.0).normalized(), Vec3(0.0, 0.0, 0.0))
        self.assertAlmostEqual(Vec3(3.0, 0.0, 4.0).normalized().length(), 1.0)

    def test_clamp_move_and_smootherstep(self) -> None:
        self.assertEqual(clamp(12.0, 0.0, 10.0), 10.0)
        self.assertEqual(move_toward(0.0, 10.0, 3.0), 3.0)
        self.assertEqual(move_toward(9.0, 10.0, 3.0), 10.0)
        self.assertEqual(smootherstep(-1.0), 0.0)
        self.assertEqual(smootherstep(2.0), 1.0)
        self.assertAlmostEqual(smootherstep(0.5), 0.5)

    def test_shortest_angle_delta_is_deterministic_at_pi(self) -> None:
        self.assertAlmostEqual(shortest_angle_delta(0.0, pi), pi)
        self.assertAlmostEqual(shortest_angle_delta(pi, 0.0), pi)

    def test_half_life_alpha(self) -> None:
        self.assertAlmostEqual(half_life_alpha(0.5, 0.5), 0.5)
