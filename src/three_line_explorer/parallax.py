from __future__ import annotations

from dataclasses import dataclass
from math import floor, isfinite
from typing import Any, Final

from three_line_explorer import palette
from three_line_explorer.blit_anchor import anchored_blt_origin
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
from three_line_explorer.math3d import AABB, Vec3
from three_line_explorer.pixel_map_source import compile_pixel_rows
from three_line_explorer.projection import project_world_point


@dataclass(frozen=True, slots=True)
class ParallaxBackdropLine:
    z_offset: float
    phase_ratio: float
    scroll_multiplier: float


@dataclass(frozen=True, slots=True)
class ParallaxLayerTuning:
    pixels_per_world: float
    world_width: float
    lines: tuple[ParallaxBackdropLine, ...]


@dataclass(frozen=True, slots=True)
class ParallaxTileRegion:
    u: int
    v: int
    width: int
    height: int
    colkey: int | None


@dataclass(frozen=True, slots=True)
class ParallaxSequenceRegion:
    u: int
    v: int
    width: int
    height: int
    colkey: int | None


@dataclass(frozen=True, slots=True)
class ParallaxAtlas:
    image: Any
    regions: dict[str, ParallaxTileRegion]
    sequence_regions: dict[ParallaxLayer, ParallaxSequenceRegion]
    layer_tuning: dict[ParallaxLayer, ParallaxLayerTuning]


PARALLAX_LAYER_TUNING: Final[dict[ParallaxLayer, ParallaxLayerTuning]] = {
    ParallaxLayer.FAR: ParallaxLayerTuning(
        pixels_per_world=0.035,
        world_width=72.0,
        lines=(
            ParallaxBackdropLine(z_offset=64.0, phase_ratio=0.0, scroll_multiplier=0.8),
            ParallaxBackdropLine(z_offset=44.0, phase_ratio=0.5, scroll_multiplier=1.0),
        ),
    ),
    ParallaxLayer.MID: ParallaxLayerTuning(
        pixels_per_world=0.085,
        world_width=64.0,
        lines=(
            ParallaxBackdropLine(z_offset=36.0, phase_ratio=0.25, scroll_multiplier=0.9),
            ParallaxBackdropLine(z_offset=24.0, phase_ratio=0.75, scroll_multiplier=1.1),
        ),
    ),
    ParallaxLayer.NEAR: ParallaxLayerTuning(
        pixels_per_world=0.14,
        world_width=56.0,
        lines=(
            ParallaxBackdropLine(z_offset=18.0, phase_ratio=0.0, scroll_multiplier=0.95),
            ParallaxBackdropLine(z_offset=8.0, phase_ratio=0.5, scroll_multiplier=1.15),
        ),
    ),
}

PARALLAX_VIEWPORT_MARGIN_X = 96
PARALLAX_WORLD_SPAN_MARGIN_X = 96.0
PARALLAX_STRIP_SCREEN_OVERLAP = 1
PARALLAX_STRIP_SCALE_LIMIT = 4.0
PARALLAX_STRIP_EDGE_TO_MID_SCALE_LIMIT = 2.0


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
    sequence_regions: dict[ParallaxLayer, ParallaxSequenceRegion] = {}
    layer_y = 0
    for layer in ParallaxLayer:
        sequence = PARALLAX_SEQUENCES[layer]
        x = 0
        layer_h = max(PARALLAX_TILES[asset_id].source.height for asset_id in sequence)
        layer_colkeys = {
            PARALLAX_TILES[asset_id].source.transparent_color
            for asset_id in sequence
        }
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
        if len(layer_colkeys) != 1:
            raise ValueError(f"parallax layer uses mixed transparent colors: {layer}")
        sequence_regions[layer] = ParallaxSequenceRegion(
            u=0,
            v=layer_y,
            width=x,
            height=layer_h,
            colkey=next(iter(layer_colkeys)),
        )
        layer_y += layer_h

    return ParallaxAtlas(
        image=image,
        regions=regions,
        sequence_regions=sequence_regions,
        layer_tuning=dict(PARALLAX_LAYER_TUNING),
    )


def draw_parallax_background(
    pyxel: Any,
    atlas: ParallaxAtlas,
    snapshot: CameraSnapshot,
    player_x: float,
    visible_bounds: AABB,
) -> None:
    del player_x
    pyxel.rect(VIEWPORT_X, VIEWPORT_Y, VIEWPORT_W, VIEWPORT_H, palette.BACKGROUND)

    for layer in (ParallaxLayer.FAR, ParallaxLayer.MID, ParallaxLayer.NEAR):
        tuning = atlas.layer_tuning[layer]
        edge_z = far_stage_edge_z(snapshot, visible_bounds)
        direction = farther_z_direction(snapshot)
        strip_world_w = tuning.world_width * len(PARALLAX_SEQUENCES[layer])
        for line in tuning.lines:
            line_z = edge_z + direction * line.z_offset
            scroll_world = (
                snapshot.position.x
                * tuning.pixels_per_world
                * line.scroll_multiplier
                + strip_world_w * line.phase_ratio
            )
            _draw_projected_layer(
                pyxel,
                atlas,
                snapshot,
                layer,
                visible_bounds,
                line_z,
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
    region = atlas.sequence_regions[layer]
    strip_world_w = tuning.world_width * len(sequence)
    min_x, max_x = _projected_world_x_span_for_viewport(snapshot, edge_z, visible_bounds)
    phase_x = scroll_world % strip_world_w
    x = phase_x + floor((min_x - phase_x) / strip_world_w) * strip_world_w - strip_world_w

    while x < max_x + strip_world_w:
        _draw_projected_strip(
            pyxel,
            atlas,
            snapshot,
            region,
            edge_z,
            x,
            x + strip_world_w,
        )
        x += strip_world_w


def _draw_projected_strip(
    pyxel: Any,
    atlas: ParallaxAtlas,
    snapshot: CameraSnapshot,
    region: ParallaxSequenceRegion,
    edge_z: float,
    left_x: float,
    right_x: float,
) -> None:
    left = project_world_point(snapshot, Vec3(left_x, GROUND_Y, edge_z))
    right = project_world_point(snapshot, Vec3(right_x, GROUND_Y, edge_z))
    middle_x = (left_x + right_x) * 0.5
    middle = project_world_point(snapshot, Vec3(middle_x, GROUND_Y, edge_z))
    if left is None or right is None or middle is None:
        return

    screen_left = min(left.x, right.x)
    screen_right = max(left.x, right.x)
    screen_width = screen_right - screen_left
    if screen_width <= 0.0 or region.width <= 0:
        return

    edge_draw_width = max(1, round(screen_width) + PARALLAX_STRIP_SCREEN_OVERLAP * 2)
    edge_scale = edge_draw_width / region.width
    midpoint_scale = _strip_midpoint_scale(
        snapshot,
        middle.depth,
        abs(right_x - left_x),
        region.width,
    )
    use_edge_alignment = _can_use_edge_projected_scale(edge_scale, midpoint_scale)
    if use_edge_alignment:
        scale = edge_scale
        bottom_y = max(left.y, right.y)
    else:
        scale = midpoint_scale
        bottom_y = middle.y

    if scale <= 0.0 or not isfinite(scale):
        return
    scale = min(scale, PARALLAX_STRIP_SCALE_LIMIT)
    if use_edge_alignment:
        anchor_screen_x = floor(screen_left) - PARALLAX_STRIP_SCREEN_OVERLAP
        source_anchor_x = 0.0
    else:
        anchor_screen_x = middle.x
        source_anchor_x = (region.width - 1) * 0.5
    draw_x, draw_y = anchored_blt_origin(
        screen_x=anchor_screen_x,
        screen_y=bottom_y,
        width=region.width,
        height=region.height,
        anchor_x=source_anchor_x,
        anchor_y=region.height - 1,
        scale=scale,
    )

    pyxel.blt(
        draw_x,
        draw_y,
        atlas.image,
        region.u,
        region.v,
        region.width,
        region.height,
        region.colkey,
        scale=scale,
    )


def _strip_midpoint_scale(
    snapshot: CameraSnapshot,
    camera_depth: float,
    world_width: float,
    source_width: int,
) -> float:
    if camera_depth <= 0.0 or source_width <= 0:
        return 0.0
    return snapshot.focal_px * world_width / camera_depth / source_width


def _can_use_edge_projected_scale(edge_scale: float, midpoint_scale: float) -> bool:
    if edge_scale <= 0.0 or midpoint_scale <= 0.0:
        return False
    if not isfinite(edge_scale) or not isfinite(midpoint_scale):
        return False
    if edge_scale > PARALLAX_STRIP_SCALE_LIMIT:
        return False
    return edge_scale <= midpoint_scale * PARALLAX_STRIP_EDGE_TO_MID_SCALE_LIMIT


def _projected_world_x_span_for_viewport(
    snapshot: CameraSnapshot,
    edge_z: float,
    visible_bounds: AABB,
) -> tuple[float, float]:
    xs = [
        _world_x_at_screen_x_on_ground_z(
            snapshot,
            VIEWPORT_X - PARALLAX_VIEWPORT_MARGIN_X,
            edge_z,
        ),
        _world_x_at_screen_x_on_ground_z(
            snapshot,
            VIEWPORT_X + VIEWPORT_W + PARALLAX_VIEWPORT_MARGIN_X,
            edge_z,
        ),
    ]
    finite_xs = [x for x in xs if x is not None]
    if len(finite_xs) < 2:
        return (
            visible_bounds.minimum.x - PARALLAX_WORLD_SPAN_MARGIN_X,
            visible_bounds.maximum.x + PARALLAX_WORLD_SPAN_MARGIN_X,
        )

    return (
        min(visible_bounds.minimum.x, *finite_xs) - PARALLAX_WORLD_SPAN_MARGIN_X,
        max(visible_bounds.maximum.x, *finite_xs) + PARALLAX_WORLD_SPAN_MARGIN_X,
    )


def _world_x_at_screen_x_on_ground_z(
    snapshot: CameraSnapshot,
    screen_x: float,
    edge_z: float,
) -> float | None:
    q = (screen_x - snapshot.screen_center_x) / snapshot.focal_px
    base = Vec3(0.0, GROUND_Y, edge_z) - snapshot.position
    camera_x_without_world_x = base.dot(snapshot.right)
    camera_z_without_world_x = base.dot(snapshot.forward)
    denominator = snapshot.right.x - q * snapshot.forward.x
    if abs(denominator) < 1e-6:
        return None

    world_x = (q * camera_z_without_world_x - camera_x_without_world_x) / denominator
    if not isfinite(world_x):
        return None
    projected = project_world_point(snapshot, Vec3(world_x, GROUND_Y, edge_z))
    if projected is None:
        return None
    return world_x
