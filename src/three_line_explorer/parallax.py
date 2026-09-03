from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Any, Final

from three_line_explorer import palette
from three_line_explorer.camera import CameraSnapshot
from three_line_explorer.config import (
    GROUND_Y,
    VIEWPORT_H,
    VIEWPORT_W,
    VIEWPORT_X,
    VIEWPORT_Y,
)
from three_line_explorer.generated_environment_assets import (
    PARALLAX_SEQUENCES,
    PARALLAX_TILES,
    ParallaxLayer,
    validate_all_assets,
)
from three_line_explorer.math3d import AABB, Vec3, clamp
from three_line_explorer.pixel_map_source import compile_pixel_rows
from three_line_explorer.projection import project_camera_point, world_to_camera


@dataclass(frozen=True, slots=True)
class ParallaxLayerTuning:
    pixels_per_world: float
    world_width: float
    z_offset: float
    min_scale: float
    max_scale: float


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
    ParallaxLayer.FAR: ParallaxLayerTuning(
        pixels_per_world=0.04,
        world_width=72.0,
        z_offset=36.0,
        min_scale=0.40,
        max_scale=1.20,
    ),
    ParallaxLayer.MID: ParallaxLayerTuning(
        pixels_per_world=0.10,
        world_width=64.0,
        z_offset=22.0,
        min_scale=0.45,
        max_scale=1.35,
    ),
    ParallaxLayer.NEAR: ParallaxLayerTuning(
        pixels_per_world=0.18,
        world_width=56.0,
        z_offset=8.0,
        min_scale=0.50,
        max_scale=1.55,
    ),
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
    visible_bounds: AABB,
) -> None:
    pyxel.rect(VIEWPORT_X, VIEWPORT_Y, VIEWPORT_W, VIEWPORT_H, palette.BACKGROUND)

    for layer in (ParallaxLayer.FAR, ParallaxLayer.MID, ParallaxLayer.NEAR):
        tuning = atlas.layer_tuning[layer]
        edge_z = far_stage_edge_z(snapshot, visible_bounds) + (
            farther_z_direction(snapshot) * tuning.z_offset
        )
        scroll_world = player_x * tuning.pixels_per_world * snapshot.right.x
        _draw_projected_layer(
            pyxel,
            atlas,
            snapshot,
            layer,
            visible_bounds,
            edge_z,
            scroll_world,
        )


def far_stage_edge_z(snapshot: CameraSnapshot, visible_bounds: AABB) -> float:
    if snapshot.position.z >= snapshot.pivot.z:
        return visible_bounds.minimum.z
    return visible_bounds.maximum.z


def farther_z_direction(snapshot: CameraSnapshot) -> float:
    return -1.0 if snapshot.position.z >= snapshot.pivot.z else 1.0


def _draw_projected_layer(
    pyxel: Any,
    atlas: ParallaxAtlas,
    snapshot: CameraSnapshot,
    layer: ParallaxLayer,
    visible_bounds: AABB,
    edge_z: float,
    scroll_world: float,
) -> None:
    sequence = PARALLAX_SEQUENCES[layer]
    tuning = atlas.layer_tuning[layer]
    tile_world_w = tuning.world_width
    cycle_w = tile_world_w * len(sequence)
    normalized = scroll_world % cycle_w
    start_index = floor(normalized / tile_world_w)
    x = visible_bounds.minimum.x - tile_world_w - (normalized - start_index * tile_world_w)
    sequence_index = start_index

    while x > visible_bounds.minimum.x - tile_world_w:
        x -= tile_world_w
        sequence_index -= 1

    max_x = visible_bounds.maximum.x + tile_world_w
    while x < max_x:
        asset_id = sequence[sequence_index % len(sequence)]
        region = atlas.regions[asset_id]
        anchor_world = Vec3(x + tile_world_w * 0.5, GROUND_Y, edge_z)
        camera_point = world_to_camera(snapshot, anchor_world)
        projected = project_camera_point(snapshot, camera_point)
        if projected is not None:
            scale = _projected_tile_scale(
                snapshot,
                camera_point.z,
                tile_world_w,
                region.width,
                tuning,
            )
            if scale > 0.0:
                pyxel.blt(
                    round(projected.x - region.width * scale * 0.5),
                    round(projected.y - region.height * scale),
                    atlas.image,
                    region.u,
                    region.v,
                    region.width,
                    region.height,
                    region.colkey,
                    scale=scale,
                )
        x += tile_world_w
        sequence_index += 1


def _projected_tile_scale(
    snapshot: CameraSnapshot,
    camera_z: float,
    world_width: float,
    source_width: int,
    tuning: ParallaxLayerTuning,
) -> float:
    if camera_z <= 0.0 or source_width <= 0:
        return 0.0
    projected_width = snapshot.focal_px * world_width / camera_z
    return clamp(
        projected_width / source_width,
        tuning.min_scale,
        tuning.max_scale,
    )
