from __future__ import annotations

from unittest import TestCase

from three_line_explorer.camera import CAMERA_SHOTS, make_camera_snapshot
from three_line_explorer.config import CameraShotId
from three_line_explorer.generated_environment_assets import PARALLAX_SEQUENCES, ParallaxLayer
from three_line_explorer.parallax import (
    _projected_world_x_span_for_viewport,
    build_parallax_atlas,
    draw_parallax_background,
    far_stage_edge_z,
    farther_z_direction,
)
from three_line_explorer.visible_volume import update_visible_volume


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

    def test_atlas_contains_full_sequence_regions_for_each_layer(self) -> None:
        atlas = build_parallax_atlas(FakePyxel())

        self.assertEqual(set(atlas.sequence_regions), set(ParallaxLayer))
        for layer, sequence in PARALLAX_SEQUENCES.items():
            region = atlas.sequence_regions[layer]
            tile_width = atlas.regions[sequence[0]].width
            self.assertEqual(region.width, tile_width * len(sequence))
            self.assertGreater(region.width, tile_width)

    def test_far_edge_flips_by_camera_side(self) -> None:
        visible = update_visible_volume(0.0)
        shot_a = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], 0.0, 0.0)
        shot_c = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_LEFT_SHALLOW], 0.0, 0.0)

        self.assertEqual(far_stage_edge_z(shot_a, visible.bounds), visible.bounds.minimum.z)
        self.assertEqual(far_stage_edge_z(shot_c, visible.bounds), visible.bounds.maximum.z)
        self.assertEqual(farther_z_direction(shot_a), -1.0)
        self.assertEqual(farther_z_direction(shot_c), 1.0)

    def test_draw_parallax_emits_tiles_for_each_layer(self) -> None:
        pyxel = FakePyxel()
        atlas = build_parallax_atlas(pyxel)
        snapshot = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], 40.0, 0.0)
        visible = update_visible_volume(40.0)

        draw_parallax_background(pyxel, atlas, snapshot, player_x=40.0, visible_bounds=visible.bounds)

        asset_id_by_uv = {
            (region.u, region.v): asset_id
            for asset_id, region in atlas.regions.items()
        }
        drawn_layers = {
            _layer_for_region(asset_id_by_uv[(call.u, call.v)])
            for call in pyxel.blt_calls
        }
        self.assertEqual(drawn_layers, set(ParallaxLayer))
        for call in pyxel.blt_calls:
            self.assertEqual(call.width, 256)

    def test_projected_world_span_recalculates_from_camera(self) -> None:
        visible = update_visible_volume(0.0)
        shot_a = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], 0.0, 0.0)
        shot_c = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_LEFT_SHALLOW], 0.0, 0.0)

        edge_a = far_stage_edge_z(shot_a, visible.bounds)
        edge_c = far_stage_edge_z(shot_c, visible.bounds)
        span_a = _projected_world_x_span_for_viewport(shot_a, edge_a, visible.bounds)
        span_c = _projected_world_x_span_for_viewport(shot_c, edge_c, visible.bounds)

        self.assertLess(span_a[0], visible.bounds.minimum.x)
        self.assertGreater(span_a[1], visible.bounds.maximum.x)
        self.assertLess(span_c[0], visible.bounds.minimum.x)
        self.assertGreater(span_c[1], visible.bounds.maximum.x)
        self.assertNotEqual(span_a, span_c)

    def test_parallax_strip_scale_comes_from_projected_edges(self) -> None:
        pyxel = FakePyxel()
        atlas = build_parallax_atlas(pyxel)
        visible = update_visible_volume(0.0)
        shot_a = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], 0.0, 0.0)
        shot_c = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_LEFT_SHALLOW], 0.0, 0.0)

        draw_parallax_background(pyxel, atlas, shot_a, player_x=0.0, visible_bounds=visible.bounds)
        scales_a = [call.scale for call in pyxel.blt_calls]
        pyxel.blt_calls.clear()
        draw_parallax_background(pyxel, atlas, shot_c, player_x=0.0, visible_bounds=visible.bounds)
        scales_c = [call.scale for call in pyxel.blt_calls]

        self.assertNotEqual(scales_a, scales_c)
        self.assertTrue(all(scale > 0.0 for scale in scales_a))
        self.assertTrue(all(scale > 0.0 for scale in scales_c))


def _layer_for_region(asset_id: str) -> ParallaxLayer:
    for layer, sequence in PARALLAX_SEQUENCES.items():
        if asset_id in sequence:
            return layer
    raise AssertionError(f"missing parallax asset id: {asset_id}")


class BltCall:
    def __init__(self, u: int, v: int, width: int, scale: float) -> None:
        self.u = u
        self.v = v
        self.width = width
        self.scale = scale


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
        width: int,
        _height: int,
        _colkey: int | None,
        *,
        scale: float = 1.0,
    ) -> None:
        self.blt_calls.append(BltCall(u, v, width, scale))
