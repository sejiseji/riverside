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
    VISIBLE_VOLUME_OBJECT_ID,
    VIEWPORT_H,
    VIEWPORT_W,
    VIEWPORT_X,
    VIEWPORT_Y,
)
from three_line_explorer.geometry import Face, make_aabb_faces, make_floor_face, make_player_faces
from three_line_explorer.math3d import AABB, Vec3
from three_line_explorer.player import PlayerState
from three_line_explorer.projection import ProjectedPoint, project_camera_point, world_to_camera
from three_line_explorer.stage import Stage
from three_line_explorer.visible_volume import VisibleVolumeState


@dataclass(slots=True)
class RenderFace:
    layer: RenderLayer
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

    @classmethod
    def create(cls) -> Renderer:
        return cls(render_faces=[], render_lines=[])

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
        stats = self.build_scene(
            stage,
            visible_volume,
            player,
            snapshot,
            show_volume=show_volume,
            show_lanes=show_lanes,
        )

        pyxel.clip(VIEWPORT_X, VIEWPORT_Y, VIEWPORT_W, VIEWPORT_H)
        for face in sorted(self.render_faces, key=lambda item: (item.layer, -item.depth, item.object_id, item.face_index)):
            _draw_face(pyxel, face)
        for line in sorted(self.render_lines, key=lambda item: (item.layer, -item.depth, item.object_id, item.line_index)):
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
        show_volume: bool,
        show_lanes: bool,
    ) -> RenderStats:
        self.render_faces.clear()
        self.render_lines.clear()
        stats = RenderStats()

        floor_bounds = AABB(
            Vec3(visible_volume.bounds.minimum.x, GROUND_Y, visible_volume.bounds.minimum.z),
            Vec3(visible_volume.bounds.maximum.x, GROUND_Y, visible_volume.bounds.maximum.z),
        )
        floor_face = make_floor_face(
            floor_bounds,
            FLOOR_OBJECT_ID,
            palette.FLOOR_FILL,
            palette.FLOOR_OUTLINE,
        )
        self._enqueue_face(floor_face, RenderLayer.FLOOR, snapshot, stats)

        candidates = stage.candidate_solids(visible_volume.bounds)
        stats.candidate_objects = len(candidates)
        for solid in candidates:
            clipped_bounds = intersect_aabb(solid.bounds, visible_volume.bounds)
            if clipped_bounds is None:
                continue
            if visible_volume.bounds.contains_aabb(solid.bounds):
                faces = solid.faces
            else:
                stats.clipped_boxes += 1
                faces = make_aabb_faces(
                    clipped_bounds,
                    solid.object_id,
                    solid.side_color,
                    solid.top_color,
                    solid.outline_color,
                )
            for face in faces:
                self._enqueue_face(face, RenderLayer.SOLID, snapshot, stats)

        for face in make_player_faces(
            PLAYER_OBJECT_ID,
            player.x,
            player.z,
            player.render_yaw,
            outline_color=palette.PLAYER_OUTLINE,
        ):
            self._enqueue_face(face, RenderLayer.SOLID, snapshot, stats)

        if show_lanes:
            self._enqueue_lane_lines(visible_volume.bounds, snapshot, stats)
        if show_volume:
            self._enqueue_visible_volume_edges(visible_volume.bounds, snapshot, stats)

        stats.visible_faces = len(self.render_faces)
        return stats

    def _enqueue_face(
        self,
        face: Face,
        layer: RenderLayer,
        snapshot: CameraSnapshot,
        stats: RenderStats,
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
        self.render_faces.append(
            RenderFace(
                layer=layer,
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


def _face_sort_depth(camera_points: tuple[Vec3, ...]) -> float:
    return min(point.z for point in camera_points)


def _draw_line(pyxel: Any, line: RenderLine) -> None:
    pyxel.line(
        round(line.start.x),
        round(line.start.y),
        round(line.end.x),
        round(line.end.y),
        line.color,
    )
