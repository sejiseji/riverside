from __future__ import annotations

from dataclasses import dataclass

from three_line_explorer import palette
from three_line_explorer.camera import (
    CameraRig,
    CameraSnapshot,
    apply_left_edge_camera_blend,
    compute_lane_screen_x,
    compute_lane_screen_y,
    compute_move_screen_x_delta,
    compute_screen_input_axes,
    make_camera_snapshot,
    update_stable_lane_orientation,
    update_stable_move_orientation,
)
from three_line_explorer.camera_director import CameraDirector
from three_line_explorer.config import (
    DT,
    FPS,
    INSPECTION_BODY_FONT_SIZE,
    INSPECTION_TEXT_MAX_LINES,
    INSPECTION_TEXT_MAX_WIDTH,
    PLAYER_SIZE_Y,
    SCREEN_H,
    SCREEN_W,
    VIEWPORT_H,
    VIEWPORT_W,
    VIEWPORT_X,
    VIEWPORT_Y,
)
from three_line_explorer.debug_hud import draw_debug_hud, draw_ui
from three_line_explorer.input import InputAdapter, StickBasis
from three_line_explorer.inspection import (
    InspectableProp,
    InteractionState,
    PromptSnapshot,
    advance_or_close_inspection,
    can_open_prop,
    draw_inspection_panel,
    draw_inspection_prompt,
    find_prop_by_id,
    open_inspection,
    panel_rect,
    prompt_snapshot_for_prop,
    update_active_target,
)
from three_line_explorer.inspection_content_registry import (
    CONTENT_METADATA,
    InspectionContentKind,
)
from three_line_explorer.inspection_texts import INSPECTION_TEXTS
from three_line_explorer.math3d import Vec3
from three_line_explorer.owner_memory_bubble_sprites import (
    animation_frame_index,
    build_owner_memory_bubble_atlas,
    draw_owner_memory_bubble,
)
from three_line_explorer.player import (
    PlayerState,
    create_player,
    player_bounds_at,
    reset_player,
    request_lane_change_by_world_step,
    update_player,
    warp_player_near_left,
    warp_player_near_right,
)
from three_line_explorer.projection import project_world_point
from three_line_explorer.renderer import RenderStats, Renderer
from three_line_explorer.stage import (
    CameraRule,
    Stage,
    make_story_inspectable_prop,
    story_area_index_for_x,
)
from three_line_explorer.story_progression import (
    StoryProgressState,
    activate_next_story_item_if_due,
    mark_story_item_read,
    record_ambient_inspection,
)
from three_line_explorer.text_layout import InspectionTextLayoutCache, create_text_measure
from three_line_explorer.ui_fonts import load_ui_fonts
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
        self.base_inspectable_props = self.stage.inspectable_props
        self.story_progress = StoryProgressState()
        self.active_story_prop_key: str | None = None
        self.player = create_player()
        self.visible_volume = update_visible_volume(self.player.x)
        self.camera = CameraRig.create()
        self.director = CameraDirector()
        self.input = InputAdapter()
        self.renderer = Renderer.create()
        self.owner_memory_atlas = build_owner_memory_bubble_atlas(pyxel)
        self.owner_memory_elapsed = 0
        self.owner_memory_visible = False
        self.active_rule, self.active_rule_label = self.stage.active_camera_rule(
            self.player.x,
            self.player.target_lane_index,
        )
        self.debug_visible = False
        self.show_volume = False
        self.show_lanes = False
        self.interaction = InteractionState()
        self.ui_fonts = load_ui_fonts(pyxel)
        self.inspection_text_cache = InspectionTextLayoutCache(
            INSPECTION_TEXTS,
            INSPECTION_TEXT_MAX_WIDTH,
            INSPECTION_TEXT_MAX_LINES,
            create_text_measure(self.ui_fonts.body, INSPECTION_BODY_FONT_SIZE),
        )
        self.last_stats = RenderStats()
        self.last_rendered_camera_snapshot = self._initial_snapshot()
        self.last_rendered_prompt: PromptSnapshot | None = None
        self.last_stick_basis = self._stick_basis_from_last_render()

    def _initial_snapshot(self) -> CameraSnapshot:
        snapshot = make_camera_snapshot(
            apply_left_edge_camera_blend(self.camera.current_params, self.player.x),
            self.player.x,
            self.player.z,
            shot_id=self.camera.current_shot_id,
        )
        lane_x = compute_lane_screen_x(snapshot, self.player.x)
        lane_y = compute_lane_screen_y(snapshot, self.player.x)
        stable_lane = update_stable_lane_orientation(1, lane_y)
        move_x_delta = compute_move_screen_x_delta(snapshot, self.player.x, self.player.z)
        stable_move = update_stable_move_orientation(1, move_x_delta)
        return snapshot.with_input_mapping(lane_x, lane_y, stable_lane, stable_move)

    def _stick_basis_from_last_render(self) -> StickBasis:
        move_axis, lane_axis = compute_screen_input_axes(
            self.last_rendered_camera_snapshot,
            self.player.x,
            self.player.z,
        )
        return StickBasis(
            move_forward_x=move_axis.x,
            move_forward_y=move_axis.y,
            lane_screen_x=lane_axis.x,
            lane_screen_y=lane_axis.y,
        )

    def run(self) -> None:
        self.pyxel.run(self.update, self.draw)

    def reset(self) -> None:
        reset_player(self.player)
        self.visible_volume = update_visible_volume(self.player.x)
        self.camera = CameraRig.create()
        self.director = CameraDirector()
        self.input.pointer.reset()
        self.interaction = InteractionState()
        self.story_progress = StoryProgressState()
        self.active_story_prop_key = None
        self._apply_story_prop(None)
        self.owner_memory_elapsed = 0
        self.owner_memory_visible = False
        self.last_rendered_camera_snapshot = self._initial_snapshot()
        self.last_rendered_prompt = None

    def update(self) -> None:
        pyxel = self.pyxel
        self.last_stick_basis = self._stick_basis_from_last_render()
        intent = self.input.read(
            pyxel,
            self.director.effective_shot,
            DT,
            self.last_stick_basis,
            prompt_snapshot=self.last_rendered_prompt,
            panel_open=self.interaction.panel_open,
            panel_rect=panel_rect(),
        )

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

        if self.interaction.panel_open:
            self.player.velocity_x = 0.0
            self.player.last_move_distance = 0.0
            if intent.text_panel_advance_requested:
                closed_text_key = advance_or_close_inspection(self.interaction)
                if closed_text_key is not None:
                    self._handle_inspection_closed(closed_text_key)
            if self.interaction.panel_open and self.owner_memory_visible:
                self.owner_memory_elapsed += 1
            self.camera.update(DT)
            return

        if intent.inspection_prompt_object_id is not None:
            self._try_open_inspection(intent.inspection_prompt_object_id)
            self.player.velocity_x = 0.0
            self.player.last_move_distance = 0.0
            self.camera.update(DT)
            return

        if intent.lane_screen_step != 0:
            world_step = (
                intent.lane_screen_step
                * self.last_rendered_camera_snapshot.stable_lane_orientation
            )
            request_lane_change_by_world_step(self.player, world_step)

        update_player(
            self.player,
            intent.move_axis,
            dt=DT,
            collision_provider=self.stage.candidate_collision_solids,
        )
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
        self._sync_story_prop()
        update_active_target(
            self.interaction,
            player_bounds_at(self.player.x, self.player.z),
            self.stage.inspectable_props,
        )

    def _try_open_inspection(self, object_id: str) -> None:
        prop = find_prop_by_id(self.stage.inspectable_props, object_id)
        if prop is None:
            return
        if not can_open_prop(player_bounds_at(self.player.x, self.player.z), prop):
            return
        if open_inspection(self.interaction, prop, self.inspection_text_cache):
            metadata = CONTENT_METADATA.get(prop.text_key)
            self.owner_memory_elapsed = 0
            self.owner_memory_visible = (
                metadata is not None
                and metadata.kind
                in {InspectionContentKind.OWNER_LETTER, InspectionContentKind.MEMORY_ECHO}
            )

    def _handle_inspection_closed(self, text_key: str) -> None:
        metadata = CONTENT_METADATA.get(text_key)
        self.owner_memory_visible = False
        self.owner_memory_elapsed = 0
        if metadata is None:
            return
        if metadata.kind is InspectionContentKind.AMBIENT:
            record_ambient_inspection(self.story_progress)
        else:
            mark_story_item_read(self.story_progress, content_id=text_key)
        self._sync_story_prop()

    def _sync_story_prop(self) -> None:
        story_item = activate_next_story_item_if_due(
            self.story_progress,
            area_index=story_area_index_for_x(self.player.x),
        )
        if story_item is None:
            self._apply_story_prop(None)
            return
        if self.active_story_prop_key == story_item.content_id:
            return
        self._apply_story_prop(
            make_story_inspectable_prop(
                story_item,
                player_x=self.player.x,
            )
        )

    def _apply_story_prop(self, prop: InspectableProp | None) -> None:
        self.active_story_prop_key = None if prop is None else prop.text_key
        self.stage.inspectable_props = (
            self.base_inspectable_props
            if prop is None
            else (*self.base_inspectable_props, prop)
        )
        self.stage.rebuild_chunks()

    def draw(self) -> None:
        pyxel = self.pyxel
        pyxel.cls(palette.BACKGROUND)

        snapshot = make_camera_snapshot(
            apply_left_edge_camera_blend(self.camera.current_params, self.player.x),
            self.player.x,
            self.player.z,
            lane_screen_x=self.last_rendered_camera_snapshot.lane_screen_x,
            lane_screen_y=self.last_rendered_camera_snapshot.lane_screen_y,
            stable_lane_orientation=self.last_rendered_camera_snapshot.stable_lane_orientation,
            stable_move_orientation=self.last_rendered_camera_snapshot.stable_move_orientation,
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
        self.last_rendered_prompt = None

        lane_x = compute_lane_screen_x(snapshot, self.player.x)
        lane_y = compute_lane_screen_y(snapshot, self.player.x)
        stable = update_stable_lane_orientation(
            self.last_rendered_camera_snapshot.stable_lane_orientation,
            lane_y,
        )
        move_x_delta = compute_move_screen_x_delta(snapshot, self.player.x, self.player.z)
        stable_move = update_stable_move_orientation(
            self.last_rendered_camera_snapshot.stable_move_orientation,
            move_x_delta,
        )
        self.last_rendered_camera_snapshot = snapshot.with_input_mapping(
            lane_x,
            lane_y,
            stable,
            stable_move,
        )

        if not self.interaction.panel_open:
            prompt = self._draw_active_inspection_prompt(snapshot)
            self.last_rendered_prompt = prompt
        elif self.owner_memory_visible:
            self._draw_owner_memory_bubble(snapshot)

        draw_ui(
            pyxel,
            active_camera=self.director.effective_shot,
            stick_active=self.input.pointer.stick_active,
            stick_offset=(self.input.pointer.drag_x, self.input.pointer.drag_y),
            stick_basis=self.last_stick_basis,
            active_rule_label=self.active_rule_label,
            debug_visible=self.debug_visible,
            show_volume=self.show_volume,
            show_lanes=self.show_lanes,
            bottom_controls_visible=not self.interaction.panel_open,
        )
        if self.interaction.panel_open:
            draw_inspection_panel(pyxel, self.interaction, self.ui_fonts)
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

    def _draw_active_inspection_prompt(
        self,
        snapshot: CameraSnapshot,
    ) -> PromptSnapshot | None:
        prop = find_prop_by_id(
            self.stage.inspectable_props,
            self.interaction.active_target_id,
        )
        if prop is None:
            return None
        prompt = prompt_snapshot_for_prop(prop, snapshot, self.visible_volume.bounds)
        if prompt is None:
            return None
        draw_inspection_prompt(self.pyxel, prompt)
        return prompt

    def _draw_owner_memory_bubble(self, snapshot: CameraSnapshot) -> None:
        head = project_world_point(
            snapshot,
            Vec3(self.player.x, PLAYER_SIZE_Y + 5.0, self.player.z),
        )
        if head is None:
            return
        pyxel = self.pyxel
        pyxel.clip(VIEWPORT_X, VIEWPORT_Y, VIEWPORT_W, VIEWPORT_H)
        draw_owner_memory_bubble(
            self.owner_memory_atlas,
            frame_index=animation_frame_index(self.owner_memory_elapsed),
            cat_head_screen_x=head.x,
            cat_head_screen_y=head.y,
        )
        pyxel.clip()


def main() -> None:
    App().run()
