from __future__ import annotations

from dataclasses import dataclass, field
from math import floor
from typing import Final

from three_line_explorer.config import (
    CameraShotId,
    ENVIRONMENT_OBJECT_ID_BASE,
    INSPECTABLE_OBJECT_ID_BASE,
    LaneId,
    PLAYER_START_X,
    RIVER_START_Z,
    STAGE_AREA_COUNT,
    STAGE_CHUNK_SIZE_X,
    STAGE_MAX_X,
    STAGE_MIN_X,
    STORY_INSPECTABLE_OBJECT_ID_BASE,
)
from three_line_explorer.drift_item_catalog import DRIFT_ITEM_BY_ID
from three_line_explorer.environment_sprites import (
    EnvironmentSpriteInstance,
    make_environment_sprite_instance,
)
from three_line_explorer.generated_environment_assets import WORLD_SPRITES
from three_line_explorer.geometry import AabbSolid
from three_line_explorer.inspection import InspectableProp
from three_line_explorer.math3d import AABB, Vec3, clamp, clamp_int
from three_line_explorer.story_content import StoryInspectionDefinition


AREA_LABELS: Final[tuple[str, ...]] = tuple("ABCDEFGHIJKLMNOPQR")
if len(AREA_LABELS) != STAGE_AREA_COUNT:
    raise ValueError("AREA_LABELS must match STAGE_AREA_COUNT")


@dataclass(frozen=True, slots=True)
class StageArea:
    index: int
    label: str
    x_min: float
    x_max: float
    center_x: float
    theme: str


STAGE_AREA_THEMES: Final[tuple[str, ...]] = (
    "left_edge_drain",
    "quiet_reeds",
    "narrow_bank",
    "fallen_branches",
    "shallow_pool",
    "discarded_path",
    "old_sign",
    "mossy_turn",
    "start_bank",
    "cat_start",
    "open_river",
    "stone_marker",
    "forced_camera_gate",
    "thin_grass",
    "wide_water",
    "long_shadow",
    "last_bend",
    "right_edge_flow",
)


def _build_stage_areas() -> tuple[StageArea, ...]:
    area_width = (STAGE_MAX_X - STAGE_MIN_X) / STAGE_AREA_COUNT
    return tuple(
        StageArea(
            index=index,
            label=label,
            x_min=STAGE_MIN_X + index * area_width,
            x_max=STAGE_MIN_X + (index + 1) * area_width,
            center_x=STAGE_MIN_X + (index + 0.5) * area_width,
            theme=STAGE_AREA_THEMES[index],
        )
        for index, label in enumerate(AREA_LABELS)
    )


STAGE_AREAS: Final[tuple[StageArea, ...]] = _build_stage_areas()
STAGE_AREA_BY_LABEL: Final[dict[str, StageArea]] = {
    area.label: area for area in STAGE_AREAS
}


@dataclass(frozen=True, slots=True)
class DriftPropSlot:
    area_label: str
    item_id: str
    x_offset: float = 0.0


@dataclass(frozen=True, slots=True)
class EnvironmentSpriteSlot:
    area_label: str
    sprite_id: str
    x_offset: float
    z: float


PROTOTYPE_DRIFT_PROP_SLOTS: Final[tuple[DriftPropSlot, ...]] = (
    DriftPropSlot("J", "single_sandal", 32.0),
    DriftPropSlot("I", "clouded_bottle", -2.0),
    DriftPropSlot("L", "sprouted_driftwood", -18.0),
    DriftPropSlot("M", "rusted_key", -12.0),
    DriftPropSlot("F", "yellow_name_tag", -26.0),
    DriftPropSlot("H", "stopped_watch", -22.0),
    DriftPropSlot("N", "chipped_mug", -14.0),
    DriftPropSlot("P", "bent_spoon", 0.0),
    DriftPropSlot("R", "child_rain_boot", -38.0),
)


PROTOTYPE_ENVIRONMENT_SPRITE_SLOTS: Final[tuple[EnvironmentSpriteSlot, ...]] = (
    EnvironmentSpriteSlot("E", "dead_tree_trunk", 24.0, -55.0),
    EnvironmentSpriteSlot("K", "mossy_rock", -24.0, -22.0),
    EnvironmentSpriteSlot("G", "weathered_sign", 2.0, -53.0),
    EnvironmentSpriteSlot("N", "jizo", -36.0, -54.0),
    EnvironmentSpriteSlot("F", "grass_tuft", -8.0, -51.0),
    EnvironmentSpriteSlot("H", "fern", -6.0, -50.0),
    EnvironmentSpriteSlot("I", "bracken", 32.0, -52.0),
    EnvironmentSpriteSlot("K", "butterbur", 32.0, -54.0),
    EnvironmentSpriteSlot("M", "horsetail", -28.0, -50.0),
    EnvironmentSpriteSlot("O", "sapling", -30.0, -55.0),
    EnvironmentSpriteSlot("P", "grass_tuft", 28.0, -51.0),
    EnvironmentSpriteSlot("Q", "mossy_rock", 4.0, -24.0),
    EnvironmentSpriteSlot("R", "fern", -10.0, -52.0),
)


@dataclass(frozen=True, slots=True)
class CameraRule:
    allowed_shots: frozenset[CameraShotId]
    manual_enabled: bool
    forced_shot: CameraShotId | None
    priority: int


@dataclass(frozen=True, slots=True)
class CameraZone:
    x_min: float
    x_max: float
    lane_mask: int
    rule: CameraRule
    label: str

    def contains(self, x: float, lane_index: int) -> bool:
        return self.x_min <= x <= self.x_max and bool(self.lane_mask & lane_mask(lane_index))


def lane_mask(lane_index: int) -> int:
    return 1 << int(lane_index)


ALL_LANE_MASK = lane_mask(LaneId.NEGATIVE_Z) | lane_mask(LaneId.CENTER) | lane_mask(LaneId.POSITIVE_Z)
ALL_CAMERA_SHOTS = frozenset(CameraShotId)
DEFAULT_CAMERA_RULE = CameraRule(
    allowed_shots=ALL_CAMERA_SHOTS,
    manual_enabled=True,
    forced_shot=None,
    priority=0,
)


@dataclass(slots=True)
class Stage:
    solids: tuple[AabbSolid, ...]
    zones: tuple[CameraZone, ...]
    inspectable_props: tuple[InspectableProp, ...] = ()
    environment_sprites: tuple[EnvironmentSpriteInstance, ...] = ()
    collision_solids: tuple[AabbSolid, ...] = ()
    chunks: dict[int, tuple[AabbSolid, ...]] = field(default_factory=dict)
    prop_chunks: dict[int, tuple[InspectableProp, ...]] = field(default_factory=dict)
    environment_sprite_chunks: dict[int, tuple[EnvironmentSpriteInstance, ...]] = field(default_factory=dict)
    collision_chunks: dict[int, tuple[AabbSolid, ...]] = field(default_factory=dict)

    @classmethod
    def create_prototype(cls) -> Stage:
        solids: tuple[AabbSolid, ...] = ()
        environment_sprites = tuple(_create_prototype_environment_sprites())
        inspectable_props = tuple(_create_prototype_inspectable_props(environment_sprites))
        collision_solids = tuple(_create_environment_collision_solids(environment_sprites))
        zones = (
            CameraZone(
                x_min=140.0,
                x_max=STAGE_MAX_X,
                lane_mask=ALL_LANE_MASK,
                rule=CameraRule(
                    allowed_shots=ALL_CAMERA_SHOTS,
                    manual_enabled=False,
                    forced_shot=CameraShotId.FRONT_RIGHT_CLOSE,
                    priority=20,
                ),
                label="FORCED_B",
            ),
            CameraZone(
                x_min=-260.0,
                x_max=-160.0,
                lane_mask=ALL_LANE_MASK,
                rule=CameraRule(
                    allowed_shots=frozenset(
                        {
                            CameraShotId.REAR_RIGHT_LOW,
                            CameraShotId.REAR_LEFT_SHALLOW,
                            CameraShotId.RIGHT_SIDE_WIDE,
                        }
                    ),
                    manual_enabled=True,
                    forced_shot=None,
                    priority=10,
                ),
                label="ALLOW_A_C_D",
            ),
        )
        stage = cls(
            solids=solids,
            zones=zones,
            inspectable_props=inspectable_props,
            environment_sprites=environment_sprites,
            collision_solids=collision_solids,
        )
        stage.rebuild_chunks()
        return stage

    @classmethod
    def create_render_test(cls) -> Stage:
        """Create the old color-block scene for renderer stress checks."""
        stage = cls(
            solids=tuple(_create_debug_aabb_solids()),
            zones=(),
            inspectable_props=(),
            environment_sprites=(),
            collision_solids=(),
        )
        stage.rebuild_chunks()
        return stage

    def rebuild_chunks(self) -> None:
        mutable: dict[int, list[AabbSolid]] = {}
        for solid in self.solids:
            first = chunk_index(solid.bounds.minimum.x)
            last = chunk_index(solid.bounds.maximum.x)
            for index in range(first, last + 1):
                mutable.setdefault(index, []).append(solid)
        self.chunks = {index: tuple(values) for index, values in mutable.items()}

        prop_mutable: dict[int, list[InspectableProp]] = {}
        for prop in self.inspectable_props:
            first = chunk_index(prop.bounds.minimum.x)
            last = chunk_index(prop.bounds.maximum.x)
            for index in range(first, last + 1):
                prop_mutable.setdefault(index, []).append(prop)
        self.prop_chunks = {index: tuple(values) for index, values in prop_mutable.items()}

        environment_mutable: dict[int, list[EnvironmentSpriteInstance]] = {}
        for sprite in self.environment_sprites:
            first = chunk_index(sprite.bounds.minimum.x)
            last = chunk_index(sprite.bounds.maximum.x)
            for index in range(first, last + 1):
                environment_mutable.setdefault(index, []).append(sprite)
        self.environment_sprite_chunks = {
            index: tuple(values) for index, values in environment_mutable.items()
        }

        collision_mutable: dict[int, list[AabbSolid]] = {}
        for solid in (*self.solids, *self.collision_solids):
            first = chunk_index(solid.bounds.minimum.x)
            last = chunk_index(solid.bounds.maximum.x)
            for index in range(first, last + 1):
                collision_mutable.setdefault(index, []).append(solid)
        self.collision_chunks = {
            index: tuple(values) for index, values in collision_mutable.items()
        }

    def candidate_solids(self, bounds: AABB) -> tuple[AabbSolid, ...]:
        first = chunk_index(bounds.minimum.x)
        last = chunk_index(bounds.maximum.x)
        seen: set[int] = set()
        candidates: list[AabbSolid] = []
        for index in range(first, last + 1):
            for solid in self.chunks.get(index, ()):
                if solid.object_id in seen:
                    continue
                seen.add(solid.object_id)
                if solid.bounds.intersects(bounds):
                    candidates.append(solid)
        return tuple(candidates)

    def candidate_inspectable_props(self, bounds: AABB) -> tuple[InspectableProp, ...]:
        first = chunk_index(bounds.minimum.x)
        last = chunk_index(bounds.maximum.x)
        seen: set[str] = set()
        candidates: list[InspectableProp] = []
        for index in range(first, last + 1):
            for prop in self.prop_chunks.get(index, ()):
                if prop.object_id in seen:
                    continue
                seen.add(prop.object_id)
                if prop.bounds.intersects(bounds):
                    candidates.append(prop)
        return tuple(candidates)

    def candidate_environment_sprites(
        self,
        bounds: AABB,
    ) -> tuple[EnvironmentSpriteInstance, ...]:
        first = chunk_index(bounds.minimum.x)
        last = chunk_index(bounds.maximum.x)
        seen: set[int] = set()
        candidates: list[EnvironmentSpriteInstance] = []
        for index in range(first, last + 1):
            for sprite in self.environment_sprite_chunks.get(index, ()):
                if sprite.object_id in seen:
                    continue
                seen.add(sprite.object_id)
                if sprite.bounds.intersects(bounds):
                    candidates.append(sprite)
        return tuple(candidates)

    def candidate_collision_solids(self, bounds: AABB) -> tuple[AabbSolid, ...]:
        first = chunk_index(bounds.minimum.x)
        last = chunk_index(bounds.maximum.x)
        seen: set[int] = set()
        candidates: list[AabbSolid] = []
        for index in range(first, last + 1):
            for solid in self.collision_chunks.get(index, ()):
                if solid.object_id in seen:
                    continue
                seen.add(solid.object_id)
                if solid.bounds.intersects(bounds):
                    candidates.append(solid)
        return tuple(candidates)

    def active_camera_rule(self, player_x: float, lane_index: int) -> tuple[CameraRule, str]:
        matches = [zone for zone in self.zones if zone.contains(player_x, lane_index)]
        if not matches:
            return DEFAULT_CAMERA_RULE, "DEFAULT"
        zone = max(matches, key=lambda item: item.rule.priority)
        return zone.rule, zone.label


def chunk_index(x: float) -> int:
    return floor((x - STAGE_MIN_X) / STAGE_CHUNK_SIZE_X)


def area_index_for_x(x: float) -> int:
    area_width = (STAGE_MAX_X - STAGE_MIN_X) / STAGE_AREA_COUNT
    raw_index = int(floor((clamp(x, STAGE_MIN_X, STAGE_MAX_X) - STAGE_MIN_X) / area_width))
    return clamp_int(raw_index, 0, STAGE_AREA_COUNT - 1)


def area_center_x(area_index: int) -> float:
    return stage_area_for_index(area_index).center_x


def stage_area_for_index(area_index: int) -> StageArea:
    return STAGE_AREAS[clamp_int(area_index, 0, STAGE_AREA_COUNT - 1)]


def stage_area_for_label(label: str) -> StageArea:
    normalized = label.upper()
    if normalized not in STAGE_AREA_BY_LABEL:
        raise ValueError(f"Unknown stage area label: {label}")
    return STAGE_AREA_BY_LABEL[normalized]


def area_label_for_x(x: float) -> str:
    return stage_area_for_index(area_index_for_x(x)).label


def story_area_index_for_x(x: float) -> int:
    route_length = STAGE_MAX_X - PLAYER_START_X
    if route_length <= 0.0:
        return 0
    clamped_x = clamp(x, PLAYER_START_X, STAGE_MAX_X)
    raw_index = int(floor((clamped_x - PLAYER_START_X) / route_length * STAGE_AREA_COUNT))
    return clamp_int(raw_index, 0, STAGE_AREA_COUNT - 1)


def make_story_inspectable_prop(
    story_item: StoryInspectionDefinition,
    *,
    player_x: float,
) -> InspectableProp:
    item = DRIFT_ITEM_BY_ID[story_item.sprite_id]
    x = clamp(
        player_x + 44.0,
        STAGE_MIN_X + 32.0,
        STAGE_MAX_X - 32.0,
    )
    return _drift_prop(
        object_id=f"story_{story_item.content_id}",
        render_object_id=STORY_INSPECTABLE_OBJECT_ID_BASE + story_item.sequence_index,
        item_id=story_item.sprite_id,
        x=x,
        text_key=story_item.text_key,
        marker_height=item.marker_offset_y,
        repeatable=False,
    )


def _solid(
    object_id: int,
    minimum: tuple[float, float, float],
    maximum: tuple[float, float, float],
    side_color: int,
    top_color: int,
    outline_color: int = 0,
) -> AabbSolid:
    return AabbSolid(
        object_id=object_id,
        bounds=AABB(Vec3(*minimum), Vec3(*maximum)),
        side_color=side_color,
        top_color=top_color,
        outline_color=outline_color,
    )


def _create_debug_aabb_solids() -> list[AabbSolid]:
    solids: list[AabbSolid] = []
    object_id = 1

    def add(
        minimum: tuple[float, float, float],
        maximum: tuple[float, float, float],
        side_color: int,
        top_color: int,
    ) -> None:
        nonlocal object_id
        solids.append(_solid(object_id, minimum, maximum, side_color, top_color))
        object_id += 1

    add((-380.0, 0.0, -58.0), (-362.0, 86.0, -44.0), 5, 6)
    add((362.0, 0.0, -58.0), (380.0, 86.0, -44.0), 5, 6)

    add((-80.0, 0.0, -58.0), (-52.0, 26.0, -46.0), 4, 12)
    add((55.0, 0.0, -18.0), (82.0, 55.0, -7.0), 13, 12)
    add((35.0, 0.0, 14.0), (52.0, 62.0, 25.0), 3, 11)

    add((-250.0, 0.0, -60.0), (-110.0, 32.0, -48.0), 2, 8)

    add((140.0, 0.0, -6.0), (152.0, 50.0, 6.0), 8, 10)
    add((220.0, 0.0, -6.0), (232.0, 50.0, 6.0), 8, 10)

    add((STAGE_MIN_X, 0.0, -60.0), (STAGE_MIN_X + 10.0, 100.0, -50.0), 7, 6)
    add((STAGE_MAX_X - 10.0, 0.0, -60.0), (STAGE_MAX_X, 100.0, -50.0), 7, 6)
    return solids


def _create_prototype_inspectable_props(
    environment_sprites: tuple[EnvironmentSpriteInstance, ...],
) -> list[InspectableProp]:
    props = [
        _drift_prop(
            object_id=f"river_prop_{index:03d}",
            render_object_id=INSPECTABLE_OBJECT_ID_BASE + index,
            item_id=slot.item_id,
            x=_drift_slot_x(slot),
        )
        for index, slot in enumerate(PROTOTYPE_DRIFT_PROP_SLOTS, start=1)
    ]
    props.extend(
        prop
        for prop in (
            _environment_inspectable_prop(sprite)
            for sprite in environment_sprites
        )
        if prop is not None
    )
    return props


def _drift_slot_x(slot: DriftPropSlot) -> float:
    area = stage_area_for_label(slot.area_label)
    item = DRIFT_ITEM_BY_ID[slot.item_id]
    margin = max(item.world_width * 0.5, 5.0) + 2.0
    return clamp(
        area.center_x + slot.x_offset,
        area.x_min + margin,
        area.x_max - margin,
    )


def _drift_prop(
    *,
    object_id: str,
    render_object_id: int,
    item_id: str,
    x: float,
    text_key: str | None = None,
    marker_height: float | None = None,
    repeatable: bool = True,
) -> InspectableProp:
    item = DRIFT_ITEM_BY_ID[item_id]
    visual_half_x = max(item.world_width * 0.5, 5.0)
    visual_half_z = max(item.world_width * 0.28, 4.0)
    center_z = RIVER_START_Z + 9.5
    return InspectableProp(
        object_id=object_id,
        render_object_id=render_object_id,
        bounds=AABB(
            Vec3(x - visual_half_x, 0.0, center_z - visual_half_z),
            Vec3(x + visual_half_x, 4.0, center_z + visual_half_z),
        ),
        text_key=text_key or item.text_key,
        sprite_id=item.sprite_id,
        marker_height=marker_height if marker_height is not None else item.marker_offset_y,
        acquire_padding_x=item.acquire_padding_x,
        acquire_padding_z=item.acquire_padding_z,
        release_padding_x=item.acquire_padding_x + 8.0,
        release_padding_z=item.acquire_padding_z + 6.0,
        repeatable=repeatable,
    )


def _create_prototype_environment_sprites() -> list[EnvironmentSpriteInstance]:
    def env(offset: int, slot: EnvironmentSpriteSlot) -> EnvironmentSpriteInstance:
        return make_environment_sprite_instance(
            object_id=ENVIRONMENT_OBJECT_ID_BASE + offset,
            sprite_id=slot.sprite_id,
            x=_environment_slot_x(slot),
            z=slot.z,
        )

    return [
        env(index, slot)
        for index, slot in enumerate(PROTOTYPE_ENVIRONMENT_SPRITE_SLOTS, start=1)
    ]


def _environment_slot_x(slot: EnvironmentSpriteSlot) -> float:
    area = stage_area_for_label(slot.area_label)
    spec = WORLD_SPRITES[slot.sprite_id]
    margin = spec.world_width * 0.5 + 2.0
    return clamp(
        area.center_x + slot.x_offset,
        area.x_min + margin,
        area.x_max - margin,
    )


def _environment_inspectable_prop(
    sprite: EnvironmentSpriteInstance,
) -> InspectableProp | None:
    spec = WORLD_SPRITES[sprite.sprite_id]
    if spec.inspectable_text_key is None:
        return None
    return InspectableProp(
        object_id=f"environment_{sprite.sprite_id}",
        render_object_id=sprite.object_id,
        bounds=sprite.bounds,
        text_key=spec.inspectable_text_key,
        sprite_id=None,
        marker_height=10.0,
        acquire_padding_x=24.0,
        acquire_padding_z=14.0,
        release_padding_x=32.0,
        release_padding_z=20.0,
    )


def _create_environment_collision_solids(
    sprites: tuple[EnvironmentSpriteInstance, ...],
) -> list[AabbSolid]:
    return [
        AabbSolid(sprite.object_id, sprite.collision_bounds, 0, 0, 0)
        for sprite in sprites
        if sprite.collision_bounds is not None
    ]
