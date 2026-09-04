"""State and deterministic scheduling for riverside story drift items."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .story_content import (
    STORY_CONTENT,
    STORY_CONTENT_BY_ID,
    StoryInspectionDefinition,
)


@dataclass(slots=True)
class StoryProgressState:
    """Minimal save-state for the fixed drift narrative."""

    next_sequence_index: int = 0
    active_content_id: str | None = None
    completed_ids: set[str] = field(default_factory=set)
    ambient_inspections_since_story: int = 0

    @property
    def is_complete(self) -> bool:
        return self.next_sequence_index >= len(STORY_CONTENT)


def get_active_story_item(
    state: StoryProgressState,
) -> StoryInspectionDefinition | None:
    if state.active_content_id is None:
        return None
    return STORY_CONTENT_BY_ID[state.active_content_id]


def get_next_story_item(
    state: StoryProgressState,
) -> StoryInspectionDefinition | None:
    if state.is_complete:
        return None
    return STORY_CONTENT[state.next_sequence_index]


def record_ambient_inspection(
    state: StoryProgressState,
) -> None:
    """Count player-read ambient items between fixed story beats."""

    if state.active_content_id is None and not state.is_complete:
        state.ambient_inspections_since_story += 1


def is_next_story_item_due(
    state: StoryProgressState,
    *,
    area_index: int,
) -> bool:
    if not 0 <= area_index <= 17:
        raise ValueError("area_index must be between 0 (A) and 17 (R)")

    if state.active_content_id is not None or state.is_complete:
        return False

    item = STORY_CONTENT[state.next_sequence_index]

    if area_index < item.min_area_index:
        return False

    # Crossing the end of the intended band guarantees the beat, even when
    # the ambient counter has not reached its preferred spacing.
    if area_index > item.max_area_index:
        return True

    return (
        state.ambient_inspections_since_story
        >= item.min_ambient_inspections_before
    )


def activate_next_story_item_if_due(
    state: StoryProgressState,
    *,
    area_index: int,
) -> StoryInspectionDefinition | None:
    """Reserve the next fixed story item until the player reads it.

    Calling this repeatedly returns the already active item instead of spawning
    duplicates. The caller may choose a random world slot inside the item's area
    band, but must not replace the logical content until it is read.
    """

    active = get_active_story_item(state)
    if active is not None:
        return active

    if not is_next_story_item_due(state, area_index=area_index):
        return None

    item = STORY_CONTENT[state.next_sequence_index]
    state.active_content_id = item.content_id
    return item


def mark_story_item_read(
    state: StoryProgressState,
    *,
    content_id: str,
) -> bool:
    """Advance only when the currently active item is actually inspected."""

    if state.active_content_id != content_id:
        return False

    expected = STORY_CONTENT[state.next_sequence_index]
    if expected.content_id != content_id:
        raise ValueError(
            "Story state is inconsistent: active item is not the next beat"
        )

    state.completed_ids.add(content_id)
    state.active_content_id = None
    state.next_sequence_index += 1
    state.ambient_inspections_since_story = 0
    return True


def to_save_data(state: StoryProgressState) -> dict[str, Any]:
    return {
        "next_sequence_index": state.next_sequence_index,
        "active_content_id": state.active_content_id,
        "completed_ids": sorted(state.completed_ids),
        "ambient_inspections_since_story": (
            state.ambient_inspections_since_story
        ),
    }


def from_save_data(data: dict[str, Any]) -> StoryProgressState:
    state = StoryProgressState(
        next_sequence_index=int(data.get("next_sequence_index", 0)),
        active_content_id=data.get("active_content_id"),
        completed_ids=set(data.get("completed_ids", ())),
        ambient_inspections_since_story=int(
            data.get("ambient_inspections_since_story", 0)
        ),
    )
    validate_progress_state(state)
    return state


def validate_progress_state(state: StoryProgressState) -> None:
    if not 0 <= state.next_sequence_index <= len(STORY_CONTENT):
        raise ValueError("next_sequence_index is out of range")

    valid_ids = set(STORY_CONTENT_BY_ID)
    if not state.completed_ids <= valid_ids:
        raise ValueError("completed_ids contains unknown story content")

    expected_completed = {
        item.content_id
        for item in STORY_CONTENT[: state.next_sequence_index]
    }
    if state.completed_ids != expected_completed:
        raise ValueError(
            "completed_ids must exactly match the completed sequence prefix"
        )

    if state.ambient_inspections_since_story < 0:
        raise ValueError("ambient inspection count must not be negative")

    if state.active_content_id is not None:
        if state.is_complete:
            raise ValueError("completed story cannot have an active item")
        expected = STORY_CONTENT[state.next_sequence_index].content_id
        if state.active_content_id != expected:
            raise ValueError("active_content_id must be the next story beat")
