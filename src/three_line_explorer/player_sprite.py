from __future__ import annotations

from math import pi
from typing import Any

from three_line_explorer.config import LANE_SNAP_EPSILON, LANE_Z
from three_line_explorer.math3d import shortest_angle_delta
from three_line_explorer.player import PlayerState
from three_line_explorer.player_sprite_data import (
    PLAYER_SPRITE_ANIMATION_FRAMES,
    PLAYER_SPRITE_COLUMNS,
    PLAYER_SPRITE_FRAME_H,
    PLAYER_SPRITE_FRAME_W,
    PLAYER_SPRITE_FRAMES_PER_BANK,
    PLAYER_SPRITE_IMAGE_BANKS,
    PLAYER_SPRITE_SHEETS,
    PLAYER_SPRITE_TRANSPARENT_COLOR,
)


SPRITE_ROW_FRONT = 0
SPRITE_ROW_RIGHT = 1
SPRITE_ROW_LEFT = 2
SPRITE_ROW_BACK = 3

_loaded = False


def load_player_sprite_sheet(pyxel: Any) -> None:
    global _loaded
    if _loaded:
        return

    for bank, sheet in zip(PLAYER_SPRITE_IMAGE_BANKS, PLAYER_SPRITE_SHEETS, strict=True):
        image = _image_bank(pyxel, bank)
        image.set(0, 0, list(sheet))
    _loaded = True


def player_sprite_source(player: PlayerState, frame_count: int) -> tuple[int, int, int, int, int]:
    row = player_sprite_row(player.render_yaw)
    frame = 0
    if player_sprite_is_moving(player):
        frame = (frame_count // 5) % PLAYER_SPRITE_ANIMATION_FRAMES
    bank_index = frame // PLAYER_SPRITE_FRAMES_PER_BANK
    bank_frame = frame % PLAYER_SPRITE_FRAMES_PER_BANK
    return (
        PLAYER_SPRITE_IMAGE_BANKS[bank_index],
        bank_frame * PLAYER_SPRITE_FRAME_W,
        row * PLAYER_SPRITE_FRAME_H,
        PLAYER_SPRITE_FRAME_W,
        PLAYER_SPRITE_FRAME_H,
    )


def player_sprite_row(render_yaw: float) -> int:
    candidates = (
        (0.0, SPRITE_ROW_BACK),
        (pi, SPRITE_ROW_FRONT),
        (-pi * 0.5, SPRITE_ROW_RIGHT),
        (pi * 0.5, SPRITE_ROW_LEFT),
    )
    return min(
        candidates,
        key=lambda item: abs(shortest_angle_delta(render_yaw, item[0])),
    )[1]


def player_sprite_is_moving(player: PlayerState) -> bool:
    return (
        abs(player.velocity_x) > 0.5
        or player.pending_lane_step != 0
        or abs(LANE_Z[player.target_lane_index] - player.z) > LANE_SNAP_EPSILON
    )


def _image_bank(pyxel: Any, bank: int) -> Any:
    image_getter = getattr(pyxel, "image", None)
    if callable(image_getter):
        return image_getter(bank)
    return pyxel.images[bank]


__all__ = [
    "PLAYER_SPRITE_COLUMNS",
    "PLAYER_SPRITE_FRAME_H",
    "PLAYER_SPRITE_FRAME_W",
    "PLAYER_SPRITE_IMAGE_BANKS",
    "PLAYER_SPRITE_TRANSPARENT_COLOR",
    "load_player_sprite_sheet",
    "player_sprite_is_moving",
    "player_sprite_row",
    "player_sprite_source",
]
