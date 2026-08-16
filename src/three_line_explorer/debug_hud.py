from __future__ import annotations

from math import degrees
from typing import Any

from three_line_explorer import palette
from three_line_explorer.camera import CameraSnapshot, camera_button_label, shot_debug_name
from three_line_explorer.config import (
    BOTTOM_UI_HEIGHT,
    CameraShotId,
    SCREEN_H,
    SCREEN_W,
    TOP_UI_HEIGHT,
)
from three_line_explorer.input import CAMERA_BUTTON_RECTS, MOVE_BUTTON_RECTS
from three_line_explorer.player import PlayerState
from three_line_explorer.renderer import RenderStats
from three_line_explorer.visible_volume import VisibleVolumeState


def draw_ui(
    pyxel: Any,
    *,
    active_camera: CameraShotId,
    latched_move_axis: float,
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

    for rect_x, rect_y, rect_w, rect_h, move_axis, label in MOVE_BUTTON_RECTS:
        fill = palette.UI_ACTIVE if move_axis == latched_move_axis else palette.UI_PANEL_ALT
        pyxel.rect(rect_x, rect_y, rect_w, rect_h, fill)
        pyxel.rectb(rect_x, rect_y, rect_w, rect_h, palette.UI_TEXT)
        label_x = rect_x + (rect_w - len(label) * 4) // 2
        pyxel.text(label_x, rect_y + 14, label, palette.UI_TEXT)


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
