# Riverside Current Camera And Rendering Pipeline

Baseline: post-`301093f` rendering-contract pass

This document describes the current implementation contract for camera shots,
camera transitions, screen projection, scale calculation, render ordering, and
per-object drawing. It is intended as a handoff document for future gameplay,
camera, and asset work.

## Coordinate And Viewport Contract

- Logical screen: `393 x 852`
- 3D viewport: `x=0`, `y=56`, `w=393`, `h=716`
- Top UI height: `56`
- Bottom UI height: `80`
- World axes:
  - `+X`: stage route direction
  - `+Y`: up
  - `+Z`: river side / lane crossing direction
- Ground plane: `GROUND_Y = 0.0`
- Walk lanes: `LANE_Z = (-36.0, 0.0, 36.0)`
- River starts at `RIVER_START_Z = LANE_Z[-1] + PLAYER_SIZE_Z * 0.5 = 44.0`
- Stage bounds:
  - `X = -720.0 .. 720.0`
  - `Y = 0.0 .. 100.0`
  - `Z = -60.0 .. 180.0`

## Camera Parameters

Camera parameters are stored in `CameraParameters`:

```python
azimuth: float
elevation: float
distance: float
target_y: float
```

The camera position is always derived from the current player position and the
current evaluated parameters:

```python
pivot = Vec3(player_x, target_y, player_z)
horizontal = distance * cos(elevation)
offset = Vec3(
    horizontal * cos(azimuth),
    distance * sin(elevation),
    horizontal * sin(azimuth),
)
position = pivot + offset
```

The camera always looks at `pivot`. There is no camera follow lag.

Current shots:

| Shot id | Azimuth | Elevation | Distance | Target Y |
| --- | ---: | ---: | ---: | ---: |
| `REAR_RIGHT_LOW` | 110 deg | 12 deg | 640 | 18 |
| `FRONT_RIGHT_CLOSE` | 70 deg | 14 deg | 520 | 18 |
| `REAR_LEFT_SHALLOW` | 240 deg | 6 deg | 700 | 18 |
| `RIGHT_SIDE_WIDE` | 92 deg | 8 deg | 760 | 18 |

Initial shot: `REAR_RIGHT_LOW`.

## Camera Transition

Manual or stage-driven shot changes call `CameraRig.request_shot(shot_id)`.

- Transition duration: `0.85` seconds
- Easing: `smootherstep`
- Interpolated fields:
  - `azimuth` via shortest-angle interpolation
  - `elevation`
  - `distance`
  - `target_y`
- The camera world position is not interpolated directly.
- Each frame, the interpolated offset is recomputed from the current player
  position, so the camera remains attached while the player moves.
- If another shot is requested mid-transition, the current evaluated parameters
  become the new transition start.

## Stage Camera Rules

`CameraDirector.resolve()` applies camera intent in this priority:

1. `forced_shot`
2. manual request, if `manual_enabled` and the requested shot is allowed
3. `last_manual_shot`, if still allowed
4. current effective shot, if still allowed
5. nearest allowed shot
6. stage default shot

Current prototype zones:

| X range | Rule |
| --- | --- |
| `140.0 .. STAGE_MAX_X` | force `FRONT_RIGHT_CLOSE`, manual disabled |
| `-260.0 .. -160.0` | allow `REAR_RIGHT_LOW`, `REAR_LEFT_SHALLOW`, `RIGHT_SIDE_WIDE` |

## Left Edge Camera Blend

Near the left stage edge, the current shot parameters are blended toward a
close camera target before creating the snapshot.

- Blend start: `x = -260.0`
- Blend end: `x = STAGE_MIN_X = -720.0`
- Target azimuth: `125 deg`
- Target elevation: `7 deg`
- Target distance: `340`
- Target Y: `18`

Blend factor:

```python
raw_t = (LEFT_EDGE_CAMERA_BLEND_START_X - player_x) / (
    LEFT_EDGE_CAMERA_BLEND_START_X - LEFT_EDGE_CAMERA_BLEND_END_X
)
blend = smootherstep(raw_t)
```

This is the current "zoom in while approaching the left edge" behavior. The cat
appears larger because camera distance becomes smaller and sprite scale is based
on projected world width.

## Camera Snapshot And Projection

`make_camera_snapshot()` produces:

- `position`
- `pivot`
- `forward`
- `right`
- `up`
- `focal_px`
- `screen_center_x`
- `screen_center_y`
- last stable input mappings

Camera basis:

```python
forward = normalize(pivot - position)
right = normalize(cross(forward, WORLD_UP))
up = normalize(cross(right, forward))
```

Focal length:

```python
focal_px = (VIEWPORT_W * 0.5) / tan(HORIZONTAL_FOV * 0.5)
```

Horizontal FOV is `38 deg`.

World-to-camera:

```python
relative = point - camera.position
camera_x = dot(relative, right)
camera_y = dot(relative, up)
camera_z = dot(relative, forward)
```

Projection:

```python
screen_x = screen_center_x + focal_px * camera_x / camera_z
screen_y = screen_center_y - focal_px * camera_y / camera_z
```

Near plane:

- `NEAR_PLANE = 4.0`
- Points at or behind the near plane are not drawn.
- Polygons and lines are near-clipped before projection.

## Frame Order

Update:

1. Read input using the last rendered camera and prompt snapshots.
2. Handle quit, reset, debug toggles, and warps.
3. If inspection panel is open, stop player movement and update only panel and
   camera transition.
4. If inspection prompt was tapped, open panel, stop player movement, and update
   camera transition.
5. Convert lane screen step using `last_rendered_camera_snapshot.stable_lane_orientation`.
6. Update player movement, facing, lane interpolation, collision, and walk phase.
7. Update visible volume from player X.
8. Resolve stage camera rule and requested camera.
9. Update camera transition.
10. Sync story prop and active inspection target.

Draw:

1. Build current camera snapshot from camera parameters plus left-edge blend.
2. Renderer builds floor, solids, sprites, player shadow, player, debug lines.
3. Clip to 3D viewport.
4. Draw parallax background.
5. Sort and draw render faces and render sprites together.
6. Draw debug/world lines.
7. Clear clip.
8. Save lane/input camera mapping for the next update.
9. Draw inspection prompt or owner memory bubble.
10. Draw UI, panel, and debug HUD.

## Render Bounds

The logical visible volume follows the player in X and clamps at stage edges:

```python
center_x = clamp(player_x, STAGE_MIN_X + 90, STAGE_MAX_X - 90)
visible_bounds = AABB(
    Vec3(center_x - 90, 0, STAGE_MIN_Z),
    Vec3(center_x + 90, STAGE_MAX_Y, STAGE_MAX_Z),
)
```

For visual rendering, this is expanded:

- X margin: `SCENE_RENDER_MARGIN_X = 240.0`
- Far Z margin: `SCENE_RENDER_FAR_MARGIN_Z = 120.0`

Far Z direction depends on camera side:

```python
if snapshot.position.z >= snapshot.pivot.z:
    far edge is visible_bounds.minimum.z
else:
    far edge is visible_bounds.maximum.z
```

This allows stage, river, and far-side objects to begin rendering before their
logical visible-volume boundary reaches the screen.

## Shared Render Sorting

Solid faces and sprites are put into one combined render stream.

Face key:

```python
(layer, -depth, object_id, face_index, 0, 0)
```

Sprite key:

```python
(layer, -depth, object_id, 0, 0, 0)
```

Primary depth is camera-space depth. Larger camera depth is farther away and
drawn first:

```python
depth = dot(world_point - snapshot.position, snapshot.forward)
```

`lane_depth` and `route_depth` are still stored on sprite/face records for
debugging and future tuning, but they are no longer the leading sort keys.
This is still a painter sort, not a pixel Z-buffer. Large intersecting objects
can still need manual splitting.

Render layers:

| Layer | Value | Main contents |
| --- | ---: | --- |
| `BACKGROUND` | 0 | viewport background fill |
| `FLOOR` | 10 | walkway and river faces |
| `FLOOR_GUIDE` | 20 | player shadow, debug lane lines |
| `SOLID` | 30 | AABB solids, player, props, environment sprites |
| `DEBUG_VOLUME` | 40 | visible-volume edges |
| `HUD` | 100 | top/bottom UI, panels, debug HUD |

## Object: Walkway Floor

Source:

- Generated each frame from current render bounds.
- Bounds are split at `RIVER_START_Z`.

World geometry:

```python
walkway_bounds = AABB(
    Vec3(render_min_x, GROUND_Y, render_min_z),
    Vec3(render_max_x, GROUND_Y, min(render_max_z, RIVER_START_Z)),
)
```

Rendering:

- Converted to one quad face.
- Split into triangles in `_draw_face()`.
- Uses perspective projection from vertices.
- No sprite scale is used.
- Layer: `FLOOR`
- Object id: `FLOOR_OBJECT_ID`

## Object: River Surface

Source:

- Generated each frame from current render bounds.
- Starts at `RIVER_START_Z = 44.0`.

World geometry:

```python
river_bounds = AABB(
    Vec3(render_min_x, GROUND_Y, max(render_min_z, RIVER_START_Z)),
    Vec3(render_max_x, GROUND_Y, render_max_z),
)
```

Rendering:

- Same quad/triangle path as walkway.
- Uses perspective projection from vertices.
- No sprite scale is used.
- Layer: `FLOOR`
- Object id: `RIVER_OBJECT_ID`

## Object: Static AABB Solids

Source:

- Stage solids in `Stage.solids`
- Candidates are selected by X chunks and intersection with `render_bounds`.

Geometry:

- If fully inside `render_bounds`, cached faces are reused.
- If partially crossing `render_bounds`, `intersect_aabb()` creates a clipped
  AABB and faces are generated from that clipped box.
- Faces are backface-culled before projection:

```python
visible = dot(face.normal, snapshot.position - face.center) > CULL_EPSILON
```

Rendering:

- Camera-space near clipping is applied per polygon.
- Projection is per vertex.
- No sprite scale is used.
- Layer: `SOLID`
- Drawn by `_draw_face()` with filled triangles and per-face outline.

## Shared Scaled Sprite Anchor

Scaled sprite placement uses the helper in `blit_anchor.py`.

Pyxel `blt(..., scale=s)` scales around the source rectangle center, not around
the top-left corner. For a desired screen anchor `P`, source-space anchor `A`,
and source center `C = ((w - 1) / 2, (h - 1) / 2)`, the destination origin `D`
is:

```python
D = P - C - scale * (A - C)
```

Runtime implementation:

```python
draw_x = round(screen_x - center_x - scale * (anchor_x - center_x))
draw_y = round(screen_y - center_y - scale * (anchor_y - center_y))
```

This same calculation is used for:

- player sprites
- drift / inspectable prop sprites
- environment world sprites
- projected parallax tiles

## Object: Player Sprite

World anchor:

```python
anchor_world = Vec3(player.x, GROUND_Y, player.z)
```

Projected anchor:

```python
camera_point = world_to_camera(snapshot, anchor_world)
projected = project_camera_point(snapshot, camera_point)
```

Sprite source:

- Preferred asset: `assets/player_sprites.pyxres`
- Fallback: `player_sprite_data.py`
- Frame size: `48 x 64`
- Directions: front, right, left, back
- Frames: 4
- Transparent color: `2`

Direction row comes from `player.render_yaw` and the current rendered camera
snapshot. The player's logical/world facing is not changed by the camera; only
the selected sprite row changes according to the camera-relative view angle.

Animation:

- Idle: frame `0`
- Moving: `int(player.walk_phase) % 4`
- `walk_phase` advances from actual X/Z movement distance, not `frame_count`.

Scale:

```python
projected_width = snapshot.focal_px * PLAYER_SPRITE_WORLD_WIDTH / camera_point.z
scale = clamp(projected_width / source_width, 0.85, 1.65)
```

Current values:

- `PLAYER_SPRITE_WORLD_WIDTH = 26.0`
- `PLAYER_SPRITE_MIN_SCALE = 0.85`
- `PLAYER_SPRITE_MAX_SCALE = 1.65`
- `source_width = 48`

Screen placement:

```python
draw_x, draw_y = anchored_blt_origin(
    screen_x=projected.x,
    screen_y=projected.y,
    width=48,
    height=64,
    anchor_x=PLAYER_SPRITE_ANCHOR_X,
    anchor_y=PLAYER_SPRITE_ANCHOR_Y,
    scale=scale,
)
```

Current anchor:

- `PLAYER_SPRITE_ANCHOR_X = 24.0`
- `PLAYER_SPRITE_ANCHOR_Y = 60.0`
- Head attachment: `PLAYER_SPRITE_HEAD_ANCHOR_X = 24.0`,
  `PLAYER_SPRITE_HEAD_ANCHOR_Y = 13.0`

Rendering:

- Render item type: `RenderSprite`
- Layer: `SOLID`
- Object id: `PLAYER_OBJECT_ID`
- Draw call: `pyxel.blt(..., scale=scale, colkey=2)`

## Object: Player Shadow

The player shadow is a projected world-floor ellipse. It shares the same ground
contact center as the player sprite:

```python
center = Vec3(player.x, GROUND_Y + PLAYER_SHADOW_Y, player.z)
```

Radii are in world units and are modulated by the current walk frame:

```python
radius_x = PLAYER_SHADOW_SIZE_X * 0.5 * frame_scale_x
radius_z = PLAYER_SHADOW_SIZE_Z * 0.5 * frame_scale_z
```

Current values:

- `PLAYER_SHADOW_SIZE_X = 22.0`
- `PLAYER_SHADOW_SIZE_Z = 12.0`
- `PLAYER_SHADOW_Y = 0.06`
- `PLAYER_SHADOW_SEGMENTS = 14`
- `PLAYER_SHADOW_FRAME_SCALE_X = (1.0, 0.94, 1.05, 0.94)`
- `PLAYER_SHADOW_FRAME_SCALE_Z = (1.0, 1.04, 0.96, 1.04)`

Rendering:

- Generated by `make_player_shadow_face(player)`.
- Projected and near-clipped through the same face path as floor geometry.
- Layer: `FLOOR_GUIDE`
- Object id: `PLAYER_SHADOW_OBJECT_ID`
- Drawn by `_draw_face()` as filled triangles.
- No screen-space Y correction is applied.

## Object: Drift / Inspectable Prop Sprite

World anchor:

```python
anchor_world = Vec3(
    (bounds.minimum.x + bounds.maximum.x) * 0.5,
    0.25,
    (bounds.minimum.z + bounds.maximum.z) * 0.5,
)
```

Sprite source:

- `32 x 24` cells
- 100 drift-item sprite slots
- 2 atlas pages, each `256 x 256`
- Transparent color: `8`
- `anchor_x`: visible-pixel horizontal center
- `anchor_y`: visible-pixel bottom
- `world_width`: per drift catalog item

Scale:

```python
projected_width = snapshot.focal_px * region.world_width / camera_point.z
scale = clamp(projected_width / region.width, 0.5, 1.5)
```

Screen placement:

```python
draw_x, draw_y = anchored_blt_origin(
    screen_x=projected.x,
    screen_y=projected.y,
    width=region.width,
    height=region.height,
    anchor_x=region.anchor_x,
    anchor_y=region.anchor_y,
    scale=scale,
)
```

Rendering:

- Render item type: `RenderSprite`
- Layer: `SOLID`
- Object id: `prop.render_object_id`
- Draw call: `pyxel.blt(..., scale=scale, colkey=8)`

Inspection marker:

```python
marker_world = Vec3(
    center_x,
    prop.bounds.maximum.y + prop.marker_height,
    center_z,
)
```

The marker is projected as a 2D UI prompt after the world render and is not part
of the painter sprite queue.

## Object: Environment World Sprite

World anchor:

```python
sprite.anchor = Vec3(x, 0.25, z)
```

Each environment sprite has:

- `source.width`
- `source.height`
- `anchor_x`
- `anchor_y`
- `world_width`
- `collision_half_x`
- `collision_half_z`
- `depth_bias`

Current environment sprite scale metadata:

| Sprite id | Source size | Anchor | World width | Collision half X/Z |
| --- | --- | --- | ---: | --- |
| `dead_tree_trunk` | `48 x 64` | `(24, 63)` | 28 | `12 / 10` |
| `mossy_rock` | `32 x 24` | `(16, 22)` | 20 | `9 / 8` |
| `weathered_sign` | `32 x 48` | `(16, 47)` | 18 | `5 / 5` |
| `jizo` | `32 x 48` | `(16, 46)` | 16 | `5.5 / 5.5` |
| `grass_tuft` | `16 x 16` | `(7, 15)` | 8 | `0 / 0` |
| `fern` | `24 x 24` | `(12, 23)` | 11 | `0 / 0` |
| `bracken` | `24 x 24` | `(11, 23)` | 11 | `0 / 0` |
| `butterbur` | `24 x 24` | `(11, 23)` | 13 | `0 / 0` |
| `horsetail` | `16 x 24` | `(8, 23)` | 7 | `0 / 0` |
| `sapling` | `24 x 32` | `(11, 31)` | 11 | `0 / 0` |

Scale:

```python
projected_width = snapshot.focal_px * region.world_width / camera_point.z
scale = clamp(projected_width / region.width, 0.5, 1.5)
```

Screen placement:

```python
draw_x, draw_y = anchored_blt_origin(
    screen_x=projected.x,
    screen_y=projected.y,
    width=region.width,
    height=region.height,
    anchor_x=region.anchor_x,
    anchor_y=region.anchor_y,
    scale=scale,
)
```

Rendering:

- Render item type: `RenderSprite`
- Layer: `SOLID`
- Object id: `sprite.object_id`
- Depth: `camera_point.z + region.depth_bias`
- Draw call: `pyxel.blt(..., scale=scale, colkey=region.colkey)`

Collision:

- Solid environment sprites create separate AABB collision solids.
- Foliage and forage sprites have no collision.
- Visual bounds and collision bounds are intentionally separate.

## Object: Parallax Backdrop Lines

Parallax is not inserted into the shared painter queue. It is drawn first inside
the 3D viewport, before floor, river, solids, sprites, prompts, and UI.

Atlas:

- Source tiles:
  - FAR: `64 x 32 x 4`
  - MID: `64 x 48 x 4`
  - NEAR: `64 x 64 x 4`
- Each layer keeps `a -> b -> c -> d` as a `256 px` atlas sequence for stable
  metadata, but runtime drawing projects and draws each `64 px` tile separately.
- Sequence order: `a -> b -> c -> d`
- Transparent color: `8`

Current tuning:

| Layer | Pixels/world | Tile world width | Lines |
| --- | ---: | ---: | --- |
| FAR | 0.035 | 72 | `z_offset=64 phase=0.0 scroll=0.8`, `z_offset=44 phase=0.5 scroll=1.0` |
| MID | 0.085 | 64 | `z_offset=36 phase=0.25 scroll=0.9`, `z_offset=24 phase=0.75 scroll=1.1` |
| NEAR | 0.14 | 56 | `z_offset=18 phase=0.0 scroll=0.95`, `z_offset=8 phase=0.5 scroll=1.15` |

Line position:

```python
edge_z = far_stage_edge_z(snapshot, render_bounds)
direction = farther_z_direction(snapshot)
line_z = edge_z + direction * line.z_offset
```

This creates multiple stage-parallel backdrop lines beyond the far edge of the
expanded scene. The nearer/farther pair hides gaps caused by transparent tile
edges and camera angle changes.

Scroll:

```python
sequence_world_w = tuning.world_width * len(PARALLAX_SEQUENCES[layer])
scroll_world = (
    snapshot.position.x
    * tuning.pixels_per_world
    * line.scroll_multiplier
    + sequence_world_w * line.phase_ratio
)
```

Visible world X span:

- Solves world X at the left and right viewport edges on the backdrop line.
- Adds `PARALLAX_VIEWPORT_MARGIN_X = 96` screen pixels and
  `PARALLAX_WORLD_SPAN_MARGIN_X = 96.0` world units.

Tiling:

1. Compute the current camera's world-X span on the backdrop line.
2. Convert `scroll_world` to a phase inside the `a -> b -> c -> d` sequence.
3. Walk tile indices across the span.
4. Select `sequence[tile_index % 4]`.
5. Project each tile's left, right, and middle ground anchors.
6. Draw that tile with its own scale and bottom anchor.

Scale:

1. Compute edge scale from the projected tile left/right screen width.
2. Compute midpoint scale from the tile midpoint camera depth.
3. Use edge scale only if it is stable.
4. Otherwise use midpoint scale.
5. Clamp final scale to `PARALLAX_STRIP_SCALE_LIMIT = 4.0`.

Stability rule:

```python
edge_scale <= PARALLAX_STRIP_SCALE_LIMIT
edge_scale <= midpoint_scale * PARALLAX_STRIP_EDGE_TO_MID_SCALE_LIMIT
```

Current `PARALLAX_STRIP_EDGE_TO_MID_SCALE_LIMIT = 2.0`.

Screen placement:

- Stable edge projection:

```python
anchor_screen_x = floor(screen_left) - 1
source_anchor_x = 0.0
bottom_y = max(left.y, right.y)
```

- Midpoint fallback:

```python
anchor_screen_x = middle.x
source_anchor_x = (region.width - 1) * 0.5
bottom_y = middle.y
```

Both paths then use the shared Pyxel center-pivot anchor calculation:

```python
draw_x, draw_y = anchored_blt_origin(
    screen_x=anchor_screen_x,
    screen_y=bottom_y,
    width=region.width,
    height=region.height,
    anchor_x=source_anchor_x,
    anchor_y=region.height - 1,
    scale=scale,
)
```

Draw call:

```python
pyxel.blt(
    draw_x,
    draw_y,
    atlas.image,
    region.u,
    region.v,
    region.width,
    region.height,
    region.colkey,
    scale=scale,
)
```

## Object: Inspection Prompt

Prompt source:

- No image asset.
- A small 2D triangle is drawn after world rendering.

Position:

```python
marker_world = Vec3(center_x, prop.bounds.maximum.y + marker_height, center_z)
projected = project_world_point(snapshot, marker_world)
```

Visibility:

- Not drawn if prop bounds are outside visible volume.
- Not drawn if projection is behind the near plane.
- Not drawn if projected point is outside the 3D viewport.
- Not drawn while an inspection panel is open.

Size:

- Visual half width: `5 px`
- Visual height: `7 px`
- Hitbox: `40 x 40 px`
- Bob animation: `PROMPT_BOB_Y = (0, 0, -1, -1, -2, -2, -1, -1)`

Rendering:

- 2D `pyxel.tri()` plus outline.
- No perspective scale.
- Stored as `last_rendered_prompt` for next-frame input capture.

## Object: Inspection Panel

The inspection panel is pure HUD, not 3D.

Current panel:

- `x=12`
- `y=536`
- `w=369`
- `h=204`
- title font size: `16`
- body font size: `15`
- line height: `19`
- max body lines: `6`

Rendering:

- Drawn after world, prompt/bubble, and base UI.
- No perspective scale.
- Text layout is cached by text key.
- While open, player velocity is forced to zero and player input is ignored.

## Object: Owner Memory Bubble

The owner memory bubble is drawn only while reading owner-letter or memory-echo
inspection content.

Anchor:

```python
foot = project_world_point(snapshot, Vec3(player.x, GROUND_Y, player.z))
scale = calculate_sprite_scale(
    snapshot.focal_px,
    foot.depth,
    PLAYER_SPRITE_WORLD_WIDTH,
    PLAYER_SPRITE_FRAME_W,
    minimum=PLAYER_SPRITE_MIN_SCALE,
    maximum=PLAYER_SPRITE_MAX_SCALE,
)
head_screen = player_head_screen_point(
    foot_screen_x=foot.x,
    foot_screen_y=foot.y,
    scale=scale,
)
```

The bubble is therefore attached to the visible cat sprite head, not to the
logical `PLAYER_SIZE_Y` cuboid height.

Sprite source:

- 4 frames
- Each frame: `64 x 64`
- Runtime atlas: `256 x 64`
- Transparent color: `2`
- Anchor: `(32, 62)`

Animation:

```python
sequence = (0, 1, 2, 3, 2, 1)
frame = sequence[(owner_memory_elapsed // 8) % len(sequence)]
```

Rendering:

- Drawn after world sprites and before the inspection panel.
- Fixed `1x` scale.
- Draw call: `pyxel.blt(..., colkey=2)`

## Source Files

- Camera constants: `src/three_line_explorer/config.py`
- Camera rig and snapshot: `src/three_line_explorer/camera.py`
- Camera rule resolution: `src/three_line_explorer/camera_director.py`
- App update/draw order: `src/three_line_explorer/app.py`
- Projection: `src/three_line_explorer/projection.py`
- Renderer: `src/three_line_explorer/renderer.py`
- Player movement and facing: `src/three_line_explorer/player.py`
- Player sprite source and row/frame selection: `src/three_line_explorer/player_sprite.py`
- Drift prop sprite atlas: `src/three_line_explorer/drift_item_sprites.py`
- Drift item metadata: `src/three_line_explorer/drift_item_catalog.py`
- Environment sprites and parallax source data:
  `src/three_line_explorer/generated_environment_assets.py`
- Runtime environment sprite atlas:
  `src/three_line_explorer/environment_sprites.py`
- Runtime parallax renderer: `src/three_line_explorer/parallax.py`
- Inspection prompt and panel: `src/three_line_explorer/inspection.py`
- Owner memory bubble: `src/three_line_explorer/owner_memory_bubble_sprites.py`
- Shared scaled `blt` anchor math: `src/three_line_explorer/blit_anchor.py`
