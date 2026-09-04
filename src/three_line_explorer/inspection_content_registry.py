"""Unified content registry for ambient items and fixed story beats."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final, TypeVar

from .drift_item_catalog import DRIFT_ITEMS, DriftItemDefinition
from .story_content import (
    STORY_CONTENT,
    STORY_CONTENT_BY_ID,
    STORY_RESERVED_SPRITE_IDS,
    StoryContentKind,
    StoryInspectionDefinition,
)


class InspectionContentKind(str, Enum):
    AMBIENT = "ambient"
    MEMORY_ECHO = "memory_echo"
    OWNER_LETTER = "owner_letter"


@dataclass(frozen=True, slots=True)
class InspectionContentMetadata:
    text_key: str
    sprite_id: str
    title: str
    kind: InspectionContentKind
    sequence_index: int | None
    persistent_until_read: bool
    archive_key: str | None


AMBIENT_DRIFT_ITEMS: Final[tuple[DriftItemDefinition, ...]] = tuple(
    item
    for item in DRIFT_ITEMS
    if item.item_id not in STORY_RESERVED_SPRITE_IDS
)

AMBIENT_DRIFT_ITEM_BY_ID: Final[dict[str, DriftItemDefinition]] = {
    item.item_id: item for item in AMBIENT_DRIFT_ITEMS
}


InspectionTextT = TypeVar("InspectionTextT")


def instantiate_all_inspection_texts(
    inspection_text_type: type[InspectionTextT],
) -> dict[str, InspectionTextT]:
    """Build the effective 100-entry text registry.

    The 14 reserved ambient catalog texts are replaced by 14 fixed story texts,
    preserving the original 100 sprite slots and total content count.
    """

    result = {
        item.text_key: inspection_text_type(
            title=item.title,
            pages=(item.body,),
        )
        for item in AMBIENT_DRIFT_ITEMS
    }

    result.update(
        {
            item.text_key: inspection_text_type(
                title=item.title,
                pages=item.pages,
            )
            for item in STORY_CONTENT
        }
    )

    return result


def build_content_metadata() -> dict[str, InspectionContentMetadata]:
    result: dict[str, InspectionContentMetadata] = {
        item.text_key: InspectionContentMetadata(
            text_key=item.text_key,
            sprite_id=item.sprite_id,
            title=item.title,
            kind=InspectionContentKind.AMBIENT,
            sequence_index=None,
            persistent_until_read=False,
            archive_key=None,
        )
        for item in AMBIENT_DRIFT_ITEMS
    }

    for item in STORY_CONTENT:
        kind = (
            InspectionContentKind.OWNER_LETTER
            if item.kind is StoryContentKind.OWNER_LETTER
            else InspectionContentKind.MEMORY_ECHO
        )
        result[item.text_key] = InspectionContentMetadata(
            text_key=item.text_key,
            sprite_id=item.sprite_id,
            title=item.title,
            kind=kind,
            sequence_index=item.sequence_index,
            persistent_until_read=item.persistent_until_read,
            archive_key=item.archive_key,
        )

    return result


CONTENT_METADATA: Final[dict[str, InspectionContentMetadata]] = (
    build_content_metadata()
)


def validate_content_registry() -> None:
    if len(DRIFT_ITEMS) != 100:
        raise ValueError("Base sprite catalog must still contain 100 entries")

    if len(STORY_RESERVED_SPRITE_IDS) != 14:
        raise ValueError("Expected 14 reserved sprite slots")

    if len(AMBIENT_DRIFT_ITEMS) != 86:
        raise ValueError(
            f"Expected 86 ambient items, got {len(AMBIENT_DRIFT_ITEMS)}"
        )

    if len(CONTENT_METADATA) != 100:
        raise ValueError(
            f"Effective registry must contain 100 entries, got "
            f"{len(CONTENT_METADATA)}"
        )

    base_sprite_ids = {item.item_id for item in DRIFT_ITEMS}
    if not STORY_RESERVED_SPRITE_IDS <= base_sprite_ids:
        missing = sorted(STORY_RESERVED_SPRITE_IDS - base_sprite_ids)
        raise ValueError(f"Story sprite binding missing from atlas: {missing}")

    if set(STORY_CONTENT_BY_ID) & set(AMBIENT_DRIFT_ITEM_BY_ID):
        raise ValueError("Story text keys collide with ambient item ids")


validate_content_registry()
