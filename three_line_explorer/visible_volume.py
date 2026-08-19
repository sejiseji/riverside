from __future__ import annotations

from dataclasses import dataclass

from three_line_explorer.config import (
    GROUND_Y,
    STAGE_MAX_X,
    STAGE_MAX_Y,
    STAGE_MAX_Z,
    STAGE_MIN_X,
    STAGE_MIN_Z,
    VISIBLE_SIZE_X,
)
from three_line_explorer.math3d import AABB, Vec3, clamp


@dataclass(slots=True)
class VisibleVolumeState:
    center_x: float
    bounds: AABB
    clamped_left: bool
    clamped_right: bool


def validate_visible_volume() -> None:
    if STAGE_MAX_X - STAGE_MIN_X < VISIBLE_SIZE_X:
        raise ValueError("stage_length_x must be greater than or equal to VISIBLE_SIZE_X")


def update_visible_volume(player_x: float) -> VisibleVolumeState:
    validate_visible_volume()
    half_x = VISIBLE_SIZE_X * 0.5
    center_x = clamp(player_x, STAGE_MIN_X + half_x, STAGE_MAX_X - half_x)
    bounds = AABB(
        Vec3(center_x - half_x, GROUND_Y, STAGE_MIN_Z),
        Vec3(center_x + half_x, STAGE_MAX_Y, STAGE_MAX_Z),
    )
    return VisibleVolumeState(
        center_x=center_x,
        bounds=bounds,
        clamped_left=center_x <= STAGE_MIN_X + half_x,
        clamped_right=center_x >= STAGE_MAX_X - half_x,
    )
