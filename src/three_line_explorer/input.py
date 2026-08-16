from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from typing import Any

from three_line_explorer.config import (
    BOTTOM_UI_HEIGHT,
    CameraShotId,
    LEFT_EDGE_ZONE_X1,
    LEFT_EDGE_ZONE_X2,
    RIGHT_EDGE_ZONE_X1,
    RIGHT_EDGE_ZONE_X2,
    SCREEN_H,
    SCREEN_W,
    TAP_MAX_DISTANCE,
    TAP_MAX_SECONDS,
    TOP_UI_HEIGHT,
    VIEWPORT_H,
    VIEWPORT_Y,
)


CAMERA_BUTTON_RECTS: tuple[tuple[int, int, int, int, CameraShotId], ...] = (
    (12, 10, 34, 26, CameraShotId.REAR_RIGHT_HIGH),
    (52, 10, 34, 26, CameraShotId.FRONT_RIGHT_CLOSE),
    (92, 10, 34, 26, CameraShotId.REAR_LEFT_SHALLOW),
)

MOVE_BUTTON_RECTS: tuple[tuple[int, int, int, int, float, str], ...] = (
    (49, SCREEN_H - BOTTOM_UI_HEIGHT + 18, 92, 36, -1.0, "-X"),
    (151, SCREEN_H - BOTTOM_UI_HEIGHT + 18, 92, 36, 0.0, "STOP"),
    (253, SCREEN_H - BOTTOM_UI_HEIGHT + 18, 92, 36, 1.0, "+X"),
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
class PointerTracker:
    pressed: bool = False
    start_x: float = 0.0
    start_y: float = 0.0
    elapsed: float = 0.0

    def update(self, pyxel: Any, dt: float) -> tuple[float, float] | None:
        if _btnp(pyxel, "MOUSE_BUTTON_LEFT"):
            self.pressed = True
            self.start_x = float(pyxel.mouse_x)
            self.start_y = float(pyxel.mouse_y)
            self.elapsed = 0.0
            return None

        if self.pressed:
            self.elapsed += dt
            if _btnr(pyxel, "MOUSE_BUTTON_LEFT"):
                end_x = float(pyxel.mouse_x)
                end_y = float(pyxel.mouse_y)
                was_tap = (
                    self.elapsed <= TAP_MAX_SECONDS
                    and hypot(end_x - self.start_x, end_y - self.start_y) <= TAP_MAX_DISTANCE
                )
                self.pressed = False
                if was_tap:
                    return end_x, end_y
        return None


@dataclass(slots=True)
class InputAdapter:
    latched_move_axis: float = 0.0
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

        tap = self.pointer.update(pyxel, dt)
        if tap is not None:
            tap_camera, tap_move_axis, tap_lane_step = self._consume_tap(tap, current_camera)
            if tap_camera is not None:
                requested_camera = tap_camera
            if tap_move_axis is not None:
                self.latched_move_axis = tap_move_axis
            if tap_lane_step != 0:
                lane_screen_step = tap_lane_step

        keyboard_axis = 0.0
        if _btn(pyxel, "KEY_UP") or _btn(pyxel, "KEY_W"):
            keyboard_axis += 1.0
        if _btn(pyxel, "KEY_DOWN") or _btn(pyxel, "KEY_S"):
            keyboard_axis -= 1.0

        move_axis = keyboard_axis if keyboard_axis != 0.0 else self.latched_move_axis

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

    def _consume_tap(
        self,
        position: tuple[float, float],
        current_camera: CameraShotId,
    ) -> tuple[CameraShotId | None, float | None, int]:
        x, y = position

        for rect_x, rect_y, rect_w, rect_h, shot_id in CAMERA_BUTTON_RECTS:
            if _in_rect(x, y, rect_x, rect_y, rect_w, rect_h):
                return shot_id, None, 0

        for rect_x, rect_y, rect_w, rect_h, move_axis, _label in MOVE_BUTTON_RECTS:
            if _in_rect(x, y, rect_x, rect_y, rect_w, rect_h):
                return None, move_axis, 0

        if VIEWPORT_Y <= y <= VIEWPORT_Y + VIEWPORT_H:
            if LEFT_EDGE_ZONE_X1 <= x <= LEFT_EDGE_ZONE_X2:
                return None, None, -1
            if RIGHT_EDGE_ZONE_X1 <= x <= RIGHT_EDGE_ZONE_X2:
                return None, None, 1

        return None, None, 0


def next_camera_shot(current: CameraShotId) -> CameraShotId:
    shots = tuple(CameraShotId)
    return shots[(shots.index(current) + 1) % len(shots)]


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
