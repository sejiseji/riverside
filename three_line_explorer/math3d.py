from __future__ import annotations

from dataclasses import dataclass
from math import isclose, pi, sqrt, tau


@dataclass(frozen=True, slots=True)
class Vec2:
    x: float
    y: float

    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vec2:
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vec2:
        return self * scalar

    def __truediv__(self, scalar: float) -> Vec2:
        if scalar == 0:
            raise ZeroDivisionError("cannot divide Vec2 by zero")
        return Vec2(self.x / scalar, self.y / scalar)

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y

    def length(self) -> float:
        return sqrt(self.length_squared())

    def normalized(self) -> Vec2:
        length = self.length()
        if length == 0:
            return Vec2(0.0, 0.0)
        return self / length

    def dot(self, other: Vec2) -> float:
        return self.x * other.x + self.y * other.y


@dataclass(frozen=True, slots=True)
class Vec3:
    x: float
    y: float
    z: float

    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __neg__(self) -> Vec3:
        return Vec3(-self.x, -self.y, -self.z)

    def __mul__(self, scalar: float) -> Vec3:
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vec3:
        return self * scalar

    def __truediv__(self, scalar: float) -> Vec3:
        if scalar == 0:
            raise ZeroDivisionError("cannot divide Vec3 by zero")
        return Vec3(self.x / scalar, self.y / scalar, self.z / scalar)

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y + self.z * self.z

    def length(self) -> float:
        return sqrt(self.length_squared())

    def normalized(self) -> Vec3:
        length = self.length()
        if length == 0:
            return Vec3(0.0, 0.0, 0.0)
        return self / length

    def dot(self, other: Vec3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vec3) -> Vec3:
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )


@dataclass(frozen=True, slots=True)
class AABB:
    minimum: Vec3
    maximum: Vec3

    @property
    def center(self) -> Vec3:
        return (self.minimum + self.maximum) * 0.5

    @property
    def size(self) -> Vec3:
        return self.maximum - self.minimum

    def contains_point(self, point: Vec3) -> bool:
        return (
            self.minimum.x <= point.x <= self.maximum.x
            and self.minimum.y <= point.y <= self.maximum.y
            and self.minimum.z <= point.z <= self.maximum.z
        )

    def contains_aabb(self, other: AABB) -> bool:
        return (
            self.minimum.x <= other.minimum.x
            and self.minimum.y <= other.minimum.y
            and self.minimum.z <= other.minimum.z
            and other.maximum.x <= self.maximum.x
            and other.maximum.y <= self.maximum.y
            and other.maximum.z <= self.maximum.z
        )

    def intersects(self, other: AABB) -> bool:
        return not (
            self.maximum.x <= other.minimum.x
            or other.maximum.x <= self.minimum.x
            or self.maximum.y <= other.minimum.y
            or other.maximum.y <= self.minimum.y
            or self.maximum.z <= other.minimum.z
            or other.maximum.z <= self.minimum.z
        )


WORLD_UP = Vec3(0.0, 1.0, 0.0)


def clamp(value: float, minimum: float, maximum: float) -> float:
    if minimum > maximum:
        raise ValueError("minimum must be less than or equal to maximum")
    return max(minimum, min(maximum, value))


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    return int(clamp(float(value), float(minimum), float(maximum)))


def lerp(start: float, end: float, t: float) -> float:
    return start + (end - start) * t


def move_toward(current: float, target: float, max_delta: float) -> float:
    if max_delta < 0:
        raise ValueError("max_delta must not be negative")
    delta = target - current
    if abs(delta) <= max_delta:
        return target
    return current + max_delta * (1.0 if delta > 0 else -1.0)


def smootherstep(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def half_life_alpha(dt: float, half_life: float) -> float:
    if half_life <= 0.0:
        return 1.0
    return 1.0 - 2.0 ** (-dt / half_life)


def shortest_angle_delta(start: float, target: float) -> float:
    delta = (target - start + pi) % tau - pi
    if isclose(delta, -pi, abs_tol=1e-12):
        return pi
    return delta


def lerp_angle(start: float, target: float, t: float) -> float:
    return start + shortest_angle_delta(start, target) * t


def normalize_angle(angle: float) -> float:
    return angle % tau


def rotate_y(vector: Vec3, yaw: float) -> Vec3:
    from math import cos, sin

    c = cos(yaw)
    s = sin(yaw)
    return Vec3(
        vector.x * c + vector.z * s,
        vector.y,
        -vector.x * s + vector.z * c,
    )
