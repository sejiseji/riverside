from __future__ import annotations

from math import pi
from unittest import TestCase

import three_line_explorer.player_sprite as player_sprite_module
from three_line_explorer.player import create_player
from three_line_explorer.player_sprite import (
    PLAYER_SPRITE_RESOURCE_PATH,
    SPRITE_ROW_BACK,
    SPRITE_ROW_FRONT,
    SPRITE_ROW_LEFT,
    SPRITE_ROW_RIGHT,
    load_player_sprite_sheet,
    player_sprite_is_moving,
    player_sprite_row,
    player_sprite_source,
)
from three_line_explorer.player_sprite_data import (
    PLAYER_SPRITE_ANIMATION_FRAMES,
    PLAYER_SPRITE_COLUMNS,
    PLAYER_SPRITE_FRAME_H,
    PLAYER_SPRITE_FRAME_W,
    PLAYER_SPRITE_FRAMES_PER_BANK,
    PLAYER_SPRITE_IMAGE_BANKS,
    PLAYER_SPRITE_ROWS,
    PLAYER_SPRITE_SHEETS,
    PLAYER_SPRITE_TRANSPARENT_COLOR,
)


class FakeImage:
    def __init__(self) -> None:
        self.set_calls: list[tuple[int, int, list[str]]] = []

    def set(self, x: int, y: int, rows: list[str]) -> None:
        self.set_calls.append((x, y, rows))


class FakePyxel:
    def __init__(self, *, load_succeeds: bool) -> None:
        self.load_succeeds = load_succeeds
        self.load_calls: list[tuple[str, dict]] = []
        self.fake_image = FakeImage()

    def load(self, filename: str, **kwargs: object) -> None:
        self.load_calls.append((filename, kwargs))
        if not self.load_succeeds:
            raise FileNotFoundError(filename)

    def image(self, bank: int) -> FakeImage:
        self.loaded_bank = bank
        return self.fake_image


class PlayerSpriteTests(TestCase):
    def tearDown(self) -> None:
        player_sprite_module._loaded = False

    def test_sprite_sheet_dimensions_match_pyxel_bank_layout(self) -> None:
        self.assertEqual(len(PLAYER_SPRITE_SHEETS), len(PLAYER_SPRITE_IMAGE_BANKS))
        self.assertEqual(PLAYER_SPRITE_COLUMNS * PLAYER_SPRITE_ROWS, 16)
        self.assertEqual(PLAYER_SPRITE_ANIMATION_FRAMES, 4)
        self.assertEqual(PLAYER_SPRITE_IMAGE_BANKS, (0,))
        for sheet in PLAYER_SPRITE_SHEETS:
            self.assertEqual(len(sheet), PLAYER_SPRITE_FRAME_H * 4)
            self.assertTrue(
                all(
                    len(row) == PLAYER_SPRITE_FRAME_W * PLAYER_SPRITE_FRAMES_PER_BANK
                    for row in sheet
                )
            )
        self.assertIn(format(PLAYER_SPRITE_TRANSPARENT_COLOR, "x"), PLAYER_SPRITE_SHEETS[0][0])

    def test_render_yaw_selects_cardinal_sprite_rows(self) -> None:
        self.assertEqual(player_sprite_row(0.0), SPRITE_ROW_RIGHT)
        self.assertEqual(player_sprite_row(pi), SPRITE_ROW_LEFT)
        self.assertEqual(player_sprite_row(-pi * 0.5), SPRITE_ROW_FRONT)
        self.assertEqual(player_sprite_row(pi * 0.5), SPRITE_ROW_BACK)

    def test_load_prefers_pyxres_resource(self) -> None:
        pyxel = FakePyxel(load_succeeds=True)

        load_player_sprite_sheet(pyxel)

        self.assertEqual(pyxel.load_calls[0][0], PLAYER_SPRITE_RESOURCE_PATH)
        self.assertEqual(pyxel.fake_image.set_calls, [])

    def test_load_falls_back_to_embedded_sprite_data(self) -> None:
        pyxel = FakePyxel(load_succeeds=False)

        load_player_sprite_sheet(pyxel)

        self.assertEqual(pyxel.load_calls[0][0], PLAYER_SPRITE_RESOURCE_PATH)
        self.assertEqual(len(pyxel.fake_image.set_calls), 1)
        self.assertEqual(pyxel.fake_image.set_calls[0][2], list(PLAYER_SPRITE_SHEETS[0]))

    def test_idle_and_moving_source_frames(self) -> None:
        player = create_player()
        self.assertFalse(player_sprite_is_moving(player))
        image_bank, u, *_ = player_sprite_source(player, 99)
        self.assertEqual(image_bank, PLAYER_SPRITE_IMAGE_BANKS[0])
        self.assertEqual(u, 0)

        player.velocity_x = 1.0
        self.assertTrue(player_sprite_is_moving(player))
        image_bank, u, *_ = player_sprite_source(player, 5)
        self.assertEqual(image_bank, PLAYER_SPRITE_IMAGE_BANKS[0])
        self.assertEqual(u, PLAYER_SPRITE_FRAME_W)

        image_bank, u, *_ = player_sprite_source(player, 15)
        self.assertEqual(image_bank, PLAYER_SPRITE_IMAGE_BANKS[0])
        self.assertEqual(u, PLAYER_SPRITE_FRAME_W * 3)

        image_bank, u, *_ = player_sprite_source(player, 20)
        self.assertEqual(image_bank, PLAYER_SPRITE_IMAGE_BANKS[0])
        self.assertEqual(u, 0)
