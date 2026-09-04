from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from random import Random
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from three_line_explorer.drift_item_catalog import (  # noqa: E402
    DRIFT_ITEM_BY_ID,
    DRIFT_ITEM_IDS,
    DRIFT_ITEMS,
    DriftRarity,
    validate_catalog,
)
from three_line_explorer.drift_item_randomizer import (  # noqa: E402
    DriftSelectionPolicy,
    eligible_drift_items,
    select_drift_items,
)
from three_line_explorer.drift_item_sprites import (  # noqa: E402
    ATLAS_CAPACITY,
    ATLAS_PAGE_COUNT,
    CELL_H,
    CELL_W,
    SPRITE_ROWS,
    TRANSPARENT_COLOR,
    instantiate_pixel_map_sources,
    validate_all_sprites,
)
from three_line_explorer.inspection_content_registry import (  # noqa: E402
    AMBIENT_DRIFT_ITEMS,
    CONTENT_METADATA,
    InspectionContentKind,
    instantiate_all_inspection_texts,
    validate_content_registry,
)
from three_line_explorer.story_content import (  # noqa: E402
    MEMORY_ECHOES,
    OWNER_LETTERS,
    STORY_CONTENT,
    STORY_RESERVED_SPRITE_IDS,
    STORY_SEQUENCE_IDS,
    StoryContentKind,
    validate_story_content,
)
from three_line_explorer.story_progression import (  # noqa: E402
    StoryProgressState,
    activate_next_story_item_if_due,
    from_save_data,
    get_active_story_item,
    mark_story_item_read,
    record_ambient_inspection,
    to_save_data,
    validate_progress_state,
)


@dataclass(frozen=True)
class FakeInspectionText:
    title: str
    pages: tuple[str, ...]


@dataclass(frozen=True)
class FakePixelMapSource:
    width: int
    height: int
    rows: tuple[str, ...]
    transparent_color: int


class BaseCatalogTests(unittest.TestCase):
    def test_base_catalog_and_sprite_atlas_still_have_100_slots(self) -> None:
        validate_catalog()
        validate_all_sprites()
        self.assertEqual(len(DRIFT_ITEMS), 100)
        self.assertEqual(len(DRIFT_ITEM_BY_ID), 100)
        self.assertEqual(len(DRIFT_ITEM_IDS), 100)
        self.assertEqual(set(SPRITE_ROWS), set(DRIFT_ITEM_IDS))

    def test_ambient_descriptions_remain_compact(self) -> None:
        for item in DRIFT_ITEMS:
            self.assertLessEqual(len(item.body), 60, item.item_id)
            self.assertNotIn("\n", item.body)

    def test_sprite_contract(self) -> None:
        self.assertEqual(CELL_W, 32)
        self.assertEqual(CELL_H, 24)
        self.assertEqual(TRANSPARENT_COLOR, 8)
        allowed = set(".012345679abcdef")
        for sprite_id, rows in SPRITE_ROWS.items():
            self.assertEqual(len(rows), CELL_H, sprite_id)
            for row in rows:
                self.assertEqual(len(row), CELL_W, sprite_id)
                self.assertLessEqual(set(row), allowed, sprite_id)
                self.assertNotIn("8", row, sprite_id)

    def test_two_atlas_pages_cover_all_sprites(self) -> None:
        self.assertEqual(ATLAS_PAGE_COUNT, 2)
        self.assertGreaterEqual(
            ATLAS_PAGE_COUNT * ATLAS_CAPACITY,
            len(SPRITE_ROWS),
        )

    def test_pixel_map_adapter(self) -> None:
        maps = instantiate_pixel_map_sources(FakePixelMapSource)
        self.assertEqual(len(maps), 100)
        self.assertEqual(maps["water_pressure_gauge"].width, 32)
        self.assertEqual(maps["water_pressure_gauge"].height, 24)
        self.assertEqual(
            maps["water_pressure_gauge"].transparent_color,
            8,
        )


class StoryContentTests(unittest.TestCase):
    def test_story_content_counts_and_sequence(self) -> None:
        validate_story_content()
        self.assertEqual(len(OWNER_LETTERS), 8)
        self.assertEqual(len(MEMORY_ECHOES), 6)
        self.assertEqual(len(STORY_CONTENT), 14)
        self.assertEqual(len(STORY_RESERVED_SPRITE_IDS), 14)
        self.assertEqual(
            [item.sequence_index for item in STORY_CONTENT],
            list(range(14)),
        )

    def test_sequence_interleaves_memories_then_finishes_with_letters(self) -> None:
        expected_kinds = [
            StoryContentKind.OWNER_LETTER,
            StoryContentKind.MEMORY_ECHO,
            StoryContentKind.OWNER_LETTER,
            StoryContentKind.MEMORY_ECHO,
            StoryContentKind.OWNER_LETTER,
            StoryContentKind.MEMORY_ECHO,
            StoryContentKind.OWNER_LETTER,
            StoryContentKind.MEMORY_ECHO,
            StoryContentKind.OWNER_LETTER,
            StoryContentKind.MEMORY_ECHO,
            StoryContentKind.OWNER_LETTER,
            StoryContentKind.MEMORY_ECHO,
            StoryContentKind.OWNER_LETTER,
            StoryContentKind.OWNER_LETTER,
        ]
        self.assertEqual(
            [item.kind for item in STORY_CONTENT],
            expected_kinds,
        )

    def test_owner_letters_are_long_manual_pages_without_memory_episodes(self) -> None:
        forbidden = (
            "病院",
            "シャワー",
            "爪切り",
            "ガリガリの謎生物",
            "腹を見せ",
            "後ろ脚で蹴",
        )
        for letter in OWNER_LETTERS:
            self.assertGreaterEqual(len(letter.pages), 3, letter.content_id)
            self.assertLessEqual(len(letter.pages), 5, letter.content_id)
            joined = "".join(letter.pages)
            for phrase in forbidden:
                self.assertNotIn(phrase, joined, letter.content_id)

    def test_memory_echoes_hold_requested_episode_motifs(self) -> None:
        joined = "".join(
            page
            for memory in MEMORY_ECHOES
            for page in memory.pages
        )
        for phrase in (
            "白い壁",
            "水。泡。",
            "前脚一本",
            "寒い夜",
            "腹を見せる",
            "春は",
            "夏は",
            "秋は",
            "冬は",
        ):
            self.assertIn(phrase, joined)

    def test_story_sprite_bindings_exist_in_base_atlas(self) -> None:
        self.assertLessEqual(
            STORY_RESERVED_SPRITE_IDS,
            set(SPRITE_ROWS),
        )


class EffectiveRegistryTests(unittest.TestCase):
    def test_effective_registry_is_86_ambient_plus_14_story(self) -> None:
        validate_content_registry()
        self.assertEqual(len(AMBIENT_DRIFT_ITEMS), 86)
        self.assertEqual(len(CONTENT_METADATA), 100)
        self.assertEqual(
            sum(
                meta.kind is InspectionContentKind.AMBIENT
                for meta in CONTENT_METADATA.values()
            ),
            86,
        )
        self.assertEqual(
            sum(
                meta.kind is InspectionContentKind.OWNER_LETTER
                for meta in CONTENT_METADATA.values()
            ),
            8,
        )
        self.assertEqual(
            sum(
                meta.kind is InspectionContentKind.MEMORY_ECHO
                for meta in CONTENT_METADATA.values()
            ),
            6,
        )

    def test_text_adapter_returns_exactly_100_effective_entries(self) -> None:
        texts = instantiate_all_inspection_texts(FakeInspectionText)
        self.assertEqual(len(texts), 100)
        self.assertEqual(len(texts["owner_letter_08"].pages), 5)
        self.assertEqual(len(texts["memory_echo_05_belly_trap"].pages), 1)
        self.assertIn("帰る道", texts["owner_letter_08"].pages[-1])


class AmbientRandomizerTests(unittest.TestCase):
    def test_default_pool_excludes_fixed_story_sprite_slots(self) -> None:
        final = eligible_drift_items(area_index=17)
        ids = {item.item_id for item in final}
        self.assertEqual(len(ids), 86)
        self.assertTrue(STORY_RESERVED_SPRITE_IDS.isdisjoint(ids))

    def test_debug_policy_can_restore_all_100_base_catalog_items(self) -> None:
        policy = DriftSelectionPolicy(exclude_story_reserved=False)
        final = eligible_drift_items(area_index=17, policy=policy)
        self.assertEqual(len(final), 100)

    def test_selection_is_deterministic_and_has_no_duplicates(self) -> None:
        left = select_drift_items(
            rng=Random(7341), area_index=17, count=30
        )
        right = select_drift_items(
            rng=Random(7341), area_index=17, count=30
        )
        left_ids = [item.item_id for item in left]
        right_ids = [item.item_id for item in right]
        self.assertEqual(left_ids, right_ids)
        self.assertEqual(len(left_ids), len(set(left_ids)))

    def test_existing_batch_caps_still_hold(self) -> None:
        selected = select_drift_items(
            rng=Random(912), area_index=17, count=40
        )
        self.assertLessEqual(
            sum(item.rarity is DriftRarity.ECHO for item in selected),
            1,
        )
        self.assertLessEqual(
            sum(item.owner_handwriting for item in selected),
            1,
        )
        self.assertLessEqual(
            sum(item.clue_level == 3 for item in selected),
            1,
        )


class StoryProgressionTests(unittest.TestCase):
    def test_first_story_item_waits_for_area_and_ambient_spacing(self) -> None:
        state = StoryProgressState()
        self.assertIsNone(
            activate_next_story_item_if_due(state, area_index=1)
        )
        self.assertIsNone(
            activate_next_story_item_if_due(state, area_index=2)
        )
        record_ambient_inspection(state)
        item = activate_next_story_item_if_due(state, area_index=2)
        self.assertIsNotNone(item)
        self.assertEqual(item.content_id, "owner_letter_01")

    def test_unread_story_item_persists_and_blocks_later_beats(self) -> None:
        state = StoryProgressState(ambient_inspections_since_story=10)
        first = activate_next_story_item_if_due(state, area_index=17)
        again = activate_next_story_item_if_due(state, area_index=17)
        self.assertEqual(first, again)
        self.assertEqual(state.next_sequence_index, 0)
        self.assertEqual(state.active_content_id, "owner_letter_01")

    def test_reading_advances_exactly_one_step(self) -> None:
        state = StoryProgressState(ambient_inspections_since_story=10)
        first = activate_next_story_item_if_due(state, area_index=17)
        self.assertTrue(
            mark_story_item_read(state, content_id=first.content_id)
        )
        self.assertEqual(state.next_sequence_index, 1)
        self.assertIsNone(state.active_content_id)
        self.assertEqual(state.ambient_inspections_since_story, 0)
        self.assertFalse(
            mark_story_item_read(state, content_id=first.content_id)
        )

    def test_full_sequence_can_be_completed_in_order(self) -> None:
        state = StoryProgressState()
        for expected_id in STORY_SEQUENCE_IDS:
            # Moving beyond each item's max area guarantees availability.
            state.ambient_inspections_since_story = 99
            item = activate_next_story_item_if_due(
                state, area_index=17
            )
            self.assertEqual(item.content_id, expected_id)
            self.assertTrue(
                mark_story_item_read(state, content_id=expected_id)
            )
        self.assertTrue(state.is_complete)

    def test_save_round_trip(self) -> None:
        state = StoryProgressState(ambient_inspections_since_story=5)
        item = activate_next_story_item_if_due(state, area_index=17)
        self.assertIsNotNone(item)
        restored = from_save_data(to_save_data(state))
        validate_progress_state(restored)
        self.assertEqual(to_save_data(restored), to_save_data(state))
        self.assertEqual(
            get_active_story_item(restored).content_id,
            "owner_letter_01",
        )


if __name__ == "__main__":
    unittest.main()
