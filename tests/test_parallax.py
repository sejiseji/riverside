from __future__ import annotations

from math import tan
from unittest import TestCase

from three_line_explorer.camera import CAMERA_SHOTS, make_camera_snapshot
from three_line_explorer.config import CameraShotId
from three_line_explorer.generated_environment_assets import PARALLAX_SEQUENCES, ParallaxLayer
from three_line_explorer.parallax import (
    build_parallax_atlas,
    draw_parallax_background,
    horizon_screen_y,
)


class ParallaxTests(TestCase):
    def test_atlas_contains_all_parallax_sequence_tiles(self) -> None:
        atlas = build_parallax_atlas(FakePyxel())
        expected = {
            asset_id
            for sequence in PARALLAX_SEQUENCES.values()
            for asset_id in sequence
        }

        self.assertEqual(set(atlas.regions), expected)
        self.assertEqual(len(atlas.image.set_calls), len(expected))

    def test_horizon_uses_interpolated_camera_elevation(self) -> None:
        snapshot = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], 0.0, 0.0)

        self.assertAlmostEqual(
            horizon_screen_y(snapshot),
            snapshot.screen_center_y - snapshot.focal_px * tan(snapshot.params.elevation),
        )

    def test_draw_parallax_emits_tiles_for_each_layer(self) -> None:
        pyxel = FakePyxel()
        atlas = build_parallax_atlas(pyxel)
        snapshot = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], 40.0, 0.0)

        draw_parallax_background(pyxel, atlas, snapshot, player_x=40.0)

        asset_id_by_uv = {
            (region.u, region.v): asset_id
            for asset_id, region in atlas.regions.items()
        }
        drawn_layers = {
            _layer_for_region(asset_id_by_uv[(call.u, call.v)])
            for call in pyxel.blt_calls
        }
        self.assertEqual(drawn_layers, set(ParallaxLayer))


def _layer_for_region(asset_id: str) -> ParallaxLayer:
    for layer, sequence in PARALLAX_SEQUENCES.items():
        if asset_id in sequence:
            return layer
    raise AssertionError(f"missing parallax asset id: {asset_id}")


class BltCall:
    def __init__(self, u: int, v: int) -> None:
        self.u = u
        self.v = v


class FakeImage:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.set_calls: list[tuple[int, int, tuple[str, ...]]] = []

    def cls(self, _color: int) -> None:
        pass

    def set(self, x: int, y: int, rows: list[str]) -> None:
        self.set_calls.append((x, y, tuple(rows)))


class FakePyxel:
    Image = FakeImage

    def __init__(self) -> None:
        self.blt_calls: list[BltCall] = []
        self.rect_calls: list[tuple[int, int, int, int, int]] = []

    def rect(self, x: int, y: int, width: int, height: int, color: int) -> None:
        self.rect_calls.append((x, y, width, height, color))

    def blt(
        self,
        _x: int,
        _y: int,
        _image: FakeImage,
        u: int,
        v: int,
        _width: int,
        _height: int,
        _colkey: int | None,
    ) -> None:
        self.blt_calls.append(BltCall(u, v))
