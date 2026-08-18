from __future__ import annotations

from dataclasses import dataclass, field
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
    def test_drag_right_moves_forward_until_release(self) -> None:
        adapter = InputAdapter()
        pyxel = FakePyxel()

        pyxel.pointer_press(196, 700)
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT)
        self.assertEqual(intent.move_axis, 0.0)

        pyxel.pointer_hold(236, 700)
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT)
        self.assertEqual(intent.move_axis, 1.0)
        self.assertTrue(adapter.pointer.stick_active)

        pyxel.pointer_release(236, 700)
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT)
        self.assertEqual(intent.move_axis, 0.0)
        self.assertFalse(adapter.pointer.stick_active)

    def test_vertical_drag_emits_screen_lane_steps_by_distance(self) -> None:
        adapter = InputAdapter()
        pyxel = FakePyxel()

        pyxel.pointer_press(196, 700)
        adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT)

        pyxel.pointer_hold(196, round(700 - STICK_LANE_STEP_PX + 1))
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT)
        self.assertEqual(intent.lane_screen_step, 0)

        pyxel.pointer_hold(196, round(700 - STICK_LANE_STEP_PX))
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT)
        self.assertEqual(intent.lane_screen_step, 1)

    def test_drag_uses_screen_cardinal_stick_basis(self) -> None:
        adapter = InputAdapter()
        pyxel = FakePyxel()
        basis = StickBasis(
            move_forward_x=-1.0,
            move_forward_y=0.0,
            lane_screen_x=0.0,
            lane_screen_y=-1.0,
        )

        pyxel.pointer_press(196, 700)
        adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT, basis)

        pyxel.pointer_hold(236, 700)
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT, basis)
        self.assertEqual(intent.move_axis, -1.0)
        self.assertEqual(intent.lane_screen_step, 0)

        pyxel.pointer_hold(196, round(700 - STICK_LANE_STEP_PX - 2.0))
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT, basis)
        self.assertEqual(intent.move_axis, 0.0)
        self.assertEqual(intent.lane_screen_step, 1)

    def test_keyboard_horizontal_keys_follow_screen_move_orientation(self) -> None:
        adapter = InputAdapter()
        pyxel = FakePyxel()

        pyxel.down = {pyxel.KEY_RIGHT}
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT, StickBasis())
        self.assertEqual(intent.move_axis, 1.0)

        inverted_basis = StickBasis(move_forward_x=-1.0)
        intent = adapter.read(pyxel, CameraShotId.FRONT_RIGHT_CLOSE, DT, inverted_basis)
        self.assertEqual(intent.move_axis, -1.0)

        pyxel.down = {pyxel.KEY_LEFT}
        intent = adapter.read(pyxel, CameraShotId.FRONT_RIGHT_CLOSE, DT, inverted_basis)
        self.assertEqual(intent.move_axis, 1.0)

    def test_keyboard_vertical_keys_emit_lane_steps(self) -> None:
        adapter = InputAdapter()
        pyxel = FakePyxel()

        pyxel.pressed = {pyxel.KEY_UP}
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT, StickBasis())
        self.assertEqual(intent.move_axis, 0.0)
        self.assertEqual(intent.lane_screen_step, 1)

        pyxel.pressed = {pyxel.KEY_DOWN}
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT, StickBasis())
        self.assertEqual(intent.move_axis, 0.0)
        self.assertEqual(intent.lane_screen_step, -1)

    def test_active_drag_is_rebased_when_stick_basis_changes(self) -> None:
        adapter = InputAdapter()
        pyxel = FakePyxel()
        initial_basis = StickBasis()
        inverted_basis = StickBasis(move_forward_x=-1.0)

        pyxel.pointer_press(196, 700)
        adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT, initial_basis)

        pyxel.pointer_hold(236, 700)
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT, initial_basis)
        self.assertEqual(intent.move_axis, 1.0)
        self.assertEqual(intent.lane_screen_step, 0)

        intent = adapter.read(pyxel, CameraShotId.FRONT_RIGHT_CLOSE, DT, inverted_basis)
        self.assertEqual(intent.move_axis, 1.0)
        self.assertEqual(intent.lane_screen_step, 0)
        self.assertAlmostEqual(adapter.pointer.drag_x, -40.0)
        self.assertAlmostEqual(adapter.pointer.drag_y, 0.0)

        pyxel.pointer_hold(220, 700)
        intent = adapter.read(pyxel, CameraShotId.FRONT_RIGHT_CLOSE, DT, inverted_basis)
        self.assertEqual(intent.move_axis, 1.0)

    def test_vertical_drag_waits_before_repeating_lane_step(self) -> None:
        adapter = InputAdapter()
        pyxel = FakePyxel()

        pyxel.pointer_press(196, 700)
        adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT)

        pyxel.pointer_hold(196, round(700 - STICK_LANE_STEP_PX))
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT)
        self.assertEqual(intent.lane_screen_step, 1)

        pyxel.pointer_hold(196, round(700 - STICK_LANE_STEP_PX * 2))
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT)
        self.assertEqual(intent.lane_screen_step, 0)

        repeated = 0
        frames = int(STICK_LANE_REPEAT_DELAY_SECONDS / DT) + 2
        for _ in range(frames):
            intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT)
            repeated = intent.lane_screen_step
            if repeated != 0:
                break

        self.assertEqual(repeated, 1)

    def test_camera_button_tap_still_requests_camera(self) -> None:
        adapter = InputAdapter()
        pyxel = FakePyxel()

        pyxel.pointer_press(60, 18)
        adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT)

        pyxel.pointer_release(60, 18)
        intent = adapter.read(pyxel, CameraShotId.REAR_RIGHT_LOW, DT)
        self.assertEqual(intent.requested_camera, CameraShotId.FRONT_RIGHT_CLOSE)
