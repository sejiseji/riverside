from __future__ import annotations

from dataclasses import dataclass, field

from three_line_explorer.config import PLAYER_SIZE_X, PLAYER_SIZE_Y, PLAYER_SIZE_Z
from three_line_explorer.math3d import AABB, Vec3, rotate_y


@dataclass(frozen=True, slots=True)
class Face:
    object_id: int
    face_index: int
    vertices: tuple[Vec3, ...]
    normal: Vec3
    center: Vec3
    fill_color: int
    outline_color: int


def average_vec3(points: tuple[Vec3, ...]) -> Vec3:
    inv = 1.0 / len(points)
    return Vec3(
        sum(point.x for point in points) * inv,
        sum(point.y for point in points) * inv,
        sum(point.z for point in points) * inv,
    )


def make_aabb_faces(
    bounds: AABB,
    object_id: int,
    side_color: int,
    top_color: int,
    outline_color: int,
    *,
    include_bottom: bool = True,
) -> tuple[Face, ...]:
    mn = bounds.minimum
    mx = bounds.maximum
    x0, y0, z0 = mn.x, mn.y, mn.z
    x1, y1, z1 = mx.x, mx.y, mx.z

    definitions: list[tuple[tuple[Vec3, Vec3, Vec3, Vec3], Vec3, int]] = [
        ((Vec3(x1, y0, z0), Vec3(x1, y0, z1), Vec3(x1, y1, z1), Vec3(x1, y1, z0)), Vec3(1, 0, 0), side_color),
        ((Vec3(x0, y0, z1), Vec3(x0, y0, z0), Vec3(x0, y1, z0), Vec3(x0, y1, z1)), Vec3(-1, 0, 0), side_color),
        ((Vec3(x1, y0, z1), Vec3(x0, y0, z1), Vec3(x0, y1, z1), Vec3(x1, y1, z1)), Vec3(0, 0, 1), side_color),
        ((Vec3(x0, y0, z0), Vec3(x1, y0, z0), Vec3(x1, y1, z0), Vec3(x0, y1, z0)), Vec3(0, 0, -1), side_color),
        ((Vec3(x0, y1, z0), Vec3(x1, y1, z0), Vec3(x1, y1, z1), Vec3(x0, y1, z1)), Vec3(0, 1, 0), top_color),
    ]
    if include_bottom:
        definitions.append(
            ((Vec3(x0, y0, z1), Vec3(x1, y0, z1), Vec3(x1, y0, z0), Vec3(x0, y0, z0)), Vec3(0, -1, 0), side_color)
        )

    faces: list[Face] = []
    for face_index, (vertices, normal, fill_color) in enumerate(definitions):
        faces.append(
            Face(
                object_id=object_id,
                face_index=face_index,
                vertices=vertices,
                normal=normal,
                center=average_vec3(vertices),
                fill_color=fill_color,
                outline_color=outline_color,
            )
        )
    return tuple(faces)


@dataclass(frozen=True, slots=True)
class AabbSolid:
    object_id: int
    bounds: AABB
    side_color: int
    top_color: int
    outline_color: int
    faces: tuple[Face, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "faces",
            make_aabb_faces(
                self.bounds,
                self.object_id,
                self.side_color,
                self.top_color,
                self.outline_color,
            ),
        )


def make_floor_face(bounds: AABB, object_id: int, fill_color: int, outline_color: int) -> Face:
    vertices = (
        Vec3(bounds.minimum.x, bounds.minimum.y, bounds.minimum.z),
        Vec3(bounds.maximum.x, bounds.minimum.y, bounds.minimum.z),
        Vec3(bounds.maximum.x, bounds.minimum.y, bounds.maximum.z),
        Vec3(bounds.minimum.x, bounds.minimum.y, bounds.maximum.z),
    )
    return Face(
        object_id=object_id,
        face_index=0,
        vertices=vertices,
        normal=Vec3(0.0, 1.0, 0.0),
        center=average_vec3(vertices),
        fill_color=fill_color,
        outline_color=outline_color,
    )


PLAYER_FACE_DEFINITIONS = (
    (
        (Vec3(0.5, -0.5, -0.5), Vec3(0.5, -0.5, 0.5), Vec3(0.5, 0.5, 0.5), Vec3(0.5, 0.5, -0.5)),
        Vec3(1.0, 0.0, 0.0),
        8,
    ),
    (
        (Vec3(-0.5, -0.5, 0.5), Vec3(-0.5, -0.5, -0.5), Vec3(-0.5, 0.5, -0.5), Vec3(-0.5, 0.5, 0.5)),
        Vec3(-1.0, 0.0, 0.0),
        2,
    ),
    (
        (Vec3(-0.5, -0.5, -0.5), Vec3(0.5, -0.5, -0.5), Vec3(0.5, 0.5, -0.5), Vec3(-0.5, 0.5, -0.5)),
        Vec3(0.0, 0.0, -1.0),
        11,
    ),
    (
        (Vec3(0.5, -0.5, 0.5), Vec3(-0.5, -0.5, 0.5), Vec3(-0.5, 0.5, 0.5), Vec3(0.5, 0.5, 0.5)),
        Vec3(0.0, 0.0, 1.0),
        10,
    ),
    (
        (Vec3(-0.5, 0.5, -0.5), Vec3(0.5, 0.5, -0.5), Vec3(0.5, 0.5, 0.5), Vec3(-0.5, 0.5, 0.5)),
        Vec3(0.0, 1.0, 0.0),
        12,
    ),
)


def make_player_faces(
    object_id: int,
    x: float,
    z: float,
    yaw: float,
    *,
    outline_color: int,
) -> tuple[Face, ...]:
    center = Vec3(x, PLAYER_SIZE_Y * 0.5, z)
    scale = Vec3(PLAYER_SIZE_X, PLAYER_SIZE_Y, PLAYER_SIZE_Z)
    faces: list[Face] = []
    for face_index, (unit_vertices, unit_normal, fill_color) in enumerate(PLAYER_FACE_DEFINITIONS):
        vertices = tuple(
            center
            + rotate_y(
                Vec3(
                    unit_vertex.x * scale.x,
                    unit_vertex.y * scale.y,
                    unit_vertex.z * scale.z,
                ),
                yaw,
            )
            for unit_vertex in unit_vertices
        )
        normal = rotate_y(unit_normal, yaw).normalized()
        faces.append(
            Face(
                object_id=object_id,
                face_index=face_index,
                vertices=vertices,
                normal=normal,
                center=average_vec3(vertices),
                fill_color=fill_color,
                outline_color=outline_color,
            )
        )
    return tuple(faces)
