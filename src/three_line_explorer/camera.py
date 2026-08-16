from __future__ import annotations

from dataclasses import dataclass, replace
from math import cos, isfinite, sin, tan

from three_line_explorer.config import (
    CAMERA_SHOT_SPECS,
    CAMERA_TRANSITION_SECONDS,
    CameraShotId,
    HORIZONTAL_FOV,
    INITIAL_CAMERA,
    LANE_MAPPING_SWITCH_THRESHOLD_PX,
    LANE_Z,
    MOVE_MAPPING_SWITCH_THRESHOLD_PX,
    SCREEN_W,
    VIEWPORT_H,
    VIEWPORT_W,
    VIEWPORT_X,
    VIEWPORT_Y,
)
from three_line_explorer.math3d import Vec2, Vec3, WORLD_UP, lerp, lerp_angle, smootherstep
from three_line_explorer.projection import project_world_point


@dataclass(frozen=True, slots=True)
class CameraParameters:
    azimuth: float
    elevation: float
    distance: float
    target_y: float


CameraShot = CameraParameters


CAMERA_SHOTS: dict[CameraShotId, CameraShot] = {
    shot_id: CameraShot(*values) for shot_id, values in CAMERA_SHOT_SPECS.items()
}

SCREEN_INPUT_AXIS_SAMPLE_DISTANCE = 32.0


@dataclass(slots=True)
class CameraTransition:
    start_params: CameraParameters
    target_params: CameraParameters
    elapsed: float
    duration: float
    active: bool


@dataclass(slots=True)
class CameraSnapshot:
    position: Vec3
    pivot: Vec3
    forward: Vec3
    right: Vec3
    up: Vec3
    focal_px: float
    screen_center_x: float
    screen_center_y: float
    lane_screen_x: tuple[float, float, float]
    stable_lane_orientation: int
    stable_move_orientation: int
    shot_id: CameraShotId
    params: CameraParameters

    def with_input_mapping(
        self,
        lane_screen_x: tuple[float, float, float],
        stable_lane_orientation: int,
        stable_move_orientation: int,
    ) -> CameraSnapshot:
        return replace(
            self,
            lane_screen_x=lane_screen_x,
            stable_lane_orientation=stable_lane_orientation,
            stable_move_orientation=stable_move_orientation,
        )

    def with_lane_mapping(
        self,
        lane_screen_x: tuple[float, float, float],
        stable_lane_orientation: int,
    ) -> CameraSnapshot:
        return replace(
            self,
            lane_screen_x=lane_screen_x,
            stable_lane_orientation=stable_lane_orientation,
        )


def interpolate_camera_params(
    start: CameraParameters,
    target: CameraParameters,
    t: float,
) -> CameraParameters:
    return CameraParameters(
        azimuth=lerp_angle(start.azimuth, target.azimuth, t),
        elevation=lerp(start.elevation, target.elevation, t),
        distance=lerp(start.distance, target.distance, t),
        target_y=lerp(start.target_y, target.target_y, t),
    )


@dataclass(slots=True)
class CameraRig:
    current_params: CameraParameters
    current_shot_id: CameraShotId
    transition: CameraTransition

    @classmethod
    def create(cls) -> CameraRig:
        params = CAMERA_SHOTS[INITIAL_CAMERA]
        return cls(
            current_params=params,
            current_shot_id=INITIAL_CAMERA,
            transition=CameraTransition(params, params, 0.0, CAMERA_TRANSITION_SECONDS, False),
        )

    @property
    def transition_progress(self) -> float:
        if not self.transition.active:
            return 1.0
        if self.transition.duration <= 0.0:
            return 1.0
        return min(1.0, self.transition.elapsed / self.transition.duration)

    def request_shot(self, shot_id: CameraShotId) -> None:
        target = CAMERA_SHOTS[shot_id]
        if shot_id == self.current_shot_id and not self.transition.active:
            return
        if self.transition.active and self.transition.target_params == target:
            self.current_shot_id = shot_id
            return

        self.transition = CameraTransition(
            start_params=self.current_params,
            target_params=target,
            elapsed=0.0,
            duration=CAMERA_TRANSITION_SECONDS,
            active=True,
        )
        self.current_shot_id = shot_id

    def update(self, dt: float) -> None:
        if not self.transition.active:
            return

        self.transition.elapsed += dt
        raw_t = 1.0
        if self.transition.duration > 0.0:
            raw_t = min(1.0, self.transition.elapsed / self.transition.duration)
        eased_t = smootherstep(raw_t)
        self.current_params = interpolate_camera_params(
            self.transition.start_params,
            self.transition.target_params,
            eased_t,
        )
        if raw_t >= 1.0:
            self.current_params = self.transition.target_params
            self.transition.active = False


def make_camera_snapshot(
    params: CameraParameters,
    player_x: float,
    player_z: float,
    *,
    lane_screen_x: tuple[float, float, float] = (0.0, 0.0, 0.0),
    stable_lane_orientation: int = 1,
    stable_move_orientation: int = 1,
    shot_id: CameraShotId = INITIAL_CAMERA,
) -> CameraSnapshot:
    pivot = Vec3(player_x, params.target_y, player_z)
    horizontal = params.distance * cos(params.elevation)
    offset = Vec3(
        horizontal * cos(params.azimuth),
        params.distance * sin(params.elevation),
        horizontal * sin(params.azimuth),
    )
    position = pivot + offset
    forward = (pivot - position).normalized()
    right = forward.cross(WORLD_UP).normalized()
    if right.length_squared() == 0.0:
        right = Vec3(1.0, 0.0, 0.0)
    up = right.cross(forward).normalized()
    focal_px = (VIEWPORT_W * 0.5) / tan(HORIZONTAL_FOV * 0.5)

    return CameraSnapshot(
        position=position,
        pivot=pivot,
        forward=forward,
        right=right,
        up=up,
        focal_px=focal_px,
        screen_center_x=VIEWPORT_X + VIEWPORT_W * 0.5,
        screen_center_y=VIEWPORT_Y + VIEWPORT_H * 0.5,
        lane_screen_x=lane_screen_x,
        stable_lane_orientation=stable_lane_orientation,
        stable_move_orientation=stable_move_orientation,
        shot_id=shot_id,
        params=params,
    )


def compute_lane_screen_x(snapshot: CameraSnapshot, player_x: float) -> tuple[float, float, float]:
    values: list[float] = []
    for lane_z in LANE_Z:
        projected = project_world_point(snapshot, Vec3(player_x, 0.25, lane_z))
        values.append(float("nan") if projected is None else projected.x)
    return tuple(values)  # type: ignore[return-value]


def compute_screen_input_axes(
    snapshot: CameraSnapshot,
    player_x: float,
    player_z: float,
) -> tuple[Vec2, Vec2]:
    del player_x, player_z
    move_axis = Vec2(0.0, -float(snapshot.stable_move_orientation))
    lane_axis = Vec2(1.0, 0.0)
    return move_axis, lane_axis


def compute_move_screen_y_delta(
    snapshot: CameraSnapshot,
    player_x: float,
    player_z: float,
) -> float:
    origin = Vec3(player_x, 0.25, player_z)
    start = project_world_point(snapshot, origin)
    end = project_world_point(
        snapshot,
        origin + Vec3(SCREEN_INPUT_AXIS_SAMPLE_DISTANCE, 0.0, 0.0),
    )
    if start is None or end is None:
        return float("nan")
    return end.y - start.y


def update_stable_lane_orientation(
    previous_orientation: int,
    lane_screen_x: tuple[float, float, float],
) -> int:
    negative_z_x = lane_screen_x[0]
    positive_z_x = lane_screen_x[2]
    if not isfinite(negative_z_x) or not isfinite(positive_z_x):
        return 1 if previous_orientation >= 0 else -1

    measure = positive_z_x - negative_z_x
    if previous_orientation >= 0:
        if measure <= -LANE_MAPPING_SWITCH_THRESHOLD_PX:
            return -1
        return 1
    if measure >= LANE_MAPPING_SWITCH_THRESHOLD_PX:
        return 1
    return -1


def update_stable_move_orientation(previous_orientation: int, screen_y_delta: float) -> int:
    previous = 1 if previous_orientation >= 0 else -1
    if not isfinite(screen_y_delta):
        return previous

    if previous >= 0:
        if screen_y_delta >= MOVE_MAPPING_SWITCH_THRESHOLD_PX:
            return -1
        return 1
    if screen_y_delta <= -MOVE_MAPPING_SWITCH_THRESHOLD_PX:
        return 1
    return -1


def camera_button_label(shot_id: CameraShotId) -> str:
    if shot_id == CameraShotId.REAR_RIGHT_HIGH:
        return "A"
    if shot_id == CameraShotId.FRONT_RIGHT_CLOSE:
        return "B"
    return "C"


def shot_debug_name(shot_id: CameraShotId) -> str:
    return {
        CameraShotId.REAR_RIGHT_HIGH: "REAR_RIGHT_HIGH",
        CameraShotId.FRONT_RIGHT_CLOSE: "FRONT_RIGHT_CLOSE",
        CameraShotId.REAR_LEFT_SHALLOW: "REAR_LEFT_SHALLOW",
    }[shot_id]


def is_screen_x_visible(value: float) -> bool:
    return isfinite(value) and 0.0 <= value <= float(SCREEN_W)
