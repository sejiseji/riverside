from __future__ import annotations

from math import pi
from typing import Any

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
PLAYER_SPRITE_RESOURCE_PATH = "assets/player_sprites.pyxres"
PLAYER_SPRITE_ANCHOR_X = PLAYER_SPRITE_FRAME_W * 0.5
PLAYER_SPRITE_ANCHOR_Y = 60.0
PLAYER_SPRITE_IDLE_FRAME = 0
PLAYER_SPRITE_WALK_SEQUENCE = (0, 1, 2, 3)

_loaded = False


def load_player_sprite_sheet(pyxel: Any) -> None:
    global _loaded
    if _loaded:
        return

    if _try_load_player_sprite_resource(pyxel):
        _loaded = True
        return

    for bank, sheet in zip(PLAYER_SPRITE_IMAGE_BANKS, PLAYER_SPRITE_SHEETS, strict=True):
        image = _image_bank(pyxel, bank)
        image.set(0, 0, list(sheet))
    _loaded = True


def player_sprite_source(player: PlayerState, frame_count: int) -> tuple[int, int, int, int, int]:
    del frame_count
    row = player_sprite_row(player.render_yaw)
    frame = player_sprite_frame(player)
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
        (0.0, SPRITE_ROW_RIGHT),
        (pi, SPRITE_ROW_LEFT),
        (-pi * 0.5, SPRITE_ROW_FRONT),
        (pi * 0.5, SPRITE_ROW_BACK),
    )
    return min(
        candidates,
        key=lambda item: abs(shortest_angle_delta(render_yaw, item[0])),
    )[1]


def player_sprite_frame(player: PlayerState) -> int:
    if not player_sprite_is_moving(player):
        return PLAYER_SPRITE_IDLE_FRAME
    return PLAYER_SPRITE_WALK_SEQUENCE[
        int(player.walk_phase) % len(PLAYER_SPRITE_WALK_SEQUENCE)
    ]


def player_sprite_is_moving(player: PlayerState) -> bool:
    return player.last_move_distance > 0.01


def _image_bank(pyxel: Any, bank: int) -> Any:
    image_getter = getattr(pyxel, "image", None)
    if callable(image_getter):
        return image_getter(bank)
    return pyxel.images[bank]


def _try_load_player_sprite_resource(pyxel: Any) -> bool:
    loader = getattr(pyxel, "load", None)
    if not callable(loader):
        return False
    try:
        loader(
            PLAYER_SPRITE_RESOURCE_PATH,
            exclude_tilemaps=True,
            exclude_sounds=True,
            exclude_musics=True,
        )
    except Exception:
        return False
    return True


__all__ = [
    "PLAYER_SPRITE_COLUMNS",
    "PLAYER_SPRITE_FRAME_H",
    "PLAYER_SPRITE_FRAME_W",
    "PLAYER_SPRITE_IMAGE_BANKS",
    "PLAYER_SPRITE_RESOURCE_PATH",
    "PLAYER_SPRITE_ANCHOR_X",
    "PLAYER_SPRITE_ANCHOR_Y",
    "PLAYER_SPRITE_TRANSPARENT_COLOR",
    "load_player_sprite_sheet",
    "player_sprite_frame",
    "player_sprite_is_moving",
    "player_sprite_row",
    "player_sprite_source",
]
