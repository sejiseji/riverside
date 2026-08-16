from __future__ import annotations

from dataclasses import dataclass

from three_line_explorer import palette
from three_line_explorer.camera import (
    CameraRig,
    CameraSnapshot,
    compute_lane_screen_x,
    make_camera_snapshot,
    update_stable_lane_orientation,
)
from three_line_explorer.camera_director import CameraDirector
from three_line_explorer.config import DT, FPS, SCREEN_H, SCREEN_W
from three_line_explorer.debug_hud import draw_debug_hud, draw_ui
from three_line_explorer.input import InputAdapter
from three_line_explorer.player import (
    PlayerState,
    change_lane_by_world_step,
    create_player,
    reset_player,
    update_player,
    warp_player_near_left,
    warp_player_near_right,
)
from three_line_explorer.renderer import RenderStats, Renderer
from three_line_explorer.stage import CameraRule, Stage
from three_line_explorer.visible_volume import VisibleVolumeState, update_visible_volume


@dataclass(slots=True)
class AppState:
    player: PlayerState
    visible_volume: VisibleVolumeState
    active_rule: CameraRule
    active_rule_label: str
    debug_visible: bool
    show_volume: bool
    show_lanes: bool
    last_stats: RenderStats


class App:
    def __init__(self) -> None:
        import pyxel

        self.pyxel = pyxel
        pyxel.init(SCREEN_W, SCREEN_H, title="riverside prototype", fps=FPS)
        pyxel.mouse(True)

        self.stage = Stage.create_prototype()
        self.player = create_player()
        self.visible_volume = update_visible_volume(self.player.x)
        self.camera = CameraRig.create()
        self.director = CameraDirector()
        self.input = InputAdapter()
        self.renderer = Renderer.create()
        self.active_rule, self.active_rule_label = self.stage.active_camera_rule(
            self.player.x,
            self.player.target_lane_index,
        )
        self.debug_visible = False
        self.show_volume = False
        self.show_lanes = False
        self.last_stats = RenderStats()
        self.last_rendered_camera_snapshot = self._initial_snapshot()

    def _initial_snapshot(self) -> CameraSnapshot:
        snapshot = make_camera_snapshot(
            self.camera.current_params,
            self.player.x,
            self.player.z,
            shot_id=self.camera.current_shot_id,
        )
        lane_x = compute_lane_screen_x(snapshot, self.player.x)
        stable = update_stable_lane_orientation(1, lane_x)
        return snapshot.with_lane_mapping(lane_x, stable)

    def run(self) -> None:
        self.pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        reset_player(self.player)
        self.visible_volume = update_visible_volume(self.player.x)
        self.camera = CameraRig.create()
        self.director = CameraDirector()
        self.input.pointer.reset()
        self.last_rendered_camera_snapshot = self._initial_snapshot()

    def update(self) -> None:
        pyxel = self.pyxel
        intent = self.input.read(pyxel, self.director.effective_shot, DT)

        if intent.quit_requested:
            pyxel.quit()
            return

        if intent.reset_requested:
            self.reset()
            return

        if intent.debug_toggle_requested:
            self.debug_visible = not self.debug_visible
        if intent.debug_volume_toggle_requested:
            self.show_volume = not self.show_volume
        if intent.debug_lanes_toggle_requested:
            self.show_lanes = not self.show_lanes
        if intent.warp_left_requested:
            warp_player_near_left(self.player)
        if intent.warp_right_requested:
            warp_player_near_right(self.player)

        if intent.lane_screen_step != 0:
            world_step = (
                intent.lane_screen_step
                * self.last_rendered_camera_snapshot.stable_lane_orientation
            )
            change_lane_by_world_step(self.player, world_step)

        update_player(self.player, intent.move_axis, dt=DT)
        self.visible_volume = update_visible_volume(self.player.x)

        self.active_rule, self.active_rule_label = self.stage.active_camera_rule(
            self.player.x,
            self.player.target_lane_index,
        )
        desired_shot = self.director.resolve(
            self.active_rule,
            intent.requested_camera,
            self.camera.current_shot_id,
        )
        self.camera.request_shot(desired_shot)
        self.camera.update(DT)

    def draw(self) -> None:
        pyxel = self.pyxel
        pyxel.cls(palette.BACKGROUND)

        snapshot = make_camera_snapshot(
            self.camera.current_params,
            self.player.x,
            self.player.z,
            lane_screen_x=self.last_rendered_camera_snapshot.lane_screen_x,
            stable_lane_orientation=self.last_rendered_camera_snapshot.stable_lane_orientation,
            shot_id=self.camera.current_shot_id,
        )

        self.last_stats = self.renderer.render(
            pyxel,
            self.stage,
            self.visible_volume,
            self.player,
            snapshot,
            show_volume=self.show_volume,
            show_lanes=self.show_lanes,
        )

        lane_x = compute_lane_screen_x(snapshot, self.player.x)
        stable = update_stable_lane_orientation(
            self.last_rendered_camera_snapshot.stable_lane_orientation,
            lane_x,
        )
        self.last_rendered_camera_snapshot = snapshot.with_lane_mapping(lane_x, stable)

        draw_ui(
            pyxel,
            active_camera=self.director.effective_shot,
            stick_active=self.input.pointer.stick_active,
            stick_offset=(self.input.pointer.drag_x, self.input.pointer.drag_y),
            active_rule_label=self.active_rule_label,
            debug_visible=self.debug_visible,
            show_volume=self.show_volume,
            show_lanes=self.show_lanes,
        )
        if self.debug_visible:
            draw_debug_hud(
                pyxel,
                player=self.player,
                visible_volume=self.visible_volume,
                snapshot=self.last_rendered_camera_snapshot,
                stats=self.last_stats,
                active_rule_label=self.active_rule_label,
                transition_progress=self.camera.transition_progress,
            )


def main() -> None:
    App().run()
