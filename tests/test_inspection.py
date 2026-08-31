from __future__ import annotations

from unittest import TestCase

from three_line_explorer.camera import CAMERA_SHOTS, make_camera_snapshot
from three_line_explorer.config import CameraShotId, LANE_Z, RIVER_START_Z
from three_line_explorer.inspection import (
    INSPECTION_TEXTS,
    InspectableProp,
    InteractionState,
    advance_or_close_inspection,
    current_page,
    marker_world_position,
    open_inspection,
    prompt_snapshot_for_prop,
    update_active_target,
)
from three_line_explorer.math3d import AABB, Vec3
from three_line_explorer.player import player_bounds_at
from three_line_explorer.stage import Stage
from three_line_explorer.visible_volume import update_visible_volume


class InspectionTests(TestCase):
    def test_river_side_lane_can_acquire_prop_but_center_lane_cannot(self) -> None:
        stage = Stage.create_prototype()
        state = InteractionState()

        update_active_target(
            state,
            player_bounds_at(78.0, LANE_Z[1]),
            stage.inspectable_props,
        )
        self.assertIsNone(state.active_target_id)

        update_active_target(
            state,
            player_bounds_at(78.0, LANE_Z[2]),
            stage.inspectable_props,
        )
        self.assertEqual(state.active_target_id, "river_prop_001")

    def test_active_prop_uses_release_padding_as_hysteresis(self) -> None:
        stage = Stage.create_prototype()
        state = InteractionState(active_target_id="river_prop_001")

        update_active_target(
            state,
            player_bounds_at(78.0, 21.0),
            stage.inspectable_props,
        )
        self.assertEqual(state.active_target_id, "river_prop_001")

        update_active_target(
            state,
            player_bounds_at(78.0, 20.0),
            stage.inspectable_props,
        )
        self.assertIsNone(state.active_target_id)

    def test_nearest_target_ties_are_stable_by_object_id(self) -> None:
        props = (
            InspectableProp(
                object_id="b_prop",
                render_object_id=100,
                bounds=AABB(Vec3(40.0, 0.0, 48.0), Vec3(48.0, 4.0, 56.0)),
                text_key="single_sandal",
            ),
            InspectableProp(
                object_id="a_prop",
                render_object_id=101,
                bounds=AABB(Vec3(40.0, 0.0, 48.0), Vec3(48.0, 4.0, 56.0)),
                text_key="single_sandal",
            ),
        )
        state = InteractionState()

        update_active_target(state, player_bounds_at(42.0, LANE_Z[2]), props)

        self.assertEqual(state.active_target_id, "a_prop")

    def test_marker_uses_top_center_plus_height(self) -> None:
        prop = Stage.create_prototype().inspectable_props[0]

        marker = marker_world_position(prop)

        self.assertEqual(marker.x, 78.0)
        self.assertEqual(marker.y, 13.0)
        self.assertEqual(marker.z, RIVER_START_Z + 8.0)

    def test_prompt_snapshot_projects_active_prop_to_hitbox(self) -> None:
        prop = Stage.create_prototype().inspectable_props[0]
        snapshot = make_camera_snapshot(
            CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW],
            78.0,
            LANE_Z[2],
        )
        volume = update_visible_volume(78.0)

        prompt = prompt_snapshot_for_prop(prop, snapshot, volume.bounds)

        self.assertIsNotNone(prompt)
        assert prompt is not None
        self.assertTrue(prompt.visible)
        self.assertTrue(
            prompt.hitbox.contains(
                prompt.hitbox.x + prompt.hitbox.width // 2,
                prompt.hitbox.y + prompt.hitbox.height // 2,
            )
        )

    def test_panel_opens_advances_and_closes(self) -> None:
        prop = Stage.create_prototype().inspectable_props[0]
        state = InteractionState()

        self.assertTrue(open_inspection(state, prop, INSPECTION_TEXTS))
        self.assertTrue(state.panel_open)
        self.assertIn(prop.object_id, state.inspected_ids)
        page = current_page(state)
        self.assertIsNotNone(page)
        assert page is not None
        self.assertEqual(page.title, "Single sandal")

        advance_or_close_inspection(state)
        self.assertTrue(state.panel_open)
        self.assertEqual(state.page_index, 1)

        advance_or_close_inspection(state)
        self.assertFalse(state.panel_open)
