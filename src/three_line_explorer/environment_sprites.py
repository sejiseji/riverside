from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from three_line_explorer.generated_environment_assets import (
    WORLD_SPRITES,
    WorldSpriteKind,
    validate_all_assets,
)
from three_line_explorer.math3d import AABB, Vec3
from three_line_explorer.pixel_map_source import compile_pixel_rows


ENVIRONMENT_SPRITE_TRANSPARENT_COLOR: Final = 8


@dataclass(frozen=True, slots=True)
class EnvironmentSpriteRegion:
    u: int
    v: int
    width: int
    height: int
    anchor_x: int
    anchor_y: int
    world_width: float
    colkey: int | None
    depth_bias: float


@dataclass(frozen=True, slots=True)
class EnvironmentSpriteAtlas:
    image: Any
    regions: dict[str, EnvironmentSpriteRegion]


@dataclass(frozen=True, slots=True)
class EnvironmentSpriteInstance:
    object_id: int
    sprite_id: str
    anchor: Vec3
    bounds: AABB
    collision_bounds: AABB | None = None


def make_environment_sprite_instance(
    *,
    object_id: int,
    sprite_id: str,
    x: float,
    z: float,
    y: float = 0.25,
) -> EnvironmentSpriteInstance:
    spec = WORLD_SPRITES[sprite_id]
    anchor = Vec3(x, y, z)
    visual_half_x = spec.world_width * 0.5
    visual_half_z = max(spec.collision_half_z, spec.world_width * 0.25, 3.0)
    visual_height = spec.source.height * spec.world_width / spec.source.width
    bounds = AABB(
        Vec3(x - visual_half_x, 0.0, z - visual_half_z),
        Vec3(x + visual_half_x, max(visual_height, 1.0), z + visual_half_z),
    )

    collision_bounds = None
    if spec.kind in {WorldSpriteKind.SOLID, WorldSpriteKind.SOLID_INSPECTABLE}:
        collision_bounds = AABB(
            Vec3(x - spec.collision_half_x, 0.0, z - spec.collision_half_z),
            Vec3(x + spec.collision_half_x, 48.0, z + spec.collision_half_z),
        )

    return EnvironmentSpriteInstance(
        object_id=object_id,
        sprite_id=sprite_id,
        anchor=anchor,
        bounds=bounds,
        collision_bounds=collision_bounds,
    )


def build_environment_sprite_atlas(pyxel: Any | None = None) -> EnvironmentSpriteAtlas:
    if pyxel is None:
        import pyxel as pyxel_module

        pyxel = pyxel_module

    validate_all_assets()
    sprite_ids = tuple(WORLD_SPRITES)
    atlas_w = sum(WORLD_SPRITES[sprite_id].source.width for sprite_id in sprite_ids)
    atlas_h = max(WORLD_SPRITES[sprite_id].source.height for sprite_id in sprite_ids)
    image = pyxel.Image(atlas_w, atlas_h)
    image.cls(ENVIRONMENT_SPRITE_TRANSPARENT_COLOR)

    regions: dict[str, EnvironmentSpriteRegion] = {}
    u = 0
    for sprite_id in sprite_ids:
        spec = WORLD_SPRITES[sprite_id]
        source = spec.source
        image.set(u, 0, compile_pixel_rows(source.rows, source.transparent_color))
        regions[sprite_id] = EnvironmentSpriteRegion(
            u=u,
            v=0,
            width=source.width,
            height=source.height,
            anchor_x=spec.anchor_x,
            anchor_y=spec.anchor_y,
            world_width=spec.world_width,
            colkey=source.transparent_color,
            depth_bias=spec.depth_bias,
        )
        u += source.width

    return EnvironmentSpriteAtlas(image=image, regions=regions)
