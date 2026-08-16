from __future__ import annotations

from three_line_explorer.math3d import AABB, Vec3


def intersect_aabb(first: AABB, second: AABB) -> AABB | None:
    minimum = Vec3(
        max(first.minimum.x, second.minimum.x),
        max(first.minimum.y, second.minimum.y),
        max(first.minimum.z, second.minimum.z),
    )
    maximum = Vec3(
        min(first.maximum.x, second.maximum.x),
        min(first.maximum.y, second.maximum.y),
        min(first.maximum.z, second.maximum.z),
    )
    if minimum.x >= maximum.x or minimum.y >= maximum.y or minimum.z >= maximum.z:
        return None
    return AABB(minimum, maximum)


def clip_segment_aabb(start: Vec3, end: Vec3, bounds: AABB) -> tuple[Vec3, Vec3] | None:
    t_min = 0.0
    t_max = 1.0
    delta = end - start

    for start_value, delta_value, min_value, max_value in (
        (start.x, delta.x, bounds.minimum.x, bounds.maximum.x),
        (start.y, delta.y, bounds.minimum.y, bounds.maximum.y),
        (start.z, delta.z, bounds.minimum.z, bounds.maximum.z),
    ):
        if delta_value == 0.0:
            if start_value < min_value or start_value > max_value:
                return None
            continue

        inv_delta = 1.0 / delta_value
        near_t = (min_value - start_value) * inv_delta
        far_t = (max_value - start_value) * inv_delta
        if near_t > far_t:
            near_t, far_t = far_t, near_t
        t_min = max(t_min, near_t)
        t_max = min(t_max, far_t)
        if t_min > t_max:
            return None

    return start + delta * t_min, start + delta * t_max


def clip_camera_segment_near(start: Vec3, end: Vec3, near_plane: float) -> tuple[Vec3, Vec3] | None:
    start_inside = start.z >= near_plane
    end_inside = end.z >= near_plane
    if start_inside and end_inside:
        return start, end
    if not start_inside and not end_inside:
        return None

    delta = end - start
    if delta.z == 0.0:
        return None
    t = (near_plane - start.z) / delta.z
    clipped = start + delta * t
    if start_inside:
        return start, clipped
    return clipped, end


def clip_camera_polygon_near(vertices: tuple[Vec3, ...], near_plane: float) -> tuple[Vec3, ...]:
    if not vertices:
        return ()

    output: list[Vec3] = []
    previous = vertices[-1]
    previous_inside = previous.z >= near_plane

    for current in vertices:
        current_inside = current.z >= near_plane
        if current_inside != previous_inside:
            delta = current - previous
            if delta.z != 0.0:
                t = (near_plane - previous.z) / delta.z
                output.append(previous + delta * t)
        if current_inside:
            output.append(current)
        previous = current
        previous_inside = current_inside

    return tuple(output)
