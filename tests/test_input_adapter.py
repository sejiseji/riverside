from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from unittest import TestCase

from three_line_explorer.config import (
    CameraShotId,
    DT,
    STICK_LANE_REPEAT_DELAY_SECONDS,
    STICK_LANE_STEP_PX,
)
from three_line_explorer.input import InputAdapter, StickBasis


@dataclass(slots=True)
class FakePyxel:
    MOUSE_BUTTON_LEFT: int = 1
    KEY_UP: int = 2
    KEY_DOWN: int = 3
    KEY_LEFT: int = 4
    KEY_RIGHT: int = 5
    KEY_1: int = 6
    KEY_2: int = 7
    KEY_3: int = 8
    KEY_C: int = 9
    KEY_W: int = 10
    KEY_S: int = 11
    KEY_R: int = 12
    KEY_D: int = 13
    KEY_B: int = 14
    KEY_L: int = 15
    KEY_J: int = 16
    KEY_K: int = 17
    KEY_ESCAPE: int = 18
    mouse_x: int = 0
    mouse_y: int = 0
    down: set[int] = field(default_factory=set)
    pressed: set[int] = field(default_factory=set)
    released: set[int] = field(default_factory=set)

    def btn(self, key: int) -> bool:
        return key in self.down

    def btnp(self, key: int) -> bool:
        return key in self.pressed

    def btnr(self, key: int) -> bool:
        return key in self.released

    def pointer_press(self, x: int, y: int) -> None:
        self.mouse_x = x
        self.mouse_y = y
        self.down = {self.MOUSE_BUTTON_LEFT}
        self.pressed = {self.MOUSE_BUTTON_LEFT}
        self.released = set()

    def pointer_hold(self, x: int, y: int) -> None:
        self.mouse_x = x
        self.mouse_y = y
        self.down = {self.MOUSE_BUTTON_LEFT}
        self.pressed = set()
        self.released = set()

    def pointer_release(self, x: int, y: int) -> None:
        self.mouse_x = x
        self.mouse_y = y
        self.down = set()
        self.pressed = set()
        self.released = {self.MOUSE_BUTTON_LEFT}


class InputAdapterTests(TestCase):
    def test_drag_up_moves_forward_until_release(self) -> None:
        adapter = InputAdapter()
        pyxel = FakePyxel()

        pyxel.pointer_press(196, 700)
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_HIGH, DT)
        self.assertEqual(intent.move_axis, 0.0)

        pyxel.pointer_hold(196, 660)
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_HIGH, DT)
        self.assertEqual(intent.move_axis, 1.0)
        self.assertTrue(adapter.pointer.stick_active)

        pyxel.pointer_release(196, 660)
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_HIGH, DT)
        self.assertEqual(intent.move_axis, 0.0)
        self.assertFalse(adapter.pointer.stick_active)

    def test_horizontal_drag_emits_screen_lane_steps_by_distance(self) -> None:
        adapter = InputAdapter()
        pyxel = FakePyxel()

        pyxel.pointer_press(196, 700)
        adapter.read(pyxel, CameraShotId.REAR_RIGHT_HIGH, DT)

        pyxel.pointer_hold(round(196 + STICK_LANE_STEP_PX - 1), 700)
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_HIGH, DT)
        self.assertEqual(intent.lane_screen_step, 0)

        pyxel.pointer_hold(round(196 + STICK_LANE_STEP_PX), 700)
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_HIGH, DT)
        self.assertEqual(intent.lane_screen_step, 1)

    def test_drag_uses_camera_aligned_stick_basis(self) -> None:
        adapter = InputAdapter()
        pyxel = FakePyxel()
        inv_sqrt2 = 1.0 / sqrt(2.0)
        basis = StickBasis(
            move_forward_x=inv_sqrt2,
            move_forward_y=-inv_sqrt2,
            lane_screen_x=inv_sqrt2,
            lane_screen_y=inv_sqrt2,
        )

        pyxel.pointer_press(196, 700)
        adapter.read(pyxel, CameraShotId.REAR_RIGHT_HIGH, DT, basis)

        pyxel.pointer_hold(196 + 40, 700 - 40)
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_HIGH, DT, basis)
        self.assertEqual(intent.move_axis, 1.0)
        self.assertEqual(intent.lane_screen_step, 0)

        lane_drag = (STICK_LANE_STEP_PX + 2.0) * inv_sqrt2
        pyxel.pointer_hold(round(196 + lane_drag), round(700 + lane_drag))
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_HIGH, DT, basis)
        self.assertEqual(intent.move_axis, 0.0)
        self.assertEqual(intent.lane_screen_step, 1)

    def test_horizontal_drag_waits_before_repeating_lane_step(self) -> None:
        adapter = InputAdapter()
        pyxel = FakePyxel()

        pyxel.pointer_press(196, 700)
        adapter.read(pyxel, CameraShotId.REAR_RIGHT_HIGH, DT)

        pyxel.pointer_hold(round(196 + STICK_LANE_STEP_PX), 700)
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_HIGH, DT)
        self.assertEqual(intent.lane_screen_step, 1)

        pyxel.pointer_hold(round(196 + STICK_LANE_STEP_PX * 2), 700)
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_HIGH, DT)
        self.assertEqual(intent.lane_screen_step, 0)

        repeated = 0
        frames = int(STICK_LANE_REPEAT_DELAY_SECONDS / DT) + 2
        for _ in range(frames):
            intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_HIGH, DT)
            repeated = intent.lane_screen_step
            if repeated != 0:
                break

        self.assertEqual(repeated, 1)

    def test_camera_button_tap_still_requests_camera(self) -> None:
        adapter = InputAdapter()
        pyxel = FakePyxel()

        pyxel.pointer_press(60, 18)
        adapter.read(pyxel, CameraShotId.REAR_RIGHT_HIGH, DT)

        pyxel.pointer_release(60, 18)
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_HIGH, DT)
        self.assertEqual(intent.requested_camera, CameraShotId.FRONT_RIGHT_CLOSE)
