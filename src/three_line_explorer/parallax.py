from __future__ import annotations

from dataclasses import dataclass
from math import floor, tan
from typing import Any, Final

from three_line_explorer import palette
from three_line_explorer.camera import CameraSnapshot
from three_line_explorer.config import VIEWPORT_H, VIEWPORT_W, VIEWPORT_X, VIEWPORT_Y
from three_line_explorer.generated_environment_assets import (
    PARALLAX_SEQUENCES,
    PARALLAX_TILES,
    ParallaxLayer,
    validate_all_assets,
)
from three_line_explorer.pixel_map_source import compile_pixel_rows


@dataclass(frozen=True, slots=True)
class ParallaxLayerTuning:
    pixels_per_world: float
    horizon_offset_y: int


@dataclass(frozen=True, slots=True)
class ParallaxTileRegion:
    u: int
    v: int
    width: int
    height: int
    colkey: int | None


@dataclass(frozen=True, slots=True)
class ParallaxAtlas:
    image: Any
    regions: dict[str, ParallaxTileRegion]
    layer_tuning: dict[ParallaxLayer, ParallaxLayerTuning]


PARALLAX_LAYER_TUNING: Final[dict[ParallaxLayer, ParallaxLayerTuning]] = {
    ParallaxLayer.FAR: ParallaxLayerTuning(pixels_per_world=0.04, horizon_offset_y=4),
    ParallaxLayer.MID: ParallaxLayerTuning(pixels_per_world=0.10, horizon_offset_y=18),
    ParallaxLayer.NEAR: ParallaxLayerTuning(pixels_per_world=0.18, horizon_offset_y=38),
}


def build_parallax_atlas(pyxel: Any | None = None) -> ParallaxAtlas:
    if pyxel is None:
        import pyxel as pyxel_module

        pyxel = pyxel_module

    validate_all_assets()
    atlas_w = max(
        sum(PARALLAX_TILES[asset_id].source.width for asset_id in sequence)
        for sequence in PARALLAX_SEQUENCES.values()
    )
    atlas_h = sum(
        max(PARALLAX_TILES[asset_id].source.height for asset_id in sequence)
        for sequence in PARALLAX_SEQUENCES.values()
    )
    image = pyxel.Image(atlas_w, atlas_h)
    image.cls(8)

    regions: dict[str, ParallaxTileRegion] = {}
    layer_y = 0
    for layer in ParallaxLayer:
        sequence = PARALLAX_SEQUENCES[layer]
        x = 0
        layer_h = max(PARALLAX_TILES[asset_id].source.height for asset_id in sequence)
        for asset_id in sequence:
            source = PARALLAX_TILES[asset_id].source
            image.set(x, layer_y, compile_pixel_rows(source.rows, source.transparent_color))
            regions[asset_id] = ParallaxTileRegion(
                u=x,
                v=layer_y,
                width=source.width,
                height=source.height,
                colkey=source.transparent_color,
            )
            x += source.width
        layer_y += layer_h

    return ParallaxAtlas(
        image=image,
        regions=regions,
        layer_tuning=dict(PARALLAX_LAYER_TUNING),
    )


def draw_parallax_background(
    pyxel: Any,
    atlas: ParallaxAtlas,
    snapshot: CameraSnapshot,
    player_x: float,
) -> None:
    pyxel.rect(VIEWPORT_X, VIEWPORT_Y, VIEWPORT_W, VIEWPORT_H, palette.BACKGROUND)
    horizon_y = horizon_screen_y(snapshot)
    screen_x_orientation = snapshot.right.x

    for layer in (ParallaxLayer.FAR, ParallaxLayer.MID, ParallaxLayer.NEAR):
        tuning = atlas.layer_tuning[layer]
        bottom_y = round(horizon_y) + tuning.horizon_offset_y
        scroll_px = round(-player_x * tuning.pixels_per_world * screen_x_orientation)
        _draw_layer(pyxel, atlas, layer, bottom_y, scroll_px)


def horizon_screen_y(snapshot: CameraSnapshot) -> float:
    return snapshot.screen_center_y - snapshot.focal_px * tan(snapshot.params.elevation)


def _draw_layer(
    pyxel: Any,
    atlas: ParallaxAtlas,
    layer: ParallaxLayer,
    bottom_y: int,
    scroll_px: int,
) -> None:
    sequence = PARALLAX_SEQUENCES[layer]
    first_region = atlas.regions[sequence[0]]
    tile_w = first_region.width
    cycle_w = tile_w * len(sequence)
    normalized = scroll_px % cycle_w
    start_index = floor(normalized / tile_w)
    x = VIEWPORT_X - (normalized - start_index * tile_w)
    sequence_index = start_index

    while x > VIEWPORT_X - tile_w:
        x -= tile_w
        sequence_index -= 1

    viewport_right = VIEWPORT_X + VIEWPORT_W
    while x < viewport_right:
        asset_id = sequence[sequence_index % len(sequence)]
        region = atlas.regions[asset_id]
        pyxel.blt(
            round(x),
            bottom_y - region.height,
            atlas.image,
            region.u,
            region.v,
            region.width,
            region.height,
            region.colkey,
        )
        x += region.width
        sequence_index += 1
