from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Protocol

from three_line_explorer.config import NEAR_PLANE
from three_line_explorer.math3d import Vec3


class CameraSnapshotLike(Protocol):
    position: Vec3
    right: Vec3
    up: Vec3
    forward: Vec3
    focal_px: float
    screen_center_x: float
    screen_center_y: float


@dataclass(frozen=True, slots=True)
class ProjectedPoint:
    x: float
    y: float
    depth: float


def world_to_camera(snapshot: CameraSnapshotLike, point: Vec3) -> Vec3:
    relative = point - snapshot.position
    return Vec3(
        relative.dot(snapshot.right),
        relative.dot(snapshot.up),
        relative.dot(snapshot.forward),
    )


def project_camera_point(
    snapshot: CameraSnapshotLike,
    camera_point: Vec3,
    *,
    near_plane: float = NEAR_PLANE,
) -> ProjectedPoint | None:
    if camera_point.z <= near_plane:
        return None

    screen_x = snapshot.screen_center_x + snapshot.focal_px * camera_point.x / camera_point.z
    screen_y = snapshot.screen_center_y - snapshot.focal_px * camera_point.y / camera_point.z
    if not all(isfinite(value) for value in (screen_x, screen_y, camera_point.z)):
        return None
    return ProjectedPoint(screen_x, screen_y, camera_point.z)


def project_world_point(
    snapshot: CameraSnapshotLike,
    point: Vec3,
    *,
    near_plane: float = NEAR_PLANE,
) -> ProjectedPoint | None:
    return project_camera_point(snapshot, world_to_camera(snapshot, point), near_plane=near_plane)
