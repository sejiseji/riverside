from __future__ import annotations

from math import degrees, hypot
from typing import Any

from three_line_explorer import palette
from three_line_explorer.camera import CameraSnapshot, camera_button_label, shot_debug_name
from three_line_explorer.config import (
    BOTTOM_UI_HEIGHT,
    CameraShotId,
    SCREEN_H,
    SCREEN_W,
    STICK_UI_KNOB_RADIUS,
    STICK_UI_RADIUS,
    TOP_UI_HEIGHT,
)
from three_line_explorer.input import CAMERA_BUTTON_RECTS, StickBasis
from three_line_explorer.player import PlayerState
from three_line_explorer.renderer import RenderStats
from three_line_explorer.visible_volume import VisibleVolumeState


def draw_ui(
    pyxel: Any,
    *,
    active_camera: CameraShotId,
    stick_active: bool,
    stick_offset: tuple[float, float],
    stick_basis: StickBasis,
    active_rule_label: str,
    debug_visible: bool,
    show_volume: bool,
    show_lanes: bool,
) -> None:
    pyxel.rect(0, 0, SCREEN_W, TOP_UI_HEIGHT, palette.UI_PANEL)
    pyxel.rect(0, SCREEN_H - BOTTOM_UI_HEIGHT, SCREEN_W, BOTTOM_UI_HEIGHT, palette.UI_PANEL)

    for rect_x, rect_y, rect_w, rect_h, shot_id in CAMERA_BUTTON_RECTS:
        fill = palette.UI_ACTIVE if shot_id == active_camera else palette.UI_PANEL_ALT
        pyxel.rect(rect_x, rect_y, rect_w, rect_h, fill)
        pyxel.rectb(rect_x, rect_y, rect_w, rect_h, palette.UI_TEXT)
        pyxel.text(rect_x + 13, rect_y + 9, camera_button_label(shot_id), palette.UI_TEXT)

    pyxel.text(140, 13, f"CAM {camera_button_label(active_camera)} {active_rule_label}", palette.UI_TEXT)
    flags = f"D:{int(debug_visible)} B:{int(show_volume)} L:{int(show_lanes)}"
    pyxel.text(140, 28, flags, palette.UI_MUTED)

    _draw_virtual_stick(
        pyxel,
        stick_active=stick_active,
        stick_offset=stick_offset,
        stick_basis=stick_basis,
    )


def _draw_virtual_stick(
    pyxel: Any,
    *,
    stick_active: bool,
    stick_offset: tuple[float, float],
    stick_basis: StickBasis,
) -> None:
    center_x = SCREEN_W // 2
    center_y = SCREEN_H - BOTTOM_UI_HEIGHT // 2
    fill = palette.UI_ACTIVE if stick_active else palette.UI_PANEL_ALT

    pyxel.circ(center_x, center_y, STICK_UI_RADIUS, fill)
    pyxel.circb(center_x, center_y, STICK_UI_RADIUS, palette.UI_TEXT)
    _draw_axis(pyxel, center_x, center_y, stick_basis.move_forward_x, stick_basis.move_forward_y)
    _draw_axis(pyxel, center_x, center_y, stick_basis.lane_screen_x, stick_basis.lane_screen_y)

    knob_x, knob_y = _stick_knob_position(center_x, center_y, stick_offset)
    pyxel.circ(knob_x, knob_y, STICK_UI_KNOB_RADIUS, palette.UI_TEXT)


def _stick_knob_position(center_x: int, center_y: int, offset: tuple[float, float]) -> tuple[int, int]:
    dx, dy = offset
    length = hypot(dx, dy)
    max_offset = STICK_UI_RADIUS - STICK_UI_KNOB_RADIUS - 3
    if length > max_offset and length > 0.0:
        scale = max_offset / length
        dx *= scale
        dy *= scale
    return round(center_x + dx), round(center_y + dy)


def _draw_axis(pyxel: Any, center_x: int, center_y: int, axis_x: float, axis_y: float) -> None:
    length = 22
    end_length = 26
    pyxel.line(
        round(center_x - axis_x * length),
        round(center_y - axis_y * length),
        round(center_x + axis_x * length),
        round(center_y + axis_y * length),
        palette.UI_TEXT,
    )
    _draw_arrow(
        pyxel,
        center_x + axis_x * end_length,
        center_y + axis_y * end_length,
        axis_x,
        axis_y,
    )
    _draw_arrow(
        pyxel,
        center_x - axis_x * end_length,
        center_y - axis_y * end_length,
        -axis_x,
        -axis_y,
    )


def _draw_arrow(pyxel: Any, x: float, y: float, dx: float, dy: float) -> None:
    side_x = -dy
    side_y = dx
    pyxel.line(
        round(x),
        round(y),
        round(x - dx * 5 + side_x * 4),
        round(y - dy * 5 + side_y * 4),
        palette.UI_TEXT,
    )
    pyxel.line(
        round(x),
        round(y),
        round(x - dx * 5 - side_x * 4),
        round(y - dy * 5 - side_y * 4),
        palette.UI_TEXT,
    )


def draw_debug_hud(
    pyxel: Any,
    *,
    player: PlayerState,
    visible_volume: VisibleVolumeState,
    snapshot: CameraSnapshot,
    stats: RenderStats,
    active_rule_label: str,
    transition_progress: float,
) -> None:
    lines = [
        f"FPS {pyxel.frame_count and pyxel.frame_count}",
        f"P X/Z {player.x:7.2f} {player.z:6.2f}",
        f"VEL X {player.velocity_x:7.2f}",
        f"FACING {player.facing:+d} LANE {player.target_lane_index}",
        f"CAM {shot_debug_name(snapshot.shot_id)}",
        f"AZ/EL {degrees(snapshot.params.azimuth):6.1f} {degrees(snapshot.params.elevation):5.1f}",
        f"DIST {snapshot.params.distance:6.1f} TRANS {transition_progress * 100:5.1f}%",
        f"LANE X {snapshot.lane_screen_x[0]:6.1f} {snapshot.lane_screen_x[1]:6.1f} {snapshot.lane_screen_x[2]:6.1f}",
        f"ORIENT {snapshot.stable_lane_orientation:+d}",
        f"VOL X {visible_volume.center_x:7.2f}",
        f"VOL MIN/MAX {visible_volume.bounds.minimum.x:7.2f} {visible_volume.bounds.maximum.x:7.2f}",
        f"CLAMP L/R {int(visible_volume.clamped_left)} {int(visible_volume.clamped_right)}",
        f"RULE {active_rule_label}",
        f"CAND {stats.candidate_objects} FACES {stats.visible_faces}",
        f"TRI {stats.draw_triangles} LINE {stats.draw_lines} CLIP {stats.clipped_boxes}",
    ]

    x = 8
    y = TOP_UI_HEIGHT + 8
    width = 202
    height = len(lines) * 8 + 6
    pyxel.rect(x - 3, y - 3, width, height, 0)
    pyxel.rectb(x - 3, y - 3, width, height, palette.UI_MUTED)
    for index, line in enumerate(lines):
        pyxel.text(x, y + index * 8, line, palette.UI_TEXT)
