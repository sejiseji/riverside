from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from math import pi, sqrt
from typing import Protocol

from three_line_explorer.config import (
    DT,
    LANE_COUNT,
    LANE_HALF_LIFE,
    LANE_SNAP_EPSILON,
    LANE_TURN_DELAY_SECONDS,
    LANE_Z,
    PLAYER_ACCELERATION,
    PLAYER_DECELERATION,
    PLAYER_MAX_SPEED,
    PLAYER_MOVE_READY_RADIANS,
    PLAYER_WALK_FRAME_DISTANCE,
    PLAYER_WALK_PHASE_WRAP,
    PLAYER_SIZE_X,
    PLAYER_SIZE_Y,
    PLAYER_SIZE_Z,
    PLAYER_START_FACING,
    PLAYER_START_LANE,
    PLAYER_START_X,
    STAGE_MAX_X,
    STAGE_MIN_X,
    TURN_HALF_LIFE,
)
from three_line_explorer.math3d import (
    AABB,
    Vec3,
    clamp,
    clamp_int,
    half_life_alpha,
    lerp_angle,
    move_toward,
    shortest_angle_delta,
)


class CollisionSolid(Protocol):
    bounds: AABB


CollisionProvider = Callable[[AABB], Iterable[CollisionSolid]]


@dataclass(slots=True)
class PlayerState:
    x: float
    z: float
    velocity_x: float
    target_lane_index: int
    facing: int
    target_yaw: float
    pending_lane_step: int
    lane_turn_delay_remaining: float
    render_yaw: float
    walk_phase: float
    last_move_distance: float


def player_min_x() -> float:
    return STAGE_MIN_X + PLAYER_SIZE_X * 0.5


def player_max_x() -> float:
    return STAGE_MAX_X - PLAYER_SIZE_X * 0.5


def player_bounds_at(x: float, z: float) -> AABB:
    return AABB(
        Vec3(x - PLAYER_SIZE_X * 0.5, 0.0, z - PLAYER_SIZE_Z * 0.5),
        Vec3(x + PLAYER_SIZE_X * 0.5, PLAYER_SIZE_Y, z + PLAYER_SIZE_Z * 0.5),
    )


def player_swept_bounds(
    start_x: float,
    start_z: float,
    end_x: float,
    end_z: float,
) -> AABB:
    start = player_bounds_at(start_x, start_z)
    end = player_bounds_at(end_x, end_z)
    return AABB(
        Vec3(
            min(start.minimum.x, end.minimum.x),
            min(start.minimum.y, end.minimum.y),
            min(start.minimum.z, end.minimum.z),
        ),
        Vec3(
            max(start.maximum.x, end.maximum.x),
            max(start.maximum.y, end.maximum.y),
            max(start.maximum.z, end.maximum.z),
        ),
    )


def create_player() -> PlayerState:
    return PlayerState(
        x=PLAYER_START_X,
        z=LANE_Z[int(PLAYER_START_LANE)],
        velocity_x=0.0,
        target_lane_index=int(PLAYER_START_LANE),
        facing=PLAYER_START_FACING,
        target_yaw=0.0 if PLAYER_START_FACING > 0 else pi,
        pending_lane_step=0,
        lane_turn_delay_remaining=0.0,
        render_yaw=0.0 if PLAYER_START_FACING > 0 else pi,
        walk_phase=0.0,
        last_move_distance=0.0,
    )


def reset_player(player: PlayerState) -> None:
    fresh = create_player()
    player.x = fresh.x
    player.z = fresh.z
    player.velocity_x = fresh.velocity_x
    player.target_lane_index = fresh.target_lane_index
    player.facing = fresh.facing
    player.target_yaw = fresh.target_yaw
    player.pending_lane_step = fresh.pending_lane_step
    player.lane_turn_delay_remaining = fresh.lane_turn_delay_remaining
    player.render_yaw = fresh.render_yaw
    player.walk_phase = fresh.walk_phase
    player.last_move_distance = fresh.last_move_distance


def change_lane_by_world_step(player: PlayerState, world_lane_step: int) -> None:
    player.target_lane_index = clamp_int(
        player.target_lane_index + world_lane_step,
        0,
        LANE_COUNT - 1,
    )


def request_lane_change_by_world_step(player: PlayerState, world_lane_step: int) -> None:
    if world_lane_step == 0:
        return

    player.target_yaw = _lane_step_yaw(world_lane_step)
    target_lane_index = clamp_int(
        player.target_lane_index + world_lane_step,
        0,
        LANE_COUNT - 1,
    )
    if target_lane_index == player.target_lane_index:
        player.pending_lane_step = 0
        player.lane_turn_delay_remaining = 0.0
        return

    player.pending_lane_step = 1 if world_lane_step > 0 else -1
    player.lane_turn_delay_remaining = LANE_TURN_DELAY_SECONDS


def set_lane(player: PlayerState, lane_index: int) -> None:
    player.target_lane_index = clamp_int(lane_index, 0, LANE_COUNT - 1)


def warp_player_near_left(player: PlayerState) -> None:
    player.x = player_min_x() + 2.0
    player.velocity_x = 0.0


def warp_player_near_right(player: PlayerState) -> None:
    player.x = player_max_x() - 2.0
    player.velocity_x = 0.0


def update_player(
    player: PlayerState,
    move_axis: float,
    *,
    dt: float = DT,
    collision_provider: CollisionProvider | None = None,
) -> None:
    start_x = player.x
    start_z = player.z
    move_axis = clamp(move_axis, -1.0, 1.0)
    move_direction = _move_direction(move_axis)
    target_z = LANE_Z[player.target_lane_index]
    lane_motion_active = (
        player.pending_lane_step != 0
        or abs(target_z - player.z) >= LANE_SNAP_EPSILON
    )

    if move_direction != 0 and not lane_motion_active:
        player.target_yaw = _move_yaw(move_direction)

    x_move_ready = (
        move_direction != 0
        and not lane_motion_active
        and _is_yaw_ready_for_move(player.render_yaw, _move_yaw(move_direction))
    )
    target_velocity_x = move_axis * PLAYER_MAX_SPEED if x_move_ready else 0.0
    if move_direction != 0:
        player.velocity_x = move_toward(
            player.velocity_x,
            target_velocity_x,
            (PLAYER_ACCELERATION if x_move_ready else PLAYER_DECELERATION) * dt,
        )
        player.facing = move_direction
    else:
        player.velocity_x = move_toward(player.velocity_x, 0.0, PLAYER_DECELERATION * dt)

    desired_x = clamp(player.x + player.velocity_x * dt, player_min_x(), player_max_x())
    if collision_provider is None:
        player.x = desired_x
    else:
        candidates = collision_provider(player_swept_bounds(player.x, player.z, desired_x, player.z))
        player.x, blocked_x = _resolve_x_movement(player.x, desired_x, player.z, candidates)
        if blocked_x:
            player.velocity_x = 0.0

    if player.pending_lane_step != 0:
        player.lane_turn_delay_remaining = move_toward(
            player.lane_turn_delay_remaining,
            0.0,
            dt,
        )
        if player.lane_turn_delay_remaining <= 0.0:
            change_lane_by_world_step(player, player.pending_lane_step)
            player.pending_lane_step = 0

    target_z = LANE_Z[player.target_lane_index]
    if player.pending_lane_step != 0:
        player.target_yaw = _lane_step_yaw(player.pending_lane_step)
    elif abs(target_z - player.z) >= LANE_SNAP_EPSILON:
        player.target_yaw = _lane_step_yaw(1 if target_z > player.z else -1)
    elif move_direction != 0:
        player.target_yaw = _move_yaw(move_direction)

    lane_alpha = half_life_alpha(dt, LANE_HALF_LIFE)
    desired_z = player.z + (target_z - player.z) * lane_alpha
    blocked_z = False
    if collision_provider is None:
        player.z = desired_z
    else:
        candidates = collision_provider(player_swept_bounds(player.x, player.z, player.x, desired_z))
        player.z, blocked_z = _resolve_z_movement(player.z, desired_z, player.x, candidates)
    if not blocked_z and abs(player.z - target_z) < LANE_SNAP_EPSILON:
        player.z = target_z

    player.last_move_distance = sqrt(
        (player.x - start_x) * (player.x - start_x)
        + (player.z - start_z) * (player.z - start_z)
    )
    if player.last_move_distance > 0.001:
        player.walk_phase = (
            player.walk_phase + player.last_move_distance / PLAYER_WALK_FRAME_DISTANCE
        ) % PLAYER_WALK_PHASE_WRAP

    turn_alpha = half_life_alpha(dt, TURN_HALF_LIFE)
    player.render_yaw = lerp_angle(player.render_yaw, player.target_yaw, turn_alpha)


def _lane_step_yaw(world_lane_step: int) -> float:
    return -pi * 0.5 if world_lane_step > 0 else pi * 0.5


def _move_direction(move_axis: float) -> int:
    if move_axis > 0.0:
        return 1
    if move_axis < 0.0:
        return -1
    return 0


def _move_yaw(move_direction: int) -> float:
    return 0.0 if move_direction > 0 else pi


def _is_yaw_ready_for_move(render_yaw: float, target_yaw: float) -> bool:
    return abs(shortest_angle_delta(render_yaw, target_yaw)) <= PLAYER_MOVE_READY_RADIANS


def _resolve_x_movement(
    start_x: float,
    desired_x: float,
    z: float,
    solids: Iterable[CollisionSolid],
) -> tuple[float, bool]:
    if desired_x == start_x:
        return desired_x, False

    start_bounds = player_bounds_at(start_x, z)
    resolved_x = desired_x
    blocked = False
    if desired_x > start_x:
        start_max_x = start_bounds.maximum.x
        desired_max_x = desired_x + PLAYER_SIZE_X * 0.5
        for solid in solids:
            bounds = solid.bounds
            if not _overlaps_yz(start_bounds, bounds):
                continue
            if start_max_x <= bounds.minimum.x < desired_max_x:
                resolved_x = min(resolved_x, bounds.minimum.x - PLAYER_SIZE_X * 0.5)
                blocked = True
    else:
        start_min_x = start_bounds.minimum.x
        desired_min_x = desired_x - PLAYER_SIZE_X * 0.5
        for solid in solids:
            bounds = solid.bounds
            if not _overlaps_yz(start_bounds, bounds):
                continue
            if desired_min_x < bounds.maximum.x <= start_min_x:
                resolved_x = max(resolved_x, bounds.maximum.x + PLAYER_SIZE_X * 0.5)
                blocked = True
    return resolved_x, blocked


def _resolve_z_movement(
    start_z: float,
    desired_z: float,
    x: float,
    solids: Iterable[CollisionSolid],
) -> tuple[float, bool]:
    if desired_z == start_z:
        return desired_z, False

    start_bounds = player_bounds_at(x, start_z)
    resolved_z = desired_z
    blocked = False
    if desired_z > start_z:
        start_max_z = start_bounds.maximum.z
        desired_max_z = desired_z + PLAYER_SIZE_Z * 0.5
        for solid in solids:
            bounds = solid.bounds
            if not _overlaps_xy(start_bounds, bounds):
                continue
            if start_max_z <= bounds.minimum.z < desired_max_z:
                resolved_z = min(resolved_z, bounds.minimum.z - PLAYER_SIZE_Z * 0.5)
                blocked = True
    else:
        start_min_z = start_bounds.minimum.z
        desired_min_z = desired_z - PLAYER_SIZE_Z * 0.5
        for solid in solids:
            bounds = solid.bounds
            if not _overlaps_xy(start_bounds, bounds):
                continue
            if desired_min_z < bounds.maximum.z <= start_min_z:
                resolved_z = max(resolved_z, bounds.maximum.z + PLAYER_SIZE_Z * 0.5)
                blocked = True
    return resolved_z, blocked


def _overlaps_yz(a: AABB, b: AABB) -> bool:
    return (
        _intervals_overlap(a.minimum.y, a.maximum.y, b.minimum.y, b.maximum.y)
        and _intervals_overlap(
            a.minimum.z,
            a.maximum.z,
            b.minimum.z,
            b.maximum.z,
        )
    )


def _overlaps_xy(a: AABB, b: AABB) -> bool:
    return (
        _intervals_overlap(a.minimum.x, a.maximum.x, b.minimum.x, b.maximum.x)
        and _intervals_overlap(
            a.minimum.y,
            a.maximum.y,
            b.minimum.y,
            b.maximum.y,
        )
    )


def _intervals_overlap(a_min: float, a_max: float, b_min: float, b_max: float) -> bool:
    return a_min < b_max and b_min < a_max
