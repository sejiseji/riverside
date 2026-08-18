from __future__ import annotations

from dataclasses import dataclass, field
from math import floor

from three_line_explorer.config import (
    CameraShotId,
    LaneId,
    STAGE_CHUNK_SIZE_X,
    STAGE_MAX_X,
    STAGE_MIN_X,
)
from three_line_explorer.geometry import AabbSolid
from three_line_explorer.math3d import AABB, Vec3


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
    chunks: dict[int, tuple[AabbSolid, ...]] = field(default_factory=dict)

    @classmethod
    def create_prototype(cls) -> Stage:
        solids = tuple(_create_prototype_solids())
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
        stage = cls(solids=solids, zones=zones)
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

    def active_camera_rule(self, player_x: float, lane_index: int) -> tuple[CameraRule, str]:
        matches = [zone for zone in self.zones if zone.contains(player_x, lane_index)]
        if not matches:
            return DEFAULT_CAMERA_RULE, "DEFAULT"
        zone = max(matches, key=lambda item: item.rule.priority)
        return zone.rule, zone.label


def chunk_index(x: float) -> int:
    return floor((x - STAGE_MIN_X) / STAGE_CHUNK_SIZE_X)


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
    add((-380.0, 0.0, 44.0), (-362.0, 86.0, 58.0), 5, 6)
    add((362.0, 0.0, -58.0), (380.0, 86.0, -44.0), 5, 6)
    add((362.0, 0.0, 44.0), (380.0, 86.0, 58.0), 5, 6)

    add((-80.0, 0.0, -58.0), (-52.0, 26.0, -46.0), 4, 12)
    add((-18.0, 0.0, 46.0), (16.0, 42.0, 58.0), 9, 10)
    add((55.0, 0.0, -18.0), (82.0, 55.0, -7.0), 13, 12)
    add((35.0, 0.0, 14.0), (52.0, 62.0, 25.0), 3, 11)

    add((-250.0, 0.0, -60.0), (-110.0, 32.0, -48.0), 2, 8)

    add((-455.0, 0.0, 52.0), (-405.0, 0.6, 60.0), 1, 12)
    add((-385.0, 0.0, 52.0), (-335.0, 0.6, 60.0), 1, 12)
    add((-300.0, 0.0, 52.0), (-250.0, 0.6, 60.0), 1, 12)
    add((-230.0, 0.0, 52.0), (-180.0, 0.6, 60.0), 1, 12)
    add((-140.0, 0.0, 52.0), (-90.0, 0.6, 60.0), 1, 12)
    add((-70.0, 0.0, 52.0), (-20.0, 0.6, 60.0), 1, 12)
    add((25.0, 0.0, 52.0), (75.0, 0.6, 60.0), 1, 12)
    add((95.0, 0.0, 52.0), (145.0, 0.6, 60.0), 1, 12)
    add((185.0, 0.0, 52.0), (235.0, 0.6, 60.0), 1, 12)
    add((255.0, 0.0, 52.0), (305.0, 0.6, 60.0), 1, 12)
    add((340.0, 0.0, 52.0), (390.0, 0.6, 60.0), 1, 12)
    add((410.0, 0.0, 52.0), (460.0, 0.6, 60.0), 1, 12)

    add((-430.0, 0.0, 46.5), (-388.0, 6.0, 51.0), 4, 9)
    add((-294.0, 0.0, 46.5), (-252.0, 6.0, 51.0), 4, 9)
    add((-168.0, 0.0, 46.5), (-126.0, 6.0, 51.0), 4, 9)
    add((-38.0, 0.0, 46.5), (4.0, 6.0, 51.0), 4, 9)
    add((122.0, 0.0, 46.5), (164.0, 6.0, 51.0), 4, 9)
    add((272.0, 0.0, 46.5), (314.0, 6.0, 51.0), 4, 9)
    add((404.0, 0.0, 46.5), (446.0, 6.0, 51.0), 4, 9)

    add((-408.0, 0.0, 49.0), (-400.0, 18.0, 57.0), 4, 10)
    add((-270.0, 0.0, 49.0), (-262.0, 18.0, 57.0), 4, 10)
    add((-142.0, 0.0, 49.0), (-134.0, 18.0, 57.0), 4, 10)
    add((140.0, 0.0, 49.0), (148.0, 18.0, 57.0), 4, 10)
    add((292.0, 0.0, 49.0), (300.0, 18.0, 57.0), 4, 10)
    add((424.0, 0.0, 49.0), (432.0, 18.0, 57.0), 4, 10)

    add((140.0, 0.0, -6.0), (152.0, 50.0, 6.0), 8, 10)
    add((220.0, 0.0, -6.0), (232.0, 50.0, 6.0), 8, 10)
    add((-260.0, 0.0, 48.0), (-248.0, 46.0, 60.0), 11, 12)
    add((-160.0, 0.0, 48.0), (-148.0, 46.0, 60.0), 11, 12)

    add((STAGE_MIN_X, 0.0, -60.0), (STAGE_MIN_X + 10.0, 100.0, -50.0), 7, 6)
    add((STAGE_MAX_X - 10.0, 0.0, 50.0), (STAGE_MAX_X, 100.0, 60.0), 7, 6)
    return solids
