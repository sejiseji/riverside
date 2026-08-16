from __future__ import annotations

from dataclasses import dataclass
from math import pi

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
    PLAYER_SIZE_X,
    PLAYER_START_FACING,
    PLAYER_START_LANE,
    PLAYER_START_X,
    STAGE_MAX_X,
    STAGE_MIN_X,
    TURN_HALF_LIFE,
)
from three_line_explorer.math3d import clamp, clamp_int, half_life_alpha, lerp_angle, move_toward


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


def player_min_x() -> float:
    return STAGE_MIN_X + PLAYER_SIZE_X * 0.5


def player_max_x() -> float:
    return STAGE_MAX_X - PLAYER_SIZE_X * 0.5


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


def update_player(player: PlayerState, move_axis: float, *, dt: float = DT) -> None:
    move_axis = clamp(move_axis, -1.0, 1.0)
    target_velocity_x = move_axis * PLAYER_MAX_SPEED
    if move_axis != 0.0:
        player.velocity_x = move_toward(
            player.velocity_x,
            target_velocity_x,
            PLAYER_ACCELERATION * dt,
        )
        player.facing = 1 if move_axis > 0.0 else -1
    else:
        player.velocity_x = move_toward(player.velocity_x, 0.0, PLAYER_DECELERATION * dt)

    player.x = clamp(player.x + player.velocity_x * dt, player_min_x(), player_max_x())

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
    elif move_axis != 0.0:
        player.target_yaw = 0.0 if move_axis > 0.0 else pi

    lane_alpha = half_life_alpha(dt, LANE_HALF_LIFE)
    player.z += (target_z - player.z) * lane_alpha
    if abs(player.z - target_z) < LANE_SNAP_EPSILON:
        player.z = target_z

    turn_alpha = half_life_alpha(dt, TURN_HALF_LIFE)
    player.render_yaw = lerp_angle(player.render_yaw, player.target_yaw, turn_alpha)


def _lane_step_yaw(world_lane_step: int) -> float:
    return -pi * 0.5 if world_lane_step > 0 else pi * 0.5
