# riverside Roadmap

Current baseline: RIV014.5 environment integration.

This roadmap keeps the prototype focused on the current structure: three
walkable Z lanes, a visual river on the +Z side, screen-space input, independent
camera shots, AABB collision/rendering, source-defined small sprites, and
GitHub Pages `.pyxapp` publishing.

## Planned Order

1. RIV012: Inspection UI stabilization
2. RIV013: Inspectable prop content expansion
3. RIV014: Riverside stage composition
4. RIV014.5: Parallax background foundation and environment asset integration
5. RIV015: Player sprite polish
6. RIV016: Collision strengthening
7. RIV017: Camera and draw-order polish
8. RIV018: Mobile input polish
9. RIV019: Minimum playable slice

## RIV012: Inspection UI Stabilization

- Confirm the inspection panel on iPhone-class portrait browsers.
- Tune panel position, height, title size, body size, and bottom guard.
- Keep Japanese text rendered once per line without faux-bold shadowing.
- Confirm panel tap, `Z`, `Enter`, and `Space` page advance.
- Confirm panel input does not leak into movement drag.

## RIV013: Inspectable Prop Content Expansion

- Expand from 3 props to about 5 props, not 10 yet.
- Keep props non-collision unless a separate collision object is explicitly
  needed.
- Finalize the GPT prop-sprite authoring format: 32x24 Pyxel palette rows,
  `.` as transparent authoring char, palette index 8 as the prop
  `transparent_color`, and no visible use of color `8` inside those prop assets.
- Keep prop text and prop placement separate through `text_key`.
- Use this stage to stabilize the content addition flow before larger layout
  work.

## RIV014: Riverside Stage Composition

- Finalize the overhead area labels from A through R.
- Preserve +Z as the river side and -Z as the inland side.
- Keep the river as visual space outside the walkable lane area.
- Place solid objects only where they do not enter the river visual zone unless
  intentionally modeled as non-walkable scenery.
- Decide the rough themes for each area before adding many more props.

## RIV014.5: Parallax Background Foundation

RIV014.5 sits after area composition and before camera polish. The background
needs the stage meaning and horizon to exist, but camera framing should be
polished while the background is visible.

### Split Background Types

- Far parallax background: 2D layers drawn before the 3D floor and river.
- World scenic objects: placed in the stage with a contact point and rendered
  through the existing depth-sorted sprite or solid queues.

Examples:

- Far background: sky, haze, distant tree line, low opposite bank silhouettes.
- World objects: nearby trees, grasses, poles, signs, fences, rocks, bridge
  supports.

Do not move the first parallax pass to `blt3d`/`bltm3d`. Riverside already uses
an independent camera, projection, visible volume, AABB clipping, and painter
queue. The initial parallax pass should stay as 2D background layers.

### Source Asset Format

- Use source-defined Pyxel color rows.
- Represent transparent authoring pixels with `.` and convert them to the layer
  `transparent_color` at atlas build time.
- Do not allow visible use of the layer's own transparent digit in transparent
  layers.
- Use `transparent_color=None` for fully opaque layers such as sky.
- Avoid huge full-screen pixel maps in source.
- Prefer tiled assets:
  - FAR: 64x32
  - MID: 64x48
  - NEAR: 64x64
- Start with around four tiles per layer and repeat them by a fixed sequence.

### Scroll and Horizon

Use `player.x`, not `visible_volume.center_x`, because the camera keeps following
the player even at stage ends.

Background X scroll:

```python
scroll_px = round(
    -player.x
    * layer.pixels_per_world
    * camera_snapshot.right.x
)
```

Initial layer speeds:

- FAR: `0.04`
- MID: `0.10`
- NEAR: `0.18`

Horizon Y should follow the current interpolated camera elevation:

```python
horizon_y = (
    viewport_center_y
    - camera_snapshot.focal_px * math.tan(camera_elevation)
)
```

Layer bottom Y is then:

```python
layer_bottom_y = round(horizon_y) + layer.horizon_offset_y
```

### Substages

RIV014.5A:

- Add pixel-map validation and atlas helpers for parallax assets.
- Build Pyxel images once after `pyxel.init`.
- Add unit tests for row width, height, palette characters, and colkey handling.

RIV014.5B:

- Draw FAR, MID, and NEAR layers inside the 3D viewport clip.
- Fill the screen width with repeated tiles.
- Use camera basis for scroll direction so A/B/C and camera transitions remain
  continuous.
- Add a debug toggle for background visibility.

RIV014.5C:

- Add riverside-appropriate art: haze, low tree line, uneven distant silhouettes,
  and repeated edge cleanup.
- Keep all layers behind the floor, river, world solids, player, props, and UI.
- Place the first generated world-sprite set: dead tree trunk, mossy rock,
  weathered sign, jizo, grass tuft, fern, bracken, butterbur, horsetail, and
  sapling.
- Keep world-sprite collision footprints separate from visual sprite bounds.

### Acceptance

- Transparent background source rows contain only valid palette digits other
  than that layer's own transparent digit, plus `.`.
- Background images are generated once at startup.
- Normal drawing stays to roughly 30 `blt` calls or fewer.
- No blank gaps appear at tile boundaries or stage ends.
- A/B/C cameras do not reverse the parallax direction incorrectly.
- Camera transitions do not cause instant background flips.
- Horizon follows camera elevation smoothly.
- Background never draws into top or bottom UI areas.
- Turning off parallax does not affect game logic.

## RIV015: Player Sprite Polish

- Tune cat sprite contact point, shadow, scale, and frame pacing.
- Keep animation speed based on movement distance.
- Confirm direction mapping after all camera transitions.
- Keep turn-before-move behavior intact.

## RIV016: Collision Strengthening

- Improve forward obstacle stopping precision.
- Decide behavior when the destination lane is blocked.
- Add collision debug overlays for player and obstacle AABBs.
- Keep inspectable props non-collision unless paired with a separate blocker.

## RIV017: Camera and Draw-Order Polish

- Recheck sprite and solid draw order in all three shots.
- Split background profiles if needed:
  - A/B: inland-facing background.
  - C: river-facing background.
- Keep painter sorting stable by line depth, route depth, camera depth, and
  object id.

## RIV018: Mobile Input Polish

- Add or refine virtual stick visuals.
- Tune drag thresholds and lane repeat cooldown.
- Confirm active drags are rebased during camera changes.
- Recheck prompt taps, panel taps, and movement drag ownership.

## RIV019: Minimum Playable Slice

- Build one short riverside exploration route.
- Use a small set of inspectable props with meaningful placement.
- Include at least one camera zone that supports the scene rather than only
  testing mechanics.
- Confirm movement, collision, camera, inspection, and publishing all work
  together on the public Pages build.
