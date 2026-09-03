"""Source-defined Pyxel sprites for riverside inspection props.

The sprite art is stored as hexadecimal Pyxel color indexes. A dot (".") is
an authoring-only shorthand for the transparent color.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final

from three_line_explorer.pixel_map_source import (
    compile_pixel_rows,
    palette_digit,
    valid_source_chars,
    validate_pixel_map,
)


CELL_W: Final = 32
CELL_H: Final = 24
TRANSPARENT_COLOR: Final = 8
TRANSPARENT_DIGIT: Final = palette_digit(TRANSPARENT_COLOR)
_VALID_SOURCE_CHARS: Final = valid_source_chars(TRANSPARENT_COLOR)


class PropSpriteId(StrEnum):
    SINGLE_SANDAL = "single_sandal"
    CLOUDED_BOTTLE = "clouded_bottle"
    DRIFTWOOD = "driftwood"


@dataclass(frozen=True, slots=True)
class PropSpriteDefinition:
    rows: tuple[str, ...]
    world_width: float


@dataclass(frozen=True, slots=True)
class SpriteRegion:
    u: int
    v: int
    width: int
    height: int
    anchor_x: int
    anchor_y: int
    world_width: float


@dataclass(frozen=True, slots=True)
class PropSpriteAtlas:
    image: Any
    regions: dict[PropSpriteId, SpriteRegion]


SINGLE_SANDAL: Final = (
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
    "................55555511........",
    "..............5556666555111.....",
    "...........11555666666555d111...",
    "........111dd5556666655577dd11..",
    "......11ddd777555555555777dd11..",
    "....11ddd777777555555777666611..",
    "...11ddd777777777777777666d11...",
    "...11d0d7777777777777ddddd11....",
    "....11d0dd777777777ddddd11......",
    ".....111d6666ddddddddd11........",
    ".......111dddddddddd11..........",
    ".........111dddd011.............",
    "...........111111...............",
    "................................",
    "................................",
    "................................",
    "................................",
)


CLOUDED_BOTTLE: Final = (
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
    "......11111.....................",
    "..444ddddcc1111.................",
    ".4999777c7777cc1111111111.......",
    ".499911cc777777777777c667111....",
    "..444666cc7777c77ddd77cc67611...",
    "......11ccc777c7777777ccc66611..",
    ".......11ccc33bbbbb33333c66611..",
    "........11ccc333bbbbb33666c11...",
    "..........11ccc3333333ccc111....",
    ".............111111111111.......",
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
)


DRIFTWOOD: Final = (
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
    ".................000............",
    "................044000..........",
    "................04999400........",
    "...............00449994000......",
    "..................44444440000...",
    "...........000000a44a990999400..",
    "......000004a49a99099a9994440...",
    "...aaa44a9a9909999a909944440....",
    "..099409999099a90999444440......",
    "...004449099a99999444440000.....",
    ".....00444999990444400444400....",
    "........0044444440.....099400...",
    "...........00000.........04400..",
    "...........................000..",
    "................................",
    "................................",
    "................................",
    "................................",
    "................................",
)


SPRITE_DEFINITIONS: Final[dict[PropSpriteId, PropSpriteDefinition]] = {
    PropSpriteId.SINGLE_SANDAL: PropSpriteDefinition(
        rows=SINGLE_SANDAL,
        world_width=18.0,
    ),
    PropSpriteId.CLOUDED_BOTTLE: PropSpriteDefinition(
        rows=CLOUDED_BOTTLE,
        world_width=20.0,
    ),
    PropSpriteId.DRIFTWOOD: PropSpriteDefinition(
        rows=DRIFTWOOD,
        world_width=24.0,
    ),
}

SPRITE_ORDER: Final = (
    PropSpriteId.SINGLE_SANDAL,
    PropSpriteId.CLOUDED_BOTTLE,
    PropSpriteId.DRIFTWOOD,
)

ATLAS_W: Final = CELL_W * len(SPRITE_ORDER)
ATLAS_H: Final = CELL_H


def validate_sprite_rows(sprite_id: PropSpriteId, rows: tuple[str, ...]) -> None:
    validate_pixel_map(
        asset_id=str(sprite_id),
        rows=rows,
        width=CELL_W,
        height=CELL_H,
        transparent_color=TRANSPARENT_COLOR,
    )


def validate_all_sprites() -> None:
    for sprite_id, definition in SPRITE_DEFINITIONS.items():
        validate_sprite_rows(sprite_id, definition.rows)


def compile_sprite_rows(rows: tuple[str, ...]) -> list[str]:
    return compile_pixel_rows(rows, TRANSPARENT_COLOR)


def visible_bounds(rows: tuple[str, ...]) -> tuple[int, int, int, int]:
    points = [
        (x, y)
        for y, row in enumerate(rows)
        for x, char in enumerate(row)
        if char != "."
    ]
    if not points:
        raise ValueError("sprite is fully transparent")

    xs = [x for x, _ in points]
    ys = [y for _, y in points]
    return min(xs), min(ys), max(xs), max(ys)


def build_prop_sprite_atlas(pyxel: Any | None = None) -> PropSpriteAtlas:
    if pyxel is None:
        import pyxel as pyxel_module

        pyxel = pyxel_module

    validate_all_sprites()

    image = pyxel.Image(ATLAS_W, ATLAS_H)
    image.cls(TRANSPARENT_COLOR)
    regions: dict[PropSpriteId, SpriteRegion] = {}

    for index, sprite_id in enumerate(SPRITE_ORDER):
        definition = SPRITE_DEFINITIONS[sprite_id]
        u = index * CELL_W
        image.set(u, 0, compile_sprite_rows(definition.rows))
        min_x, _min_y, max_x, max_y = visible_bounds(definition.rows)
        regions[sprite_id] = SpriteRegion(
            u=u,
            v=0,
            width=CELL_W,
            height=CELL_H,
            anchor_x=(min_x + max_x) // 2,
            anchor_y=max_y,
            world_width=definition.world_width,
        )

    return PropSpriteAtlas(image, regions)


def calculate_sprite_scale(
    focal_px: float,
    camera_z: float,
    world_width: float,
    source_width: int,
    *,
    minimum: float = 0.5,
    maximum: float = 1.5,
) -> float:
    if camera_z <= 0.0 or source_width <= 0:
        return 0.0
    projected_width = focal_px * world_width / camera_z
    return max(minimum, min(maximum, projected_width / source_width))
