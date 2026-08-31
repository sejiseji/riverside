from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from three_line_explorer import palette
from three_line_explorer.config import (
    INSPECTION_PANEL_H,
    INSPECTION_PANEL_W,
    INSPECTION_PANEL_X,
    INSPECTION_PANEL_Y,
    INSPECTION_PROMPT_HALF_W,
    INSPECTION_PROMPT_HEIGHT,
    INSPECTION_PROMPT_HIT_H,
    INSPECTION_PROMPT_HIT_W,
    INSPECTION_TEXT_COLUMNS,
    INSPECTION_TEXT_MAX_LINES,
    VIEWPORT_H,
    VIEWPORT_W,
    VIEWPORT_X,
    VIEWPORT_Y,
)
from three_line_explorer.geometry import Face, make_aabb_faces
from three_line_explorer.math3d import AABB, Vec3
from three_line_explorer.projection import project_world_point


PROMPT_BOB_Y = (0, 0, -1, -1, -2, -2, -1, -1)


@dataclass(frozen=True, slots=True)
class ScreenRect:
    x: int
    y: int
    width: int
    height: int

    def contains(self, point_x: float, point_y: float) -> bool:
        return (
            self.x <= point_x < self.x + self.width
            and self.y <= point_y < self.y + self.height
        )


@dataclass(frozen=True, slots=True)
class InspectionText:
    title: str
    pages: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PreparedInspectionPage:
    title: str
    lines: tuple[str, ...]
    page_index: int
    page_count: int


@dataclass(frozen=True, slots=True)
class InspectableProp:
    object_id: str
    render_object_id: int
    bounds: AABB
    text_key: str
    marker_height: float = 8.0
    acquire_padding_x: float = 28.0
    acquire_padding_z: float = 12.0
    release_padding_x: float = 36.0
    release_padding_z: float = 18.0
    repeatable: bool = True
    side_color: int = palette.INSPECTABLE_SIDE
    top_color: int = palette.INSPECTABLE_TOP
    outline_color: int = palette.INSPECTABLE_OUTLINE
    faces: tuple[Face, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "faces",
            make_aabb_faces(
                self.bounds,
                self.render_object_id,
                self.side_color,
                self.top_color,
                self.outline_color,
            ),
        )


@dataclass(frozen=True, slots=True)
class PromptSnapshot:
    object_id: str
    hitbox: ScreenRect
    visible: bool


@dataclass(slots=True)
class InteractionState:
    active_target_id: str | None = None
    opened_target_id: str | None = None
    opened_text_key: str | None = None
    page_index: int = 0
    panel_open: bool = False
    inspected_ids: set[str] = field(default_factory=set)
    prepared_pages: tuple[PreparedInspectionPage, ...] = ()


INSPECTION_TEXTS: dict[str, InspectionText] = {
    "single_sandal": InspectionText(
        title="Single sandal",
        pages=(
            "Water has made it heavy. Only one side rests near the river.",
            "Faint marks remain on the sole, but the name is too worn to read.",
        ),
    ),
    "clouded_bottle": InspectionText(
        title="Clouded bottle",
        pages=(
            "A little water is trapped inside. The cap is sealed tight.",
            "The glass is cloudy, as if it has spent a long time drifting.",
        ),
    ),
    "folded_note": InspectionText(
        title="Folded note",
        pages=(
            "The paper is wet, but a few dark lines still show through.",
            "It looks less like trash and more like something someone kept.",
        ),
    ),
}


def panel_rect() -> ScreenRect:
    return ScreenRect(
        INSPECTION_PANEL_X,
        INSPECTION_PANEL_Y,
        INSPECTION_PANEL_W,
        INSPECTION_PANEL_H,
    )


def expanded_xz(bounds: AABB, padding_x: float, padding_z: float) -> AABB:
    return AABB(
        Vec3(
            bounds.minimum.x - padding_x,
            bounds.minimum.y,
            bounds.minimum.z - padding_z,
        ),
        Vec3(
            bounds.maximum.x + padding_x,
            bounds.maximum.y,
            bounds.maximum.z + padding_z,
        ),
    )


def overlaps_xz(a: AABB, b: AABB) -> bool:
    return (
        a.maximum.x >= b.minimum.x
        and a.minimum.x <= b.maximum.x
        and a.maximum.z >= b.minimum.z
        and a.minimum.z <= b.maximum.z
    )


def axis_gap(a_min: float, a_max: float, b_min: float, b_max: float) -> float:
    if a_max < b_min:
        return b_min - a_max
    if b_max < a_min:
        return a_min - b_max
    return 0.0


def xz_gap_squared(player_bounds: AABB, prop_bounds: AABB) -> float:
    dx = axis_gap(
        player_bounds.minimum.x,
        player_bounds.maximum.x,
        prop_bounds.minimum.x,
        prop_bounds.maximum.x,
    )
    dz = axis_gap(
        player_bounds.minimum.z,
        player_bounds.maximum.z,
        prop_bounds.minimum.z,
        prop_bounds.maximum.z,
    )
    return dx * dx + dz * dz


def find_prop_by_id(
    props: tuple[InspectableProp, ...],
    object_id: str | None,
) -> InspectableProp | None:
    if object_id is None:
        return None
    for prop in props:
        if prop.object_id == object_id:
            return prop
    return None


def update_active_target(
    state: InteractionState,
    player_bounds: AABB,
    props: tuple[InspectableProp, ...],
) -> None:
    current = find_prop_by_id(props, state.active_target_id)
    if current is not None:
        release_zone = expanded_xz(
            current.bounds,
            current.release_padding_x,
            current.release_padding_z,
        )
        if overlaps_xz(player_bounds, release_zone):
            return

    candidates: list[tuple[float, str]] = []
    for prop in props:
        if not prop.repeatable and prop.object_id in state.inspected_ids:
            continue
        acquire_zone = expanded_xz(
            prop.bounds,
            prop.acquire_padding_x,
            prop.acquire_padding_z,
        )
        if overlaps_xz(player_bounds, acquire_zone):
            candidates.append((xz_gap_squared(player_bounds, prop.bounds), prop.object_id))

    if not candidates:
        state.active_target_id = None
        return

    candidates.sort()
    state.active_target_id = candidates[0][1]


def marker_world_position(prop: InspectableProp) -> Vec3:
    return Vec3(
        (prop.bounds.minimum.x + prop.bounds.maximum.x) * 0.5,
        prop.bounds.maximum.y + prop.marker_height,
        (prop.bounds.minimum.z + prop.bounds.maximum.z) * 0.5,
    )


def prompt_snapshot_for_prop(
    prop: InspectableProp,
    camera_snapshot: Any,
    visible_bounds: AABB,
) -> PromptSnapshot | None:
    if not visible_bounds.intersects(prop.bounds):
        return None

    projected = project_world_point(camera_snapshot, marker_world_position(prop))
    if projected is None:
        return None
    if not _inside_viewport(projected.x, projected.y):
        return None

    hitbox = ScreenRect(
        round(projected.x) - INSPECTION_PROMPT_HIT_W // 2,
        round(projected.y) - INSPECTION_PROMPT_HIT_H // 2,
        INSPECTION_PROMPT_HIT_W,
        INSPECTION_PROMPT_HIT_H,
    )
    return PromptSnapshot(prop.object_id, hitbox, True)


def open_inspection(
    state: InteractionState,
    prop: InspectableProp,
    texts: dict[str, InspectionText] | None = None,
) -> bool:
    if texts is None:
        texts = INSPECTION_TEXTS
    text = texts.get(prop.text_key)
    if text is None:
        return False

    state.panel_open = True
    state.opened_target_id = prop.object_id
    state.opened_text_key = prop.text_key
    state.page_index = 0
    state.inspected_ids.add(prop.object_id)
    state.prepared_pages = tuple(
        _prepare_page(text.title, page, index, len(text.pages))
        for index, page in enumerate(text.pages)
    )
    return True


def advance_or_close_inspection(state: InteractionState) -> None:
    if not state.panel_open:
        return
    if state.page_index + 1 < len(state.prepared_pages):
        state.page_index += 1
        return
    close_inspection(state)


def close_inspection(state: InteractionState) -> None:
    state.panel_open = False
    state.opened_target_id = None
    state.opened_text_key = None
    state.page_index = 0
    state.prepared_pages = ()


def current_page(state: InteractionState) -> PreparedInspectionPage | None:
    if not state.panel_open or not state.prepared_pages:
        return None
    if state.page_index < 0 or state.page_index >= len(state.prepared_pages):
        return None
    return state.prepared_pages[state.page_index]


def can_open_prop(player_bounds: AABB, prop: InspectableProp) -> bool:
    release_zone = expanded_xz(
        prop.bounds,
        prop.release_padding_x,
        prop.release_padding_z,
    )
    return overlaps_xz(player_bounds, release_zone)


def draw_inspection_prompt(pyxel: Any, prompt: PromptSnapshot) -> None:
    center_x = prompt.hitbox.x + prompt.hitbox.width // 2
    center_y = prompt.hitbox.y + prompt.hitbox.height // 2
    bob = PROMPT_BOB_Y[(pyxel.frame_count // 4) % len(PROMPT_BOB_Y)]
    y = center_y + bob
    x1 = center_x - INSPECTION_PROMPT_HALF_W
    y1 = y - 4
    x2 = center_x + INSPECTION_PROMPT_HALF_W
    y2 = y - 4
    x3 = center_x
    y3 = y + INSPECTION_PROMPT_HEIGHT - 4
    pyxel.tri(x1, y1, x2, y2, x3, y3, palette.INSPECTION_PROMPT_FILL)
    if hasattr(pyxel, "trib"):
        pyxel.trib(x1, y1, x2, y2, x3, y3, palette.INSPECTION_PROMPT_OUTLINE)
    else:
        pyxel.line(x1, y1, x2, y2, palette.INSPECTION_PROMPT_OUTLINE)
        pyxel.line(x2, y2, x3, y3, palette.INSPECTION_PROMPT_OUTLINE)
        pyxel.line(x3, y3, x1, y1, palette.INSPECTION_PROMPT_OUTLINE)


def draw_inspection_panel(pyxel: Any, state: InteractionState) -> None:
    page = current_page(state)
    rect = panel_rect()
    pyxel.rect(rect.x, rect.y, rect.width, rect.height, palette.INSPECTION_PANEL_FILL)
    pyxel.rectb(rect.x, rect.y, rect.width, rect.height, palette.INSPECTION_PANEL_BORDER)
    if page is None:
        return

    text_x = rect.x + 12
    y = rect.y + 12
    pyxel.text(text_x, y, page.title, palette.INSPECTION_PANEL_TEXT)
    y += 18
    for line in page.lines[:INSPECTION_TEXT_MAX_LINES]:
        pyxel.text(text_x, y, line, palette.INSPECTION_PANEL_TEXT)
        y += 8

    footer_y = rect.y + rect.height - 18
    pyxel.text(
        text_x,
        footer_y,
        f"{page.page_index + 1} / {page.page_count}",
        palette.INSPECTION_PANEL_MUTED,
    )
    pyxel.text(
        rect.x + rect.width - 48,
        footer_y,
        "TAP >",
        palette.INSPECTION_PANEL_TEXT,
    )


def _prepare_page(
    title: str,
    text: str,
    page_index: int,
    page_count: int,
) -> PreparedInspectionPage:
    return PreparedInspectionPage(
        title=title,
        lines=tuple(_wrap_ascii_text(text, INSPECTION_TEXT_COLUMNS)),
        page_index=page_index,
        page_count=page_count,
    )


def _wrap_ascii_text(text: str, columns: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= columns:
            current = f"{current} {word}"
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _inside_viewport(x: float, y: float) -> bool:
    return (
        VIEWPORT_X <= x < VIEWPORT_X + VIEWPORT_W
        and VIEWPORT_Y <= y < VIEWPORT_Y + VIEWPORT_H
    )
