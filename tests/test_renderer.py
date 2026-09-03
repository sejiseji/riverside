from __future__ import annotations

from unittest import TestCase

from three_line_explorer import palette
from three_line_explorer.camera import CAMERA_SHOTS, make_camera_snapshot
from three_line_explorer.config import (
    ENVIRONMENT_OBJECT_ID_BASE,
    FLOOR_OBJECT_ID,
    INSPECTABLE_OBJECT_ID_BASE,
    PLAYER_OBJECT_ID,
    PLAYER_SHADOW_OBJECT_ID,
    PLAYER_SHADOW_FRAME_SCALE_X,
    PLAYER_SHADOW_SEGMENTS,
    PLAYER_SHADOW_SIZE_X,
    RIVER_OBJECT_ID,
    SCENE_RENDER_FAR_MARGIN_Z,
    SCENE_RENDER_MARGIN_X,
    CameraShotId,
    RenderLayer,
)
from three_line_explorer.environment_sprites import (
    EnvironmentSpriteAtlas,
    EnvironmentSpriteRegion,
)
from three_line_explorer.inspection_prop_sprites import (
    PropSpriteAtlas,
    SpriteRegion,
    PropSpriteId,
)
from three_line_explorer.geometry import AabbSolid
from three_line_explorer.math3d import AABB, Vec3
from three_line_explorer.player import create_player
from three_line_explorer.renderer import (
    Renderer,
    _face_sort_depth,
    _object_sort_depths,
    _render_sprite_sort_key,
    make_player_shadow_face,
    render_scene_bounds,
)
from three_line_explorer.stage import Stage
from three_line_explorer.visible_volume import update_visible_volume


class RendererTests(TestCase):
    def test_face_sort_depth_uses_nearest_point(self) -> None:
        points = (
            Vec3(0.0, 0.0, 40.0),
            Vec3(0.0, 0.0, 10.0),
            Vec3(0.0, 0.0, 20.0),
            Vec3(0.0, 0.0, 30.0),
        )

        self.assertEqual(_face_sort_depth(points), 10.0)

    def test_ground_faces_are_split_into_walkway_and_river(self) -> None:
        renderer = Renderer.create()
        player = create_player()
        snapshot = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], player.x, player.z)

        renderer.build_scene(
            Stage(solids=(), zones=()),
            update_visible_volume(player.x),
            player,
            snapshot,
            show_volume=False,
            show_lanes=False,
        )

        ground_faces = {
            face.object_id: face.fill_color
            for face in renderer.render_faces
            if face.object_id in {FLOOR_OBJECT_ID, RIVER_OBJECT_ID}
        }
        self.assertEqual(ground_faces[FLOOR_OBJECT_ID], palette.FLOOR_FILL)
        self.assertEqual(ground_faces[RIVER_OBJECT_ID], palette.RIVER_FILL)

    def test_render_scene_bounds_expand_x_and_far_z_from_right_side_camera(self) -> None:
        logical = update_visible_volume(0.0).bounds
        snapshot = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], 0.0, 0.0)

        expanded = render_scene_bounds(logical, snapshot)

        self.assertEqual(expanded.minimum.x, logical.minimum.x - SCENE_RENDER_MARGIN_X)
        self.assertEqual(expanded.maximum.x, logical.maximum.x + SCENE_RENDER_MARGIN_X)
        self.assertEqual(expanded.minimum.z, logical.minimum.z - SCENE_RENDER_FAR_MARGIN_Z)
        self.assertEqual(expanded.maximum.z, logical.maximum.z)

    def test_render_scene_bounds_expand_far_z_from_left_side_camera(self) -> None:
        logical = update_visible_volume(0.0).bounds
        snapshot = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_LEFT_SHALLOW], 0.0, 0.0)

        expanded = render_scene_bounds(logical, snapshot)

        self.assertEqual(expanded.minimum.x, logical.minimum.x - SCENE_RENDER_MARGIN_X)
        self.assertEqual(expanded.maximum.x, logical.maximum.x + SCENE_RENDER_MARGIN_X)
        self.assertEqual(expanded.minimum.z, logical.minimum.z)
        self.assertEqual(expanded.maximum.z, logical.maximum.z + SCENE_RENDER_FAR_MARGIN_Z)

    def test_render_scene_uses_expanded_bounds_for_solid_candidates(self) -> None:
        renderer = Renderer.create()
        player = create_player()
        logical = update_visible_volume(player.x).bounds
        solid = AabbSolid(
            object_id=900,
            bounds=AABB(
                Vec3(logical.maximum.x + 24.0, 0.0, -12.0),
                Vec3(logical.maximum.x + 44.0, 30.0, 4.0),
            ),
            side_color=4,
            top_color=12,
            outline_color=0,
        )
        stage = Stage(solids=(solid,), zones=())
        stage.rebuild_chunks()
        snapshot = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], player.x, player.z)

        renderer.build_scene(
            stage,
            update_visible_volume(player.x),
            player,
            snapshot,
            show_volume=False,
            show_lanes=False,
        )

        self.assertIn(900, {face.object_id for face in renderer.render_faces})

    def test_player_shadow_is_projected_on_floor_before_player_sprite(self) -> None:
        renderer = Renderer.create()
        player = create_player()
        snapshot = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], player.x, player.z)

        renderer.build_scene(
            Stage(solids=(), zones=()),
            update_visible_volume(player.x),
            player,
            snapshot,
            show_volume=False,
            show_lanes=False,
        )

        shadow = next(face for face in renderer.render_faces if face.object_id == PLAYER_SHADOW_OBJECT_ID)
        player_sprite = next(sprite for sprite in renderer.render_sprites if sprite.object_id == PLAYER_OBJECT_ID)
        self.assertEqual(shadow.layer, RenderLayer.FLOOR_GUIDE)
        self.assertEqual(player_sprite.layer, RenderLayer.SOLID)
        self.assertEqual(shadow.fill_color, palette.PLAYER_SHADOW)
        self.assertEqual(len(shadow.points), PLAYER_SHADOW_SEGMENTS)

    def test_player_shadow_shape_is_elliptical_and_tracks_walk_frame(self) -> None:
        player = create_player()
        idle_shadow = make_player_shadow_face(player)
        player.last_move_distance = 1.0
        player.walk_phase = 2.0
        moving_shadow = make_player_shadow_face(player)

        idle_radius_x = idle_shadow.vertices[0].x - idle_shadow.center.x
        moving_radius_x = moving_shadow.vertices[0].x - moving_shadow.center.x
        self.assertEqual(len(idle_shadow.vertices), PLAYER_SHADOW_SEGMENTS)
        self.assertAlmostEqual(idle_radius_x, PLAYER_SHADOW_SIZE_X * 0.5)
        self.assertAlmostEqual(
            moving_radius_x,
            PLAYER_SHADOW_SIZE_X * 0.5 * PLAYER_SHADOW_FRAME_SCALE_X[2],
        )
        self.assertGreater(moving_radius_x, idle_radius_x)

    def test_inspectable_props_are_rendered_as_sprites_outside_collision_solids(self) -> None:
        renderer = Renderer.create()
        renderer.prop_sprite_atlas = make_fake_prop_atlas()
        player = create_player()
        stage = Stage.create_prototype()
        snapshot = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], player.x, player.z)

        renderer.build_scene(
            stage,
            update_visible_volume(player.x),
            player,
            snapshot,
            show_volume=False,
            show_lanes=False,
        )

        object_ids = {sprite.object_id for sprite in renderer.render_sprites}
        self.assertIn(INSPECTABLE_OBJECT_ID_BASE + 1, object_ids)
        self.assertNotIn(INSPECTABLE_OBJECT_ID_BASE + 1, {solid.object_id for solid in stage.solids})
        self.assertNotIn(
            INSPECTABLE_OBJECT_ID_BASE + 1,
            {face.object_id for face in renderer.render_faces},
        )

    def test_environment_sprites_are_rendered_without_aabb_faces(self) -> None:
        renderer = Renderer.create()
        renderer.environment_sprite_atlas = make_fake_environment_atlas()
        player = create_player()
        player.x = -198.0
        stage = Stage.create_prototype()
        snapshot = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], player.x, player.z)

        renderer.build_scene(
            stage,
            update_visible_volume(player.x),
            player,
            snapshot,
            show_volume=False,
            show_lanes=False,
        )

        object_ids = {sprite.object_id for sprite in renderer.render_sprites}
        self.assertIn(ENVIRONMENT_OBJECT_ID_BASE + 3, object_ids)
        self.assertNotIn(
            ENVIRONMENT_OBJECT_ID_BASE + 3,
            {face.object_id for face in renderer.render_faces},
        )

    def test_sprite_sort_key_uses_depth_before_object_id(self) -> None:
        renderer = Renderer.create()
        renderer.prop_sprite_atlas = make_fake_prop_atlas()
        player = create_player()
        stage = Stage.create_prototype()
        snapshot = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], player.x, player.z)

        renderer.build_scene(
            stage,
            update_visible_volume(player.x),
            player,
            snapshot,
            show_volume=False,
            show_lanes=False,
        )

        player_sprite = next(sprite for sprite in renderer.render_sprites if sprite.object_id == PLAYER_OBJECT_ID)
        prop_sprite = next(
            sprite
            for sprite in renderer.render_sprites
            if sprite.object_id == INSPECTABLE_OBJECT_ID_BASE + 1
        )
        prop_key = _render_sprite_sort_key(prop_sprite)
        player_key = _render_sprite_sort_key(player_sprite)
        self.assertEqual(prop_key[1], -prop_sprite.lane_depth)
        self.assertEqual(player_key[1], -player_sprite.lane_depth)
        self.assertEqual(prop_key[2], -prop_sprite.route_depth)
        self.assertEqual(player_key[2], -player_sprite.route_depth)
        self.assertEqual(prop_key[3], -prop_sprite.depth)
        self.assertEqual(player_key[3], -player_sprite.depth)
        self.assertEqual(prop_key[4], prop_sprite.object_id)
        self.assertEqual(player_key[4], player_sprite.object_id)

    def test_object_sort_depths_follow_camera_line_depth(self) -> None:
        shot_a = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], 0.0, 0.0)
        negative_z_depth, _ = _object_sort_depths(Vec3(0.0, 0.0, -36.0), shot_a)
        positive_z_depth, _ = _object_sort_depths(Vec3(0.0, 0.0, 36.0), shot_a)
        self.assertGreater(negative_z_depth, positive_z_depth)

        shot_b = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.FRONT_RIGHT_CLOSE], 0.0, 0.0)
        negative_z_depth, _ = _object_sort_depths(Vec3(0.0, 0.0, -36.0), shot_b)
        positive_z_depth, _ = _object_sort_depths(Vec3(0.0, 0.0, 36.0), shot_b)
        self.assertGreater(negative_z_depth, positive_z_depth)

        shot_c = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_LEFT_SHALLOW], 0.0, 0.0)
        negative_z_depth, _ = _object_sort_depths(Vec3(0.0, 0.0, -36.0), shot_c)
        positive_z_depth, _ = _object_sort_depths(Vec3(0.0, 0.0, 36.0), shot_c)
        self.assertGreater(positive_z_depth, negative_z_depth)

    def test_object_sort_depths_follow_camera_route_depth(self) -> None:
        shot_a = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_RIGHT_LOW], 0.0, 0.0)
        _, negative_x_depth = _object_sort_depths(Vec3(-40.0, 0.0, 0.0), shot_a)
        _, positive_x_depth = _object_sort_depths(Vec3(40.0, 0.0, 0.0), shot_a)
        self.assertGreater(positive_x_depth, negative_x_depth)

        shot_b = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.FRONT_RIGHT_CLOSE], 0.0, 0.0)
        _, negative_x_depth = _object_sort_depths(Vec3(-40.0, 0.0, 0.0), shot_b)
        _, positive_x_depth = _object_sort_depths(Vec3(40.0, 0.0, 0.0), shot_b)
        self.assertGreater(negative_x_depth, positive_x_depth)

        shot_c = make_camera_snapshot(CAMERA_SHOTS[CameraShotId.REAR_LEFT_SHALLOW], 0.0, 0.0)
        _, negative_x_depth = _object_sort_depths(Vec3(-40.0, 0.0, 0.0), shot_c)
        _, positive_x_depth = _object_sort_depths(Vec3(40.0, 0.0, 0.0), shot_c)
        self.assertGreater(positive_x_depth, negative_x_depth)


def make_fake_prop_atlas() -> PropSpriteAtlas:
    return PropSpriteAtlas(
        image=object(),
        regions={
            sprite_id: SpriteRegion(
                u=index * 32,
                v=0,
                width=32,
                height=24,
                anchor_x=16,
                anchor_y=23,
                world_width=20.0,
            )
            for index, sprite_id in enumerate(PropSpriteId)
        },
    )


def make_fake_environment_atlas() -> EnvironmentSpriteAtlas:
    return EnvironmentSpriteAtlas(
        image=object(),
        regions={
            sprite_id: EnvironmentSpriteRegion(
                u=index * 16,
                v=0,
                width=16,
                height=16,
                anchor_x=8,
                anchor_y=15,
                world_width=12.0,
                colkey=8,
                depth_bias=0.0,
            )
            for index, sprite_id in enumerate(
                sprite.sprite_id for sprite in Stage.create_prototype().environment_sprites
            )
        },
    )
