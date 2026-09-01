from __future__ import annotations

from unittest import TestCase

from three_line_explorer.camera import CAMERA_SHOTS, make_camera_snapshot
from three_line_explorer.config import (
    CameraShotId,
    INSPECTION_BODY_FONT_SIZE,
    INSPECTION_FONT_PATH,
    INSPECTION_TEXT_MAX_LINES,
    INSPECTION_TEXT_MAX_WIDTH,
    LANE_Z,
    RIVER_START_Z,
)
from three_line_explorer.inspection import (
    InspectableProp,
    InteractionState,
    advance_or_close_inspection,
    current_page,
    marker_world_position,
    open_inspection,
    prompt_snapshot_for_prop,
    prop_sprite_anchor,
    update_active_target,
)
from three_line_explorer.inspection_prop_sprites import PropSpriteId
from three_line_explorer.inspection_texts import INSPECTION_TEXTS, InspectionText
from three_line_explorer.math3d import AABB, Vec3
from three_line_explorer.player import player_bounds_at
from three_line_explorer.stage import Stage
from three_line_explorer.text_layout import (
    InspectionTextLayoutCache,
    create_text_measure,
    estimate_text_width,
    prepare_inspection_text,
    wrap_japanese_text,
)
from three_line_explorer.ui_fonts import asset_path_candidates, load_ui_fonts
from three_line_explorer.visible_volume import update_visible_volume


class InspectionTests(TestCase):
    def test_river_side_lane_can_acquire_prop_but_center_lane_cannot(self) -> None:
        stage = Stage.create_prototype()
        state = InteractionState()

        update_active_target(
            state,
            player_bounds_at(78.0, LANE_Z[1]),
            stage.inspectable_props,
        )
        self.assertIsNone(state.active_target_id)

        update_active_target(
            state,
            player_bounds_at(78.0, LANE_Z[2]),
            stage.inspectable_props,
        )
        self.assertEqual(state.active_target_id, "river_prop_001")

    def test_active_prop_uses_release_padding_as_hysteresis(self) -> None:
        stage = Stage.create_prototype()
        state = InteractionState(active_target_id="river_prop_001")

        update_active_target(
            state,
            player_bounds_at(78.0, 22.0),
            stage.inspectable_props,
        )
        self.assertEqual(state.active_target_id, "river_prop_001")

        update_active_target(
            state,
            player_bounds_at(78.0, 20.0),
            stage.inspectable_props,
        )
        self.assertIsNone(state.active_target_id)

    def test_nearest_target_ties_are_stable_by_object_id(self) -> None:
        props = (
            InspectableProp(
                object_id="b_prop",
                render_object_id=100,
                bounds=AABB(Vec3(40.0, 0.0, 48.0), Vec3(48.0, 4.0, 56.0)),
                text_key="single_sandal",
                sprite_id=PropSpriteId.SINGLE_SANDAL,
            ),
            InspectableProp(
                object_id="a_prop",
                render_object_id=101,
                bounds=AABB(Vec3(40.0, 0.0, 48.0), Vec3(48.0, 4.0, 56.0)),
                text_key="single_sandal",
                sprite_id=PropSpriteId.SINGLE_SANDAL,
            ),
        )
        state = InteractionState()

        update_active_target(state, player_bounds_at(42.0, LANE_Z[2]), props)

        self.assertEqual(state.active_target_id, "a_prop")

    def test_marker_uses_top_center_plus_height(self) -> None:
        prop = Stage.create_prototype().inspectable_props[0]

        marker = marker_world_position(prop)

        self.assertEqual(marker.x, 81.0)
        self.assertEqual(marker.y, 12.0)
        self.assertEqual(marker.z, RIVER_START_Z + 9.5)

    def test_prop_sprite_anchor_uses_ground_center(self) -> None:
        prop = Stage.create_prototype().inspectable_props[0]

        anchor = prop_sprite_anchor(prop)

        self.assertEqual(anchor.x, 81.0)
        self.assertEqual(anchor.y, 0.25)
        self.assertEqual(anchor.z, RIVER_START_Z + 9.5)

    def test_prompt_snapshot_projects_active_prop_to_hitbox(self) -> None:
        prop = Stage.create_prototype().inspectable_props[0]
        snapshot = make_camera_snapshot(
            CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW],
            78.0,
            LANE_Z[2],
        )
        volume = update_visible_volume(78.0)

        prompt = prompt_snapshot_for_prop(prop, snapshot, volume.bounds)

        self.assertIsNotNone(prompt)
        assert prompt is not None
        self.assertTrue(prompt.visible)
        self.assertTrue(
            prompt.hitbox.contains(
                prompt.hitbox.x + prompt.hitbox.width // 2,
                prompt.hitbox.y + prompt.hitbox.height // 2,
            )
        )

    def test_panel_opens_advances_and_closes(self) -> None:
        prop = Stage.create_prototype().inspectable_props[0]
        state = InteractionState()
        text_cache = make_text_cache()

        self.assertTrue(open_inspection(state, prop, text_cache))
        self.assertTrue(state.panel_open)
        self.assertIn(prop.object_id, state.inspected_ids)
        page = current_page(state)
        self.assertIsNotNone(page)
        assert page is not None
        self.assertEqual(state.prepared_text.title, "片方だけのサンダル")

        advance_or_close_inspection(state)
        self.assertTrue(state.panel_open)
        self.assertEqual(state.page_index, 1)

        advance_or_close_inspection(state)
        self.assertFalse(state.panel_open)

    def test_japanese_wrap_uses_font_measure(self) -> None:
        measure = create_text_measure(FakeFont(width_per_char=12), 16)

        lines = wrap_japanese_text(
            "水を吸って、すっかり重くなっている。",
            72,
            measure,
        )

        self.assertGreater(len(lines), 1)
        self.assertTrue(all(measure(line) <= 84 for line in lines))

    def test_text_measure_uses_font_text_width_when_available(self) -> None:
        font = FakeFont(width_per_char=12)

        measure = create_text_measure(font, 16)

        self.assertEqual(measure("abc"), 36)

    def test_text_measure_estimates_width_without_font_text_width(self) -> None:
        measure = create_text_measure(object(), 16)

        self.assertEqual(measure("abc"), 24)
        self.assertEqual(measure("川辺"), 32)

    def test_wrap_keeps_no_line_start_marks_off_line_head(self) -> None:
        measure = create_text_measure(FakeFont(width_per_char=10), 16)

        lines = wrap_japanese_text("あああ。いい", 30, measure)

        self.assertEqual(lines[0], "ああ")
        self.assertTrue(lines[1].startswith("あ。"))

    def test_wrap_keeps_no_line_end_marks_off_line_tail(self) -> None:
        measure = create_text_measure(FakeFont(width_per_char=10), 16)

        lines = wrap_japanese_text("ああ「いい", 30, measure)

        self.assertEqual(lines[0], "ああ")
        self.assertTrue(lines[1].startswith("「い"))

    def test_prepare_splits_pages_after_max_lines(self) -> None:
        source = InspectionText(
            "長い文章",
            ("あ\nい\nう\nえ\nお\nか\nき",),
        )

        prepared = prepare_inspection_text(
            source,
            max_width=999,
            max_lines=INSPECTION_TEXT_MAX_LINES,
            measure=lambda text: len(text),
        )

        self.assertEqual(len(prepared.pages), 2)
        self.assertEqual(len(prepared.pages[0].lines), INSPECTION_TEXT_MAX_LINES)
        self.assertEqual(prepared.pages[1].lines, ("き",))

    def test_text_layout_cache_reuses_prepared_text(self) -> None:
        counter = CountingMeasure()
        cache = InspectionTextLayoutCache(
            {"sample": InspectionText("見出し", ("川辺のメモ",))},
            max_width=INSPECTION_TEXT_MAX_WIDTH,
            max_lines=INSPECTION_TEXT_MAX_LINES,
            measure=counter,
        )

        first = cache.get("sample")
        calls_after_first = counter.calls
        second = cache.get("sample")

        self.assertIs(first, second)
        self.assertEqual(counter.calls, calls_after_first)

    def test_text_layout_cache_returns_none_for_missing_key(self) -> None:
        cache = make_text_cache()

        self.assertIsNone(cache.get("missing_text_key"))

    def test_font_candidates_include_pyxapp_package_path(self) -> None:
        candidates = asset_path_candidates(INSPECTION_FONT_PATH)

        self.assertEqual(candidates[0], INSPECTION_FONT_PATH)
        self.assertIn(f"riverside/{INSPECTION_FONT_PATH}", candidates)

    def test_font_loader_tries_pyxapp_package_path(self) -> None:
        success_path = f"riverside/{INSPECTION_FONT_PATH}"
        pyxel = FakePyxelFontLoader(success_path)

        fonts = load_ui_fonts(pyxel)

        self.assertEqual(fonts.title, ("font", success_path, 18))
        self.assertEqual(fonts.body, ("font", success_path, 16))
        self.assertIn((INSPECTION_FONT_PATH, 18), pyxel.calls)
        self.assertIn((success_path, 18), pyxel.calls)


class FakeFont:
    def __init__(self, *, width_per_char: int) -> None:
        self.width_per_char = width_per_char

    def text_width(self, text: str) -> int:
        return len(text) * self.width_per_char


class CountingMeasure:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, text: str) -> int:
        self.calls += 1
        return estimate_text_width(text, INSPECTION_BODY_FONT_SIZE)


class FakePyxelFontLoader:
    def __init__(self, success_path: str) -> None:
        self.success_path = success_path
        self.calls: list[tuple[str, int]] = []

    def Font(self, path: str, size: int) -> tuple[str, str, int]:
        self.calls.append((path, size))
        if path == self.success_path:
            return ("font", path, size)
        raise FileNotFoundError(path)


def make_text_cache() -> InspectionTextLayoutCache:
    return InspectionTextLayoutCache(
        INSPECTION_TEXTS,
        INSPECTION_TEXT_MAX_WIDTH,
        INSPECTION_TEXT_MAX_LINES,
        create_text_measure(FakeFont(width_per_char=12), INSPECTION_BODY_FONT_SIZE),
    )
