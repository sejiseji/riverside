from __future__ import annotations

from dataclasses import dataclass
import unittest

from three_line_explorer.owner_memory_bubble_sprites import (
    ANCHOR_X,
    ANCHOR_Y,
    ANIMATION_SEQUENCE,
    ATLAS_H,
    ATLAS_W,
    FRAME_COUNT,
    FRAME_H,
    FRAME_W,
    OWNER_MEMORY_FRAMES,
    TRANSPARENT_COLOR,
    animation_frame_index,
    build_owner_memory_bubble_atlas,
    instantiate_pixel_map_sources,
    validate_owner_memory_frames,
)


@dataclass(frozen=True)
class FakePixelMapSource:
    width: int
    height: int
    rows: tuple[str, ...]
    transparent_color: int


class OwnerMemoryBubbleSpriteTests(unittest.TestCase):
    def test_all_frames_are_valid(self) -> None:
        validate_owner_memory_frames()

    def test_sheet_geometry(self) -> None:
        self.assertEqual(FRAME_COUNT, 4)
        self.assertEqual((FRAME_W, FRAME_H), (64, 64))
        self.assertEqual((ATLAS_W, ATLAS_H), (256, 64))

    def test_reserved_transparent_digit_is_not_visible(self) -> None:
        reserved = f"{TRANSPARENT_COLOR:x}"

        for frame in OWNER_MEMORY_FRAMES:
            self.assertTrue(any("." in row for row in frame))
            self.assertTrue(all(reserved not in row for row in frame))

    def test_expected_character_colors_exist(self) -> None:
        joined = "".join(
            row
            for frame in OWNER_MEMORY_FRAMES
            for row in frame
        )

        for required in ("0", "1", "3", "4", "6", "7", "d", "e", "f"):
            self.assertIn(required, joined)

    def test_animation_sequence_is_valid(self) -> None:
        self.assertEqual(ANIMATION_SEQUENCE, (0, 1, 2, 3, 2, 1))
        self.assertTrue(
            all(0 <= frame < FRAME_COUNT for frame in ANIMATION_SEQUENCE)
        )

    def test_animation_frame_uses_panel_local_time(self) -> None:
        self.assertEqual(animation_frame_index(0), 0)
        self.assertEqual(animation_frame_index(8), 1)
        self.assertEqual(animation_frame_index(16), 2)
        self.assertEqual(animation_frame_index(24), 3)
        self.assertEqual(animation_frame_index(32), 2)
        self.assertEqual(animation_frame_index(40), 1)
        self.assertEqual(animation_frame_index(48), 0)

    def test_animation_rejects_invalid_time(self) -> None:
        with self.assertRaises(ValueError):
            animation_frame_index(-1)

        with self.assertRaises(ValueError):
            animation_frame_index(0, frame_hold=0)

    def test_pixel_map_source_adapter(self) -> None:
        sources = instantiate_pixel_map_sources(FakePixelMapSource)

        self.assertEqual(len(sources), FRAME_COUNT)

        for source in sources.values():
            self.assertEqual(source.width, FRAME_W)
            self.assertEqual(source.height, FRAME_H)
            self.assertEqual(source.transparent_color, TRANSPARENT_COLOR)

    def test_anchor_is_inside_frame(self) -> None:
        self.assertTrue(0 <= ANCHOR_X < FRAME_W)
        self.assertTrue(0 <= ANCHOR_Y < FRAME_H)

    def test_build_atlas_writes_all_frames_once(self) -> None:
        pyxel = FakePyxel()

        atlas = build_owner_memory_bubble_atlas(pyxel)

        self.assertIs(atlas.image, pyxel.image)
        self.assertEqual(pyxel.image.size, (ATLAS_W, ATLAS_H))
        self.assertEqual(pyxel.image.clear_color, TRANSPARENT_COLOR)
        self.assertEqual(len(pyxel.image.set_calls), FRAME_COUNT)
        self.assertEqual(
            [call[0] for call in pyxel.image.set_calls],
            [index * FRAME_W for index in range(FRAME_COUNT)],
        )


class FakeImage:
    def __init__(self, width: int, height: int) -> None:
        self.size = (width, height)
        self.clear_color: int | None = None
        self.set_calls: list[tuple[int, int, list[str]]] = []

    def cls(self, color: int) -> None:
        self.clear_color = color

    def set(self, x: int, y: int, rows: list[str]) -> None:
        self.set_calls.append((x, y, rows))


class FakePyxel:
    def Image(self, width: int, height: int) -> FakeImage:
        self.image = FakeImage(width, height)
        return self.image


if __name__ == "__main__":
    unittest.main()
