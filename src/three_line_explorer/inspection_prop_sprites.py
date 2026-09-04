"""Compatibility wrapper for source-defined drift-item sprites.

RIV013 promotes inspection props from a three-sprite prototype atlas to the
100-slot drift-item atlas.  Gameplay code should treat sprite identifiers as
strings, while this module keeps the old names used by tests and early stage
fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from three_line_explorer.drift_item_catalog import DRIFT_ITEM_BY_ID, DRIFT_ITEM_IDS
from three_line_explorer.drift_item_sprites import (
    ATLAS_PAGE_COUNT,
    ATLAS_PAGE_H,
    ATLAS_PAGE_W,
    CELL_H,
    CELL_W,
    SPRITE_ROWS,
    TRANSPARENT_COLOR,
    TRANSPARENT_DIGIT,
    DriftSpriteAtlas as PropSpriteAtlas,
    DriftSpriteRegion as SpriteRegion,
    build_drift_sprite_atlas,
    instantiate_pixel_map_sources,
    validate_all_sprites as validate_all_drift_sprites,
    validate_sprite_rows as validate_drift_sprite_rows,
)


class PropSpriteId(StrEnum):
    SINGLE_SANDAL = "single_sandal"
    CLOUDED_BOTTLE = "clouded_bottle"
    DRIFTWOOD = "sprouted_driftwood"


@dataclass(frozen=True, slots=True)
class PropSpriteDefinition:
    rows: tuple[str, ...]
    world_width: float


SPRITE_ORDER: Final[tuple[str, ...]] = DRIFT_ITEM_IDS
SPRITE_DEFINITIONS: Final[dict[str, PropSpriteDefinition]] = {
    sprite_id: PropSpriteDefinition(
        rows=SPRITE_ROWS[sprite_id],
        world_width=DRIFT_ITEM_BY_ID[sprite_id].world_width,
    )
    for sprite_id in DRIFT_ITEM_IDS
}
ATLAS_W: Final = ATLAS_PAGE_W
ATLAS_H: Final = ATLAS_PAGE_H


def validate_sprite_rows(sprite_id: str, rows: tuple[str, ...]) -> None:
    validate_drift_sprite_rows(sprite_id, rows)


def validate_all_sprites() -> None:
    validate_all_drift_sprites()


def compile_sprite_rows(rows: tuple[str, ...]) -> list[str]:
    return [row.replace(".", TRANSPARENT_DIGIT) for row in rows]


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


def build_prop_sprite_atlas(pyxel: object | None = None) -> PropSpriteAtlas:
    return build_drift_sprite_atlas(pyxel)


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


__all__ = [
    "ATLAS_H",
    "ATLAS_PAGE_COUNT",
    "ATLAS_W",
    "CELL_H",
    "CELL_W",
    "PropSpriteAtlas",
    "PropSpriteDefinition",
    "PropSpriteId",
    "SPRITE_DEFINITIONS",
    "SPRITE_ORDER",
    "SpriteRegion",
    "TRANSPARENT_COLOR",
    "TRANSPARENT_DIGIT",
    "build_prop_sprite_atlas",
    "calculate_sprite_scale",
    "compile_sprite_rows",
    "instantiate_pixel_map_sources",
    "validate_all_sprites",
    "validate_sprite_rows",
    "visible_bounds",
]
