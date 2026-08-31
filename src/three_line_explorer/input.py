from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from typing import Any

from three_line_explorer.config import (
    CameraShotId,
    STICK_DEAD_ZONE_PX,
    STICK_LANE_REPEAT_DELAY_SECONDS,
    STICK_LANE_STEP_PX,
    TAP_MAX_DISTANCE,
    TAP_MAX_SECONDS,
)
from three_line_explorer.inspection import PromptSnapshot, ScreenRect


CAMERA_BUTTON_RECTS: tuple[tuple[int, int, int, int, CameraShotId], ...] = (
    (12, 10, 34, 26, CameraShotId.REAR_RIGHT_LOW),
    (52, 10, 34, 26, CameraShotId.FRONT_RIGHT_CLOSE),
    (92, 10, 34, 26, CameraShotId.REAR_LEFT_SHALLOW),
)


@dataclass(slots=True)
class ControlIntent:
    move_axis: float
    lane_screen_step: int
    requested_camera: CameraShotId | None
    inspection_prompt_object_id: str | None
    text_panel_advance_requested: bool
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
    inspection_prompt_object_id: str | None = None
    text_panel_advance_requested: bool = False


@dataclass(frozen=True, slots=True)
class StickBasis:
    move_forward_x: float = 1.0
    move_forward_y: float = 0.0
    lane_screen_x: float = 0.0
    lane_screen_y: float = -1.0

    def components(self, drag_x: float, drag_y: float) -> tuple[float, float]:
        determinant = (
            self.move_forward_x * self.lane_screen_y
            - self.move_forward_y * self.lane_screen_x
        )
        if abs(determinant) < 1e-5:
            return (
                drag_x * self.move_forward_x + drag_y * self.move_forward_y,
                drag_x * self.lane_screen_x + drag_y * self.lane_screen_y,
            )
        move_component = (
            drag_x * self.lane_screen_y - drag_y * self.lane_screen_x
        ) / determinant
        lane_component = (
            self.move_forward_x * drag_y - self.move_forward_y * drag_x
        ) / determinant
        return move_component, lane_component

    def vector_from_components(
        self,
        move_component: float,
        lane_component: float,
    ) -> tuple[float, float]:
        return (
            self.move_forward_x * move_component + self.lane_screen_x * lane_component,
            self.move_forward_y * move_component + self.lane_screen_y * lane_component,
        )

    def almost_equals(self, other: StickBasis) -> bool:
        return (
            abs(self.move_forward_x - other.move_forward_x) < 1e-5
            and abs(self.move_forward_y - other.move_forward_y) < 1e-5
            and abs(self.lane_screen_x - other.lane_screen_x) < 1e-5
            and abs(self.lane_screen_y - other.lane_screen_y) < 1e-5
        )


@dataclass(slots=True)
class PointerTracker:
    pressed: bool = False
    mode: str = "none"
    start_x: float = 0.0
    start_y: float = 0.0
    lane_anchor_component: float = 0.0
    lane_cooldown_remaining: float = 0.0
    drag_x: float = 0.0
    drag_y: float = 0.0
    elapsed: float = 0.0
    last_stick_basis: StickBasis = field(default_factory=StickBasis)
    captured_object_id: str | None = None
    panel_tap_started_inside: bool = False

    def update(
        self,
        pyxel: Any,
        dt: float,
        stick_basis: StickBasis,
        *,
        prompt_snapshot: PromptSnapshot | None = None,
        panel_open: bool = False,
        panel_rect: ScreenRect | None = None,
    ) -> PointerIntent:
        intent = PointerIntent()

        if _btnp(pyxel, "MOUSE_BUTTON_LEFT"):
            self.pressed = True
            self.mode = _pointer_down_mode(
                pyxel.mouse_x,
                pyxel.mouse_y,
                prompt_snapshot=prompt_snapshot,
                panel_open=panel_open,
                panel_rect=panel_rect,
            )
            self.captured_object_id = (
                prompt_snapshot.object_id if self.mode == "inspection_tap" else None
            )
            self.panel_tap_started_inside = (
                self.mode == "panel_tap"
                and panel_rect is not None
                and panel_rect.contains(pyxel.mouse_x, pyxel.mouse_y)
            )
            self.start_x = float(pyxel.mouse_x)
            self.start_y = float(pyxel.mouse_y)
            self.lane_anchor_component = 0.0
            self.lane_cooldown_remaining = 0.0
            self.drag_x = 0.0
            self.drag_y = 0.0
            self.elapsed = 0.0
            self.last_stick_basis = stick_basis
            return intent

        if not self.pressed:
            return intent

        self.elapsed += dt
        self.lane_cooldown_remaining = max(0.0, self.lane_cooldown_remaining - dt)
        current_x = float(pyxel.mouse_x)
        current_y = float(pyxel.mouse_y)
        self.drag_x = current_x - self.start_x
        self.drag_y = current_y - self.start_y
        if self.mode == "stick" and not self.last_stick_basis.almost_equals(stick_basis):
            move_component, lane_component = self.last_stick_basis.components(
                self.drag_x,
                self.drag_y,
            )
            self.drag_x, self.drag_y = stick_basis.vector_from_components(
                move_component,
                lane_component,
            )
            self.start_x = current_x - self.drag_x
            self.start_y = current_y - self.drag_y
            self.last_stick_basis = stick_basis
        move_component, lane_component = stick_basis.components(self.drag_x, self.drag_y)

        if self.mode == "stick" and _btn(pyxel, "MOUSE_BUTTON_LEFT"):
            intent.move_axis = _stick_move_axis(move_component)
            lane_delta = lane_component - self.lane_anchor_component
            if (
                self.lane_cooldown_remaining <= 0.0
                and abs(lane_delta) >= STICK_LANE_STEP_PX
                and abs(lane_component) >= STICK_DEAD_ZONE_PX
            ):
                intent.lane_screen_step = 1 if lane_delta > 0.0 else -1
                self.lane_anchor_component += intent.lane_screen_step * STICK_LANE_STEP_PX
                self.lane_cooldown_remaining = STICK_LANE_REPEAT_DELAY_SECONDS

        if _btnr(pyxel, "MOUSE_BUTTON_LEFT"):
            was_tap = _is_short_tap(current_x, current_y, self.start_x, self.start_y, self.elapsed)
            if self.mode == "camera_tap" and was_tap:
                intent.requested_camera = _camera_button_at(current_x, current_y)
            elif self.mode == "inspection_tap" and was_tap:
                intent.inspection_prompt_object_id = self.captured_object_id
            elif (
                self.mode == "panel_tap"
                and was_tap
                and self.panel_tap_started_inside
                and panel_rect is not None
                and panel_rect.contains(current_x, current_y)
            ):
                intent.text_panel_advance_requested = True
            self.reset()

        return intent

    def reset(self) -> None:
        self.pressed = False
        self.mode = "none"
        self.start_x = 0.0
        self.start_y = 0.0
        self.lane_anchor_component = 0.0
        self.lane_cooldown_remaining = 0.0
        self.drag_x = 0.0
        self.drag_y = 0.0
        self.elapsed = 0.0
        self.last_stick_basis = StickBasis()
        self.captured_object_id = None
        self.panel_tap_started_inside = False

    @property
    def stick_active(self) -> bool:
        return self.pressed and self.mode == "stick"


@dataclass(slots=True)
class InputAdapter:
    pointer: PointerTracker = field(default_factory=PointerTracker)

    def read(
        self,
        pyxel: Any,
        current_camera: CameraShotId,
        dt: float,
        stick_basis: StickBasis | None = None,
        *,
        prompt_snapshot: PromptSnapshot | None = None,
        panel_open: bool = False,
        panel_rect: ScreenRect | None = None,
    ) -> ControlIntent:
        if stick_basis is None:
            stick_basis = StickBasis()

        requested_camera: CameraShotId | None = None
        lane_screen_step = 0
        pointer_intent = self.pointer.update(
            pyxel,
            dt,
            stick_basis,
            prompt_snapshot=prompt_snapshot,
            panel_open=panel_open,
            panel_rect=panel_rect,
        )

        if panel_open:
            return ControlIntent(
                move_axis=0.0,
                lane_screen_step=0,
                requested_camera=None,
                inspection_prompt_object_id=None,
                text_panel_advance_requested=(
                    pointer_intent.text_panel_advance_requested
                    or _panel_advance_key_pressed(pyxel)
                ),
                reset_requested=_btnp(pyxel, "KEY_R"),
                debug_toggle_requested=_btnp(pyxel, "KEY_H"),
                debug_volume_toggle_requested=_btnp(pyxel, "KEY_B"),
                debug_lanes_toggle_requested=_btnp(pyxel, "KEY_L"),
                warp_left_requested=False,
                warp_right_requested=False,
                quit_requested=_btnp(pyxel, "KEY_ESCAPE"),
            )

        if _btnp(pyxel, "KEY_1"):
            requested_camera = CameraShotId.REAR_RIGHT_LOW
        elif _btnp(pyxel, "KEY_2"):
            requested_camera = CameraShotId.FRONT_RIGHT_CLOSE
        elif _btnp(pyxel, "KEY_3"):
            requested_camera = CameraShotId.REAR_LEFT_SHALLOW
        elif _btnp(pyxel, "KEY_C"):
            requested_camera = next_camera_shot(current_camera)

        if _btnp(pyxel, "KEY_UP") or _btnp(pyxel, "KEY_W"):
            lane_screen_step = 1
        elif _btnp(pyxel, "KEY_DOWN") or _btnp(pyxel, "KEY_S"):
            lane_screen_step = -1

        if pointer_intent.requested_camera is not None:
            requested_camera = pointer_intent.requested_camera
        if pointer_intent.lane_screen_step != 0:
            lane_screen_step = pointer_intent.lane_screen_step

        keyboard_screen_axis = 0.0
        if _btn(pyxel, "KEY_RIGHT") or _btn(pyxel, "KEY_D"):
            keyboard_screen_axis += 1.0
        if _btn(pyxel, "KEY_LEFT") or _btn(pyxel, "KEY_A"):
            keyboard_screen_axis -= 1.0
        keyboard_axis = _keyboard_move_axis(keyboard_screen_axis, stick_basis)

        inspection_prompt_object_id = pointer_intent.inspection_prompt_object_id
        move_axis = keyboard_axis if keyboard_axis != 0.0 else pointer_intent.move_axis
        if inspection_prompt_object_id is not None:
            move_axis = 0.0
            lane_screen_step = 0
            requested_camera = None

        return ControlIntent(
            move_axis=move_axis,
            lane_screen_step=lane_screen_step,
            requested_camera=requested_camera,
            inspection_prompt_object_id=inspection_prompt_object_id,
            text_panel_advance_requested=False,
            reset_requested=_btnp(pyxel, "KEY_R"),
            debug_toggle_requested=_btnp(pyxel, "KEY_H"),
            debug_volume_toggle_requested=_btnp(pyxel, "KEY_B"),
            debug_lanes_toggle_requested=_btnp(pyxel, "KEY_L"),
            warp_left_requested=_btnp(pyxel, "KEY_J"),
            warp_right_requested=_btnp(pyxel, "KEY_K"),
            quit_requested=_btnp(pyxel, "KEY_ESCAPE"),
        )


def next_camera_shot(current: CameraShotId) -> CameraShotId:
    shots = tuple(CameraShotId)
    return shots[(shots.index(current) + 1) % len(shots)]


def _stick_move_axis(move_component: float) -> float:
    if abs(move_component) < STICK_DEAD_ZONE_PX:
        return 0.0
    return 1.0 if move_component > 0.0 else -1.0


def _keyboard_move_axis(screen_axis: float, stick_basis: StickBasis) -> float:
    if screen_axis == 0.0:
        return 0.0
    right_move_component, _ = stick_basis.components(STICK_DEAD_ZONE_PX, 0.0)
    return screen_axis if right_move_component >= 0.0 else -screen_axis


def _camera_button_at(x: float, y: float) -> CameraShotId | None:
    for rect_x, rect_y, rect_w, rect_h, shot_id in CAMERA_BUTTON_RECTS:
        if _in_rect(x, y, rect_x, rect_y, rect_w, rect_h):
            return shot_id
    return None


def _pointer_down_mode(
    x: float,
    y: float,
    *,
    prompt_snapshot: PromptSnapshot | None,
    panel_open: bool,
    panel_rect: ScreenRect | None,
) -> str:
    if panel_open:
        return "panel_tap"
    if _camera_button_at(x, y) is not None:
        return "camera_tap"
    if (
        prompt_snapshot is not None
        and prompt_snapshot.visible
        and prompt_snapshot.hitbox.contains(x, y)
    ):
        return "inspection_tap"
    return "stick"


def _is_short_tap(
    current_x: float,
    current_y: float,
    start_x: float,
    start_y: float,
    elapsed: float,
) -> bool:
    return (
        elapsed <= TAP_MAX_SECONDS
        and hypot(current_x - start_x, current_y - start_y) <= TAP_MAX_DISTANCE
    )


def _panel_advance_key_pressed(pyxel: Any) -> bool:
    return (
        _btnp(pyxel, "KEY_Z")
        or _btnp(pyxel, "KEY_RETURN")
        or _btnp(pyxel, "KEY_SPACE")
    )


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
