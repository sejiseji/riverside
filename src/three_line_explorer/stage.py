from __future__ import annotations

from dataclasses import dataclass, field
from math import floor

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
from three_line_explorer.geometry import AabbSolid
from three_line_explorer.inspection import InspectableProp
from three_line_explorer.math3d import AABB, Vec3, clamp, clamp_int
from three_line_explorer.story_content import StoryInspectionDefinition


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
        solids = tuple(_create_prototype_solids())
        inspectable_props = tuple(_create_prototype_inspectable_props())
        environment_sprites = tuple(_create_prototype_environment_sprites())
        collision_solids = tuple(_create_environment_collision_solids(environment_sprites))
        zones = (
            CameraZone(
                x_min=140.0,
                x_max=220.0,
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
                        {CameraShotId.REAR_RIGHT_LOW, CameraShotId.REAR_LEFT_SHALLOW}
                    ),
                    manual_enabled=True,
                    forced_shot=None,
                    priority=10,
                ),
                label="ALLOW_A_C",
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
    clamped_index = clamp_int(area_index, 0, STAGE_AREA_COUNT - 1)
    area_width = (STAGE_MAX_X - STAGE_MIN_X) / STAGE_AREA_COUNT
    return STAGE_MIN_X + (clamped_index + 0.5) * area_width


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


def _create_prototype_solids() -> list[AabbSolid]:
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
    return solids


def _create_prototype_inspectable_props() -> list[InspectableProp]:
    items = (
        ("single_sandal", 72.0),
        ("clouded_bottle", -42.0),
        ("sprouted_driftwood", 182.0),
        ("rusted_key", 268.0),
        ("yellow_name_tag", -306.0),
        ("stopped_watch", -142.0),
        ("chipped_mug", 346.0),
    )
    props = [
        _drift_prop(
            object_id=f"river_prop_{index:03d}",
            render_object_id=INSPECTABLE_OBJECT_ID_BASE + index,
            item_id=item_id,
            x=x,
        )
        for index, (item_id, x) in enumerate(items, start=1)
    ]
    props.append(
        InspectableProp(
            object_id="environment_weathered_sign",
            render_object_id=ENVIRONMENT_OBJECT_ID_BASE + 3,
            bounds=AABB(
                Vec3(-206.0, 0.0, -61.0),
                Vec3(-190.0, 30.0, -45.0),
            ),
            text_key="weathered_forest_sign",
            sprite_id=None,
            marker_height=10.0,
            acquire_padding_x=24.0,
            acquire_padding_z=14.0,
            release_padding_x=32.0,
            release_padding_z=20.0,
        )
    )
    return props


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
    def env(offset: int, sprite_id: str, x: float, z: float) -> EnvironmentSpriteInstance:
        return make_environment_sprite_instance(
            object_id=ENVIRONMENT_OBJECT_ID_BASE + offset,
            sprite_id=sprite_id,
            x=x,
            z=z,
        )

    return [
        env(1, "dead_tree_trunk", -336.0, -55.0),
        env(2, "mossy_rock", 96.0, -22.0),
        env(3, "weathered_sign", -198.0, -53.0),
        env(4, "jizo", 324.0, -54.0),
        env(5, "grass_tuft", -288.0, -51.0),
        env(6, "fern", -126.0, -50.0),
        env(7, "bracken", -8.0, -52.0),
        env(8, "butterbur", 152.0, -54.0),
        env(9, "horsetail", 252.0, -50.0),
        env(10, "sapling", 410.0, -55.0),
    ]


def _create_environment_collision_solids(
    sprites: tuple[EnvironmentSpriteInstance, ...],
) -> list[AabbSolid]:
    return [
        AabbSolid(sprite.object_id, sprite.collision_bounds, 0, 0, 0)
        for sprite in sprites
        if sprite.collision_bounds is not None
    ]
