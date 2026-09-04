"""Deterministic weighted selection for randomly arriving drift items."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Collection

from .drift_item_catalog import (
    DRIFT_ITEMS,
    DriftItemDefinition,
    DriftRarity,
)
from .story_content import STORY_RESERVED_SPRITE_IDS


@dataclass(frozen=True, slots=True)
class DriftSelectionPolicy:
    # Strong clues should remain unusual even when several objects arrive.
    max_echo_per_batch: int = 1
    max_owner_handwriting_per_batch: int = 1
    max_clue_level_3_per_batch: int = 1

    # Default gameplay exposes unseen objects before recycling common debris.
    exclude_all_seen: bool = True

    # Fourteen original sprite slots are now used by the fixed letter/memory
    # sequence and must not appear as ambient duplicates unless explicitly
    # requested for a compatibility or debug build.
    exclude_story_reserved: bool = True


DEFAULT_SELECTION_POLICY = DriftSelectionPolicy()


def eligible_drift_items(
    *,
    area_index: int,
    seen_ids: Collection[str] = (),
    policy: DriftSelectionPolicy = DEFAULT_SELECTION_POLICY,
) -> tuple[DriftItemDefinition, ...]:
    if not 0 <= area_index <= 17:
        raise ValueError("area_index must be between 0 (A) and 17 (R)")

    seen = set(seen_ids)

    result: list[DriftItemDefinition] = []

    for item in DRIFT_ITEMS:
        if (
            policy.exclude_story_reserved
            and item.item_id in STORY_RESERVED_SPRITE_IDS
        ):
            continue

        if item.min_area_index > area_index:
            continue

        if item.item_id in seen:
            if policy.exclude_all_seen or item.unique_per_save:
                continue

        result.append(item)

    return tuple(result)


def _weighted_pick(
    rng: Random,
    candidates: list[DriftItemDefinition],
) -> DriftItemDefinition:
    total_weight = sum(item.spawn_weight for item in candidates)

    if total_weight <= 0:
        raise ValueError("No positive spawn weight")

    needle = rng.randrange(total_weight)
    running = 0

    for item in candidates:
        running += item.spawn_weight
        if needle < running:
            return item

    # Defensive fallback for future custom numeric weight types.
    return candidates[-1]


def _passes_batch_caps(
    item: DriftItemDefinition,
    selected: list[DriftItemDefinition],
    policy: DriftSelectionPolicy,
) -> bool:
    if item.rarity is DriftRarity.ECHO:
        echo_count = sum(
            existing.rarity is DriftRarity.ECHO
            for existing in selected
        )
        if echo_count >= policy.max_echo_per_batch:
            return False

    if item.owner_handwriting:
        handwriting_count = sum(
            existing.owner_handwriting
            for existing in selected
        )
        if handwriting_count >= policy.max_owner_handwriting_per_batch:
            return False

    if item.clue_level == 3:
        direct_clue_count = sum(
            existing.clue_level == 3
            for existing in selected
        )
        if direct_clue_count >= policy.max_clue_level_3_per_batch:
            return False

    return True


def select_drift_items(
    *,
    rng: Random,
    area_index: int,
    count: int,
    seen_ids: Collection[str] = (),
    policy: DriftSelectionPolicy = DEFAULT_SELECTION_POLICY,
) -> tuple[DriftItemDefinition, ...]:
    """Select up to `count` distinct objects.

    Returning fewer objects is intentional when progression gates, seen-item
    filtering or clue caps leave too few legal candidates.  The caller can
    schedule another arrival later instead of weakening narrative constraints.
    """

    if count < 0:
        raise ValueError("count must not be negative")

    candidates = list(
        eligible_drift_items(
            area_index=area_index,
            seen_ids=seen_ids,
            policy=policy,
        )
    )

    selected: list[DriftItemDefinition] = []

    while candidates and len(selected) < count:
        legal = [
            item
            for item in candidates
            if _passes_batch_caps(item, selected, policy)
        ]

        if not legal:
            break

        chosen = _weighted_pick(rng, legal)
        selected.append(chosen)

        # A physical drift pattern should not contain the same catalog entry
        # twice, even when the caller allows old common items to return.
        candidates = [
            item
            for item in candidates
            if item.item_id != chosen.item_id
        ]

    return tuple(selected)


def choose_one_drift_item(
    *,
    rng: Random,
    area_index: int,
    seen_ids: Collection[str] = (),
    policy: DriftSelectionPolicy = DEFAULT_SELECTION_POLICY,
) -> DriftItemDefinition | None:
    selected = select_drift_items(
        rng=rng,
        area_index=area_index,
        count=1,
        seen_ids=seen_ids,
        policy=policy,
    )
    return selected[0] if selected else None
