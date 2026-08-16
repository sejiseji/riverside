from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from typing import Any

from three_line_explorer.config import (
    CameraShotId,
    STICK_DEAD_ZONE_PX,
    STICK_LANE_STEP_PX,
    TAP_MAX_DISTANCE,
    TAP_MAX_SECONDS,
)


CAMERA_BUTTON_RECTS: tuple[tuple[int, int, int, int, CameraShotId], ...] = (
    (12, 10, 34, 26, CameraShotId.REAR_RIGHT_HIGH),
    (52, 10, 34, 26, CameraShotId.FRONT_RIGHT_CLOSE),
    (92, 10, 34, 26, CameraShotId.REAR_LEFT_SHALLOW),
)


@dataclass(slots=True)
class ControlIntent:
    move_axis: float
    lane_screen_step: int
    requested_camera: CameraShotId | None
    reset_requested: bool
    debug_toggle_requested: bool
    debug_volume_toggle_requested: bool
    debug_lanes_toggle_requested: bool
    warp_left_requested: bool
    warp_right_requested: bool
    quit_requested: bool


@dataclass(slots=True)
class PointerIntent:
    move_axis: float = 0.0
    lane_screen_step: int = 0
    requested_camera: CameraShotId | None = None


@dataclass(slots=True)
class PointerTracker:
    pressed: bool = False
    mode: str = "none"
    start_x: float = 0.0
    start_y: float = 0.0
    lane_anchor_x: float = 0.0
    drag_x: float = 0.0
    drag_y: float = 0.0
    elapsed: float = 0.0

    def update(self, pyxel: Any, dt: float) -> PointerIntent:
        intent = PointerIntent()

        if _btnp(pyxel, "MOUSE_BUTTON_LEFT"):
            self.pressed = True
            self.mode = (
                "camera_tap" if _camera_button_at(pyxel.mouse_x, pyxel.mouse_y) else "stick"
            )
            self.start_x = float(pyxel.mouse_x)
            self.start_y = float(pyxel.mouse_y)
            self.lane_anchor_x = self.start_x
            self.drag_x = 0.0
            self.drag_y = 0.0
            self.elapsed = 0.0
            return intent

        if not self.pressed:
            return intent

        self.elapsed += dt
        current_x = float(pyxel.mouse_x)
        current_y = float(pyxel.mouse_y)
        self.drag_x = current_x - self.start_x
        self.drag_y = current_y - self.start_y

        if self.mode == "stick" and _btn(pyxel, "MOUSE_BUTTON_LEFT"):
            intent.move_axis = _stick_move_axis(self.drag_x, self.drag_y)
            lane_delta = current_x - self.lane_anchor_x
            if abs(lane_delta) >= STICK_LANE_STEP_PX and abs(self.drag_x) >= STICK_DEAD_ZONE_PX:
                intent.lane_screen_step = 1 if lane_delta > 0.0 else -1
                self.lane_anchor_x += intent.lane_screen_step * STICK_LANE_STEP_PX

        if _btnr(pyxel, "MOUSE_BUTTON_LEFT"):
            was_tap = (
                self.mode == "camera_tap"
                and self.elapsed <= TAP_MAX_SECONDS
                and hypot(current_x - self.start_x, current_y - self.start_y) <= TAP_MAX_DISTANCE
            )
            if was_tap:
                intent.requested_camera = _camera_button_at(current_x, current_y)
            self.reset()

        return intent

    def reset(self) -> None:
        self.pressed = False
        self.mode = "none"
        self.start_x = 0.0
        self.start_y = 0.0
        self.lane_anchor_x = 0.0
        self.drag_x = 0.0
        self.drag_y = 0.0
        self.elapsed = 0.0

    @property
    def stick_active(self) -> bool:
        return self.pressed and self.mode == "stick"


@dataclass(slots=True)
class InputAdapter:
    pointer: PointerTracker = field(default_factory=PointerTracker)

    def read(self, pyxel: Any, current_camera: CameraShotId, dt: float) -> ControlIntent:
        requested_camera: CameraShotId | None = None
        lane_screen_step = 0

        if _btnp(pyxel, "KEY_1"):
            requested_camera = CameraShotId.REAR_RIGHT_HIGH
        elif _btnp(pyxel, "KEY_2"):
            requested_camera = CameraShotId.FRONT_RIGHT_CLOSE
        elif _btnp(pyxel, "KEY_3"):
            requested_camera = CameraShotId.REAR_LEFT_SHALLOW
        elif _btnp(pyxel, "KEY_C"):
            requested_camera = next_camera_shot(current_camera)

        if _btnp(pyxel, "KEY_LEFT"):
            lane_screen_step = -1
        elif _btnp(pyxel, "KEY_RIGHT"):
            lane_screen_step = 1

        pointer_intent = self.pointer.update(pyxel, dt)
        if pointer_intent.requested_camera is not None:
            requested_camera = pointer_intent.requested_camera
        if pointer_intent.lane_screen_step != 0:
            lane_screen_step = pointer_intent.lane_screen_step

        keyboard_axis = 0.0
        if _btn(pyxel, "KEY_UP") or _btn(pyxel, "KEY_W"):
            keyboard_axis += 1.0
        if _btn(pyxel, "KEY_DOWN") or _btn(pyxel, "KEY_S"):
            keyboard_axis -= 1.0

        move_axis = keyboard_axis if keyboard_axis != 0.0 else pointer_intent.move_axis

        return ControlIntent(
            move_axis=move_axis,
            lane_screen_step=lane_screen_step,
            requested_camera=requested_camera,
            reset_requested=_btnp(pyxel, "KEY_R"),
            debug_toggle_requested=_btnp(pyxel, "KEY_D"),
            debug_volume_toggle_requested=_btnp(pyxel, "KEY_B"),
            debug_lanes_toggle_requested=_btnp(pyxel, "KEY_L"),
            warp_left_requested=_btnp(pyxel, "KEY_J"),
            warp_right_requested=_btnp(pyxel, "KEY_K"),
            quit_requested=_btnp(pyxel, "KEY_ESCAPE"),
        )


def next_camera_shot(current: CameraShotId) -> CameraShotId:
    shots = tuple(CameraShotId)
    return shots[(shots.index(current) + 1) % len(shots)]


def _stick_move_axis(drag_x: float, drag_y: float) -> float:
    if abs(drag_y) < STICK_DEAD_ZONE_PX:
        return 0.0
    if abs(drag_y) < abs(drag_x) * 0.5:
        return 0.0
    return 1.0 if drag_y < 0.0 else -1.0


def _camera_button_at(x: float, y: float) -> CameraShotId | None:
    for rect_x, rect_y, rect_w, rect_h, shot_id in CAMERA_BUTTON_RECTS:
        if _in_rect(x, y, rect_x, rect_y, rect_w, rect_h):
            return shot_id
    return None


def _in_rect(x: float, y: float, rect_x: int, rect_y: int, rect_w: int, rect_h: int) -> bool:
    return rect_x <= x < rect_x + rect_w and rect_y <= y < rect_y + rect_h


def _btn(pyxel: Any, key_name: str) -> bool:
    if not hasattr(pyxel, key_name):
        return False
    return bool(pyxel.btn(getattr(pyxel, key_name)))


def _btnp(pyxel: Any, key_name: str) -> bool:
    if not hasattr(pyxel, key_name):
        return False
    return bool(pyxel.btnp(getattr(pyxel, key_name)))


def _btnr(pyxel: Any, key_name: str) -> bool:
    if not hasattr(pyxel, key_name):
        return False
    return bool(pyxel.btnr(getattr(pyxel, key_name)))
