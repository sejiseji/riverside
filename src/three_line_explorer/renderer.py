from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor
from typing import Any

from three_line_explorer import palette
from three_line_explorer.camera import CameraSnapshot
from three_line_explorer.clipping import (
    clip_camera_polygon_near,
    clip_camera_segment_near,
    clip_segment_aabb,
    intersect_aabb,
)
from three_line_explorer.config import (
    CULL_EPSILON,
    FLOOR_OBJECT_ID,
    GROUND_Y,
    LANE_Z,
    NEAR_PLANE,
    PLAYER_OBJECT_ID,
    RenderLayer,
    RIVER_OBJECT_ID,
    RIVER_START_Z,
    VISIBLE_VOLUME_OBJECT_ID,
    VIEWPORT_H,
    VIEWPORT_W,
    VIEWPORT_X,
    VIEWPORT_Y,
)
from three_line_explorer.environment_sprites import (
    EnvironmentSpriteAtlas,
    build_environment_sprite_atlas,
)
from three_line_explorer.geometry import Face, make_aabb_faces, make_floor_face
from three_line_explorer.inspection import prop_sprite_anchor
from three_line_explorer.inspection_prop_sprites import (
    PropSpriteAtlas,
    TRANSPARENT_COLOR as PROP_SPRITE_TRANSPARENT_COLOR,
    build_prop_sprite_atlas,
    calculate_sprite_scale,
)
from three_line_explorer.math3d import AABB, Vec3
from three_line_explorer.parallax import (
    ParallaxAtlas,
    build_parallax_atlas,
    draw_parallax_background,
)
from three_line_explorer.player import PlayerState
from three_line_explorer.player_sprite import (
    PLAYER_SPRITE_FRAME_H,
    PLAYER_SPRITE_FRAME_W,
    PLAYER_SPRITE_TRANSPARENT_COLOR,
    load_player_sprite_sheet,
    player_sprite_source,
)
from three_line_explorer.projection import ProjectedPoint, project_camera_point, world_to_camera
from three_line_explorer.stage import Stage
from three_line_explorer.visible_volume import VisibleVolumeState


@dataclass(slots=True)
class RenderFace:
    layer: RenderLayer
    lane_depth: float
    route_depth: float
    depth: float
    object_id: int
    face_index: int
    points: tuple[ProjectedPoint, ...]
    fill_color: int
    outline_color: int


@dataclass(slots=True)
class RenderLine:
    layer: RenderLayer
    depth: float
    object_id: int
    line_index: int
    start: ProjectedPoint
    end: ProjectedPoint
    color: int


@dataclass(slots=True)
class RenderSprite:
    layer: RenderLayer
    lane_depth: float
    route_depth: float
    depth: float
    object_id: int
    anchor: ProjectedPoint
    image_source: Any
    u: int
    v: int
    w: int
    h: int
    anchor_offset_x: float
    anchor_offset_y: float
    scale: float
    colkey: int | None


@dataclass(slots=True)
class RenderStats:
    candidate_objects: int = 0
    visible_faces: int = 0
    draw_triangles: int = 0
    draw_lines: int = 0
    clipped_boxes: int = 0


@dataclass(slots=True)
class Renderer:
    render_faces: list[RenderFace]
    render_lines: list[RenderLine]
    render_sprites: list[RenderSprite]
    prop_sprite_atlas: PropSpriteAtlas | None = None
    environment_sprite_atlas: EnvironmentSpriteAtlas | None = None
    parallax_atlas: ParallaxAtlas | None = None

    @classmethod
    def create(cls) -> Renderer:
        return cls(render_faces=[], render_lines=[], render_sprites=[])

    def render(
        self,
        pyxel: Any,
        stage: Stage,
        visible_volume: VisibleVolumeState,
        player: PlayerState,
        snapshot: CameraSnapshot,
        *,
        show_volume: bool,
        show_lanes: bool,
    ) -> RenderStats:
        load_player_sprite_sheet(pyxel)
        if self.prop_sprite_atlas is None:
            self.prop_sprite_atlas = build_prop_sprite_atlas(pyxel)
        if self.environment_sprite_atlas is None:
            self.environment_sprite_atlas = build_environment_sprite_atlas(pyxel)
        if self.parallax_atlas is None:
            self.parallax_atlas = build_parallax_atlas(pyxel)
        stats = self.build_scene(
            stage,
            visible_volume,
            player,
            snapshot,
            frame_count=getattr(pyxel, "frame_count", 0),
            show_volume=show_volume,
            show_lanes=show_lanes,
        )

        pyxel.clip(VIEWPORT_X, VIEWPORT_Y, VIEWPORT_W, VIEWPORT_H)
        draw_parallax_background(pyxel, self.parallax_atlas, snapshot, player.x)
        render_items = [
            (_render_face_sort_key(face), 0, face)
            for face in self.render_faces
        ] + [
            (_render_sprite_sort_key(sprite), 1, sprite)
            for sprite in self.render_sprites
        ]
        for _sort_key, item_type, item in sorted(
            render_items,
            key=lambda value: (value[0], value[1]),
        ):
            if item_type == 0:
                _draw_face(pyxel, item)
            else:
                _draw_sprite(pyxel, item)
        for line in sorted(
            self.render_lines,
            key=lambda item: (item.layer, -item.depth, item.object_id, item.line_index),
        ):
            _draw_line(pyxel, line)
        pyxel.clip()
        return stats

    def build_scene(
        self,
        stage: Stage,
        visible_volume: VisibleVolumeState,
        player: PlayerState,
        snapshot: CameraSnapshot,
        *,
        frame_count: int = 0,
        show_volume: bool,
        show_lanes: bool,
    ) -> RenderStats:
        self.render_faces.clear()
        self.render_lines.clear()
        self.render_sprites.clear()
        stats = RenderStats()

        self._enqueue_ground_faces(visible_volume.bounds, snapshot, stats)

        candidates = stage.candidate_solids(visible_volume.bounds)
        inspectable_props = stage.candidate_inspectable_props(visible_volume.bounds)
        environment_sprites = stage.candidate_environment_sprites(visible_volume.bounds)
        stats.candidate_objects = (
            len(candidates)
            + len(inspectable_props)
            + len(environment_sprites)
        )
        for solid in candidates:
            clipped_bounds = intersect_aabb(solid.bounds, visible_volume.bounds)
            if clipped_bounds is None:
                continue
            if visible_volume.bounds.contains_aabb(solid.bounds):
                faces = solid.faces
                object_sort_center = solid.bounds.center
            else:
                stats.clipped_boxes += 1
                faces = make_aabb_faces(
                    clipped_bounds,
                    solid.object_id,
                    solid.side_color,
                    solid.top_color,
                    solid.outline_color,
                )
                object_sort_center = clipped_bounds.center
            for face in faces:
                self._enqueue_face(
                    face,
                    RenderLayer.SOLID,
                    snapshot,
                    stats,
                    object_sort_center=object_sort_center,
                )

        for sprite in environment_sprites:
            self._enqueue_environment_sprite(sprite, visible_volume.bounds, snapshot)

        for prop in inspectable_props:
            self._enqueue_inspectable_prop_sprite(prop, visible_volume.bounds, snapshot)

        self._enqueue_player_sprite(player, snapshot, frame_count)

        if show_lanes:
            self._enqueue_lane_lines(visible_volume.bounds, snapshot, stats)
        if show_volume:
            self._enqueue_visible_volume_edges(visible_volume.bounds, snapshot, stats)

        stats.visible_faces = len(self.render_faces)
        return stats

    def _enqueue_player_sprite(
        self,
        player: PlayerState,
        snapshot: CameraSnapshot,
        frame_count: int,
    ) -> None:
        anchor_world = Vec3(player.x, GROUND_Y, player.z)
        camera_point = world_to_camera(snapshot, anchor_world)
        projected = project_camera_point(snapshot, camera_point)
        if projected is None:
            return

        lane_depth, route_depth = _object_sort_depths(anchor_world, snapshot)
        image_bank, u, v, w, h = player_sprite_source(player, frame_count)
        self.render_sprites.append(
            RenderSprite(
                layer=RenderLayer.SOLID,
                lane_depth=lane_depth,
                route_depth=route_depth,
                depth=camera_point.z,
                object_id=PLAYER_OBJECT_ID,
                anchor=projected,
                image_source=image_bank,
                u=u,
                v=v,
                w=w,
                h=h,
                anchor_offset_x=PLAYER_SPRITE_FRAME_W * 0.5,
                anchor_offset_y=PLAYER_SPRITE_FRAME_H,
                scale=1.0,
                colkey=PLAYER_SPRITE_TRANSPARENT_COLOR,
            )
        )

    def _enqueue_inspectable_prop_sprite(
        self,
        prop: Any,
        visible_bounds: AABB,
        snapshot: CameraSnapshot,
    ) -> None:
        atlas = self.prop_sprite_atlas
        if (
            atlas is None
            or prop.sprite_id is None
            or not visible_bounds.intersects(prop.bounds)
        ):
            return

        anchor_world = prop_sprite_anchor(prop)
        camera_point = world_to_camera(snapshot, anchor_world)
        projected = project_camera_point(snapshot, camera_point)
        if projected is None:
            return

        region = atlas.regions[prop.sprite_id]
        scale = calculate_sprite_scale(
            snapshot.focal_px,
            camera_point.z,
            region.world_width,
            region.width,
        )
        if scale <= 0.0:
            return

        lane_depth, route_depth = _object_sort_depths(anchor_world, snapshot)
        self.render_sprites.append(
            RenderSprite(
                layer=RenderLayer.SOLID,
                lane_depth=lane_depth,
                route_depth=route_depth,
                depth=camera_point.z,
                object_id=prop.render_object_id,
                anchor=projected,
                image_source=atlas.image,
                u=region.u,
                v=region.v,
                w=region.width,
                h=region.height,
                anchor_offset_x=region.anchor_x,
                anchor_offset_y=region.anchor_y,
                scale=scale,
                colkey=PROP_SPRITE_TRANSPARENT_COLOR,
            )
        )

    def _enqueue_environment_sprite(
        self,
        sprite: Any,
        visible_bounds: AABB,
        snapshot: CameraSnapshot,
    ) -> None:
        atlas = self.environment_sprite_atlas
        if atlas is None or not visible_bounds.intersects(sprite.bounds):
            return

        camera_point = world_to_camera(snapshot, sprite.anchor)
        projected = project_camera_point(snapshot, camera_point)
        if projected is None:
            return

        region = atlas.regions[sprite.sprite_id]
        scale = calculate_sprite_scale(
            snapshot.focal_px,
            camera_point.z,
            region.world_width,
            region.width,
        )
        if scale <= 0.0:
            return

        lane_depth, route_depth = _object_sort_depths(sprite.anchor, snapshot)
        self.render_sprites.append(
            RenderSprite(
                layer=RenderLayer.SOLID,
                lane_depth=lane_depth,
                route_depth=route_depth,
                depth=camera_point.z + region.depth_bias,
                object_id=sprite.object_id,
                anchor=projected,
                image_source=atlas.image,
                u=region.u,
                v=region.v,
                w=region.width,
                h=region.height,
                anchor_offset_x=region.anchor_x,
                anchor_offset_y=region.anchor_y,
                scale=scale,
                colkey=region.colkey,
            )
        )

    def _enqueue_ground_faces(
        self,
        bounds: AABB,
        snapshot: CameraSnapshot,
        stats: RenderStats,
    ) -> None:
        walkway_max_z = min(bounds.maximum.z, RIVER_START_Z)
        if bounds.minimum.z < walkway_max_z:
            walkway_bounds = AABB(
                Vec3(bounds.minimum.x, GROUND_Y, bounds.minimum.z),
                Vec3(bounds.maximum.x, GROUND_Y, walkway_max_z),
            )
            self._enqueue_face(
                make_floor_face(
                    walkway_bounds,
                    FLOOR_OBJECT_ID,
                    palette.FLOOR_FILL,
                    palette.FLOOR_OUTLINE,
                ),
                RenderLayer.FLOOR,
                snapshot,
                stats,
                object_sort_center=walkway_bounds.center,
            )

        river_min_z = max(bounds.minimum.z, RIVER_START_Z)
        if river_min_z < bounds.maximum.z:
            river_bounds = AABB(
                Vec3(bounds.minimum.x, GROUND_Y, river_min_z),
                Vec3(bounds.maximum.x, GROUND_Y, bounds.maximum.z),
            )
            self._enqueue_face(
                make_floor_face(
                    river_bounds,
                    RIVER_OBJECT_ID,
                    palette.RIVER_FILL,
                    palette.RIVER_OUTLINE,
                ),
                RenderLayer.FLOOR,
                snapshot,
                stats,
                object_sort_center=river_bounds.center,
            )

    def _enqueue_face(
        self,
        face: Face,
        layer: RenderLayer,
        snapshot: CameraSnapshot,
        stats: RenderStats,
        *,
        object_sort_center: Vec3,
    ) -> None:
        to_camera = snapshot.position - face.center
        if face.normal.dot(to_camera) <= CULL_EPSILON:
            return

        camera_points = tuple(world_to_camera(snapshot, vertex) for vertex in face.vertices)
        clipped_points = clip_camera_polygon_near(camera_points, NEAR_PLANE)
        if len(clipped_points) < 3:
            return

        projected_points: list[ProjectedPoint] = []
        for point in clipped_points:
            projected = project_camera_point(snapshot, point)
            if projected is None:
                return
            projected_points.append(projected)

        depth = _face_sort_depth(clipped_points)
        lane_depth, route_depth = _object_sort_depths(object_sort_center, snapshot)
        self.render_faces.append(
            RenderFace(
                layer=layer,
                lane_depth=lane_depth,
                route_depth=route_depth,
                depth=depth,
                object_id=face.object_id,
                face_index=face.face_index,
                points=tuple(projected_points),
                fill_color=face.fill_color,
                outline_color=face.outline_color,
            )
        )
        stats.draw_triangles += len(projected_points) - 2

    def _enqueue_world_line(
        self,
        start: Vec3,
        end: Vec3,
        layer: RenderLayer,
        object_id: int,
        line_index: int,
        color: int,
        snapshot: CameraSnapshot,
        stats: RenderStats,
        *,
        clip_bounds: AABB | None = None,
    ) -> None:
        if clip_bounds is not None:
            clipped_world = clip_segment_aabb(start, end, clip_bounds)
            if clipped_world is None:
                return
            start, end = clipped_world

        camera_start = world_to_camera(snapshot, start)
        camera_end = world_to_camera(snapshot, end)
        clipped_camera = clip_camera_segment_near(camera_start, camera_end, NEAR_PLANE)
        if clipped_camera is None:
            return

        projected_start = project_camera_point(snapshot, clipped_camera[0])
        projected_end = project_camera_point(snapshot, clipped_camera[1])
        if projected_start is None or projected_end is None:
            return

        self.render_lines.append(
            RenderLine(
                layer=layer,
                depth=(projected_start.depth + projected_end.depth) * 0.5,
                object_id=object_id,
                line_index=line_index,
                start=projected_start,
                end=projected_end,
                color=color,
            )
        )
        stats.draw_lines += 1

    def _enqueue_lane_lines(
        self,
        bounds: AABB,
        snapshot: CameraSnapshot,
        stats: RenderStats,
    ) -> None:
        for index, lane_z in enumerate(LANE_Z):
            self._enqueue_world_line(
                Vec3(bounds.minimum.x, GROUND_Y + 0.25, lane_z),
                Vec3(bounds.maximum.x, GROUND_Y + 0.25, lane_z),
                RenderLayer.FLOOR_GUIDE,
                VISIBLE_VOLUME_OBJECT_ID,
                index,
                palette.LANE_LINE,
                snapshot,
                stats,
            )

        tick_spacing = 30.0
        first_tick = int(ceil(bounds.minimum.x / tick_spacing))
        last_tick = int(floor(bounds.maximum.x / tick_spacing))
        line_index = 100
        for tick in range(first_tick, last_tick + 1):
            x = tick * tick_spacing
            self._enqueue_world_line(
                Vec3(x, GROUND_Y + 0.35, bounds.minimum.z),
                Vec3(x, GROUND_Y + 0.35, bounds.minimum.z + 5.0),
                RenderLayer.FLOOR_GUIDE,
                VISIBLE_VOLUME_OBJECT_ID,
                line_index,
                palette.LANE_TICK,
                snapshot,
                stats,
                clip_bounds=bounds,
            )
            line_index += 1

    def _enqueue_visible_volume_edges(
        self,
        bounds: AABB,
        snapshot: CameraSnapshot,
        stats: RenderStats,
    ) -> None:
        mn = bounds.minimum
        mx = bounds.maximum
        corners = (
            Vec3(mn.x, mn.y, mn.z),
            Vec3(mx.x, mn.y, mn.z),
            Vec3(mx.x, mn.y, mx.z),
            Vec3(mn.x, mn.y, mx.z),
            Vec3(mn.x, mx.y, mn.z),
            Vec3(mx.x, mx.y, mn.z),
            Vec3(mx.x, mx.y, mx.z),
            Vec3(mn.x, mx.y, mx.z),
        )
        pairs = (
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 4),
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),
        )
        for line_index, (start_index, end_index) in enumerate(pairs):
            self._enqueue_world_line(
                corners[start_index],
                corners[end_index],
                RenderLayer.DEBUG_VOLUME,
                VISIBLE_VOLUME_OBJECT_ID,
                line_index,
                palette.VOLUME_EDGE,
                snapshot,
                stats,
            )


def _draw_face(pyxel: Any, face: RenderFace) -> None:
    points = face.points
    for index in range(1, len(points) - 1):
        p0 = points[0]
        p1 = points[index]
        p2 = points[index + 1]
        pyxel.tri(
            round(p0.x),
            round(p0.y),
            round(p1.x),
            round(p1.y),
            round(p2.x),
            round(p2.y),
            face.fill_color,
        )

    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        pyxel.line(round(start.x), round(start.y), round(end.x), round(end.y), face.outline_color)


def _render_face_sort_key(face: RenderFace) -> tuple[RenderLayer, float, float, float, int, int]:
    return (
        face.layer,
        -face.lane_depth,
        -face.route_depth,
        -face.depth,
        face.object_id,
        face.face_index,
    )


def _render_sprite_sort_key(sprite: RenderSprite) -> tuple[RenderLayer, float, float, float, int, int]:
    return (
        sprite.layer,
        0.0,
        0.0,
        -sprite.depth,
        sprite.object_id,
        0,
    )


def _object_sort_depths(center: Vec3, snapshot: CameraSnapshot) -> tuple[float, float]:
    return center.z * snapshot.forward.z, center.x * snapshot.forward.x


def _face_sort_depth(camera_points: tuple[Vec3, ...]) -> float:
    return min(point.z for point in camera_points)


def _draw_sprite(pyxel: Any, sprite: RenderSprite) -> None:
    x = round(sprite.anchor.x - sprite.anchor_offset_x * sprite.scale)
    y = round(sprite.anchor.y - sprite.anchor_offset_y * sprite.scale)
    pyxel.blt(
        x,
        y,
        sprite.image_source,
        sprite.u,
        sprite.v,
        sprite.w,
        sprite.h,
        sprite.colkey,
        scale=sprite.scale,
    )


def _draw_line(pyxel: Any, line: RenderLine) -> None:
    pyxel.line(
        round(line.start.x),
        round(line.start.y),
        round(line.end.x),
        round(line.end.y),
        line.color,
    )
