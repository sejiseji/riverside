# riverside Current Baseline

This document captures the current implementation baseline for the prototype.
Future implementation order is tracked in `docs/roadmap.md`.

## Core Rules

- Movement logic is limited to X-axis travel plus three discrete Z lanes.
- The river is visual space on the +Z side, not an extra walkable lane.
- Player position is stored as the contact-point center.
- Forward/back movement and lane movement both require the player to face the target direction first.
- Camera shots A/B/C are stage-fixed shots, independent of player facing.
- Camera transitions do not stop normal movement or lane input.
- Visible volume, collision, and solid rendering are based on AABBs.
- The logical visible volume remains the gameplay clamp, while the renderer
  uses an expanded scene AABB for floor, river, scenery, and solid pop-in.
- Rendering uses a painter-style sort without a Z buffer.
- Input is interpreted in screen space.
- Active drags are rebased when the camera input basis changes.
- Player sprites load from `.pyxres` first, with embedded data as a fallback.
- Stage camera zones can force or restrict camera shots.
- Inspectable riverside props are non-collision objects with their own proximity and text data.
- Inspection prompts are 2D UI markers projected from 3D anchor points.
- Parallax scenery is drawn as source-defined tiles projected from the far
  stage edge, before floor, river, solids, sprites, prompts, and UI.
- Environment world sprites use source-defined Pyxel color maps and share the
  same camera-side stage-order sort as player and prop sprites.
- Environment sprite collision footprints are separate from their visual
  sprites and are not rendered as AABB boxes.
- RIV013 drift content is split into ambient debris, owner letters, and memory
  echoes. Story drift items are fixed-order and advance only when their panel is
  closed after the final page.
- Owner-letter and memory-echo panels show a four-frame owner memory bubble
  projected from the player's head position.

## Screen

- Logical resolution: 393x852
- FPS: 60
- Top UI: 56 px
- Bottom UI: 80 px
- 3D viewport: x=0, y=56, w=393, h=716

## World

- +X: route forward
- -X: route backward
- +Y: up
- +Z: riverside
- -Z: inland

Stage bounds:

- X: -480 .. +480
- Y: 0 .. 100
- Z: -60 .. +180

Walkable lanes:

- `LaneId.NEGATIVE_Z`: Z=-36
- `LaneId.CENTER`: Z=0
- `LaneId.POSITIVE_Z`: Z=36

River:

- `RIVER_START_Z = LANE_Z[-1] + PLAYER_SIZE_Z * 0.5`
- Current river start: Z=44
- River extends to Z=180.
- The renderer extends floor/river drawing beyond the logical visible volume:
  X is padded on both sides, and the far camera-side Z edge is padded so the
  green ground or river continues toward the parallax background.
- Solids must not extend past `RIVER_START_Z`.
- Low riverside props may be placed beyond `RIVER_START_Z`; they are not
  collision solids.
- Inland environmental props may also be inspectable when their visible sprite
  and collision footprint are provided by the environment-sprite system.

## Player

- Size: X=18, Y=30, Z=16
- Max speed: 72
- Acceleration: 480
- Deceleration: 520
- Turn half-life: 0.04
- Move-ready yaw tolerance: 12 degrees
- Lane half-life: 0.055
- Lane turn delay: 0.10 seconds
- Walk animation advances from actual X/Z movement distance, not from
  `pyxel.frame_count`.
- Turn-in-place, reading panels, and blocked frames keep the sprite on an idle
  frame because `last_move_distance` is zero.
- A small player shadow is projected as a floor-aligned ellipse before solid
  and sprite rendering.
- The shadow uses the current sprite walk frame to apply subtle width/depth
  scale changes.

## Camera

- Shared horizontal FOV: 38 degrees
- Target Y: 18
- Transition duration: 0.85 seconds
- Near plane: 4

Shots:

- A: `REAR_RIGHT_LOW`, azimuth 110, elevation 12, distance 640
- B: `FRONT_RIGHT_CLOSE`, azimuth 70, elevation 14, distance 520
- C: `REAR_LEFT_SHALLOW`, azimuth 240, elevation 6, distance 700

## Input

Keyboard:

- `Left` / `A`: move along route toward screen-left.
- `Right` / `D`: move along route toward screen-right.
- `Up` / `W`: request lane movement toward screen-up.
- `Down` / `S`: request lane movement toward screen-down.
- `1`, `2`, `3`: request camera A/B/C.
- `C`: cycle camera.
- `H`: toggle debug HUD.
- `B`: toggle visible bounds.
- `L`: toggle lane guides.
- `R`: reset.
- `J`, `K`: debug warp left/right.
- `Esc`: quit.

Pointer:

- Camera button taps request camera changes.
- Other drags act as a virtual direction stick.
- Horizontal drag controls route movement.
- Vertical drag controls lane movement.
- Lane drag threshold is 64 px.
- Lane repeat delay is 0.16 seconds.
- If an inspection panel is open, pointer input is consumed by the panel instead of the stick.
- If an inspection prompt is tapped, that pointer sequence is captured and does not start stick input.

## Inspection

- Main modules:
  - `inspection.py`: target selection, panel state, prompt/panel drawing
  - `inspection_texts.py`: effective Japanese inspection text registry
  - `inspection_content_registry.py`: RIV013 ambient/story text integration
  - `story_content.py`: owner letters and memory echoes
  - `story_progression.py`: fixed story sequence state
  - `drift_item_catalog.py`: 100-slot drift item catalog
  - `drift_item_randomizer.py`: weighted ambient item selection
  - `drift_item_sprites.py`: 100 source-defined Pyxel color-map prop sprites
  - `inspection_prop_sprites.py`: compatibility wrapper for the 100-slot prop atlas
  - `owner_memory_bubble_sprites.py`: four-frame owner recollection bubble
  - `text_layout.py`: measured wrapping, kinsoku handling, page splitting, cache
  - `ui_fonts.py`: bundled font loading
- Data type: `InspectableProp`
- Collection: `Stage.inspectable_props`
- Collision: none on the `InspectableProp` itself
- Rendering: source-defined 32x24 prop sprites, or no prop sprite when another
  world sprite supplies the visual object
- Active target count: one nearest target
- Proximity test: world-space X/Z AABB overlap
- Acquisition padding: X=28, Z=12
- Release padding: X=36, Z=18
- Marker anchor: prop top center plus `marker_height`
- Marker draw: fixed 2D triangle after projecting the 3D anchor
- Marker hitbox: 40x40 px
- Panel rect: x=12, y=536, w=369, h=204
- Panel behavior: movement and manual camera requests stop while open
- Existing camera transitions continue while the panel is open
- Page advance: panel tap, `Z`, `Enter`, or `Space`
- Read history: `InteractionState.inspected_ids`
- Owner memory bubble display: enabled only for `OWNER_LETTER` and
  `MEMORY_ECHO`, not normal ambient drift items.
- Owner memory bubble timing: reset to frame 0 when the panel opens, then uses
  panel-local elapsed frames while the panel remains open.
- Owner memory bubble anchor: `Vec3(player.x, PLAYER_SIZE_Y + 5.0, player.z)`
  projected through the current camera.
- Current text is Japanese RIV013 content plus stage-local text.
- Current content registry: 86 ambient drift items, 8 owner letters, 6 memory
  echoes, plus stage-local `weathered_forest_sign`.
- Current prototype placed targets: seven riverside drift props plus the inland
  weathered sign.
- Story area progress is currently mapped from the prototype route start
  (`PLAYER_START_X`) toward `STAGE_MAX_X`; RIV014 can replace this with the
  final A-R area table.
- Active story item placement uses a temporary riverside slot near the player
  and remains persistent until read.
- Current prop sprite set: 100 RIV013 drift item sprites
- Prop sprite storage: Python source rows using Pyxel palette digits
- Prop sprite transparent authoring char: `.`
- Prop sprite transparent palette index: 8
- Prop sprite visible source chars: `.012345679abcdef`; color `8` is the prop
  sprite transparent color and cannot be used as a visible prop color in those
  assets.
- Prop sprite anchor: ground center of the prop AABB
- Prompt marker anchor: top center of the prop AABB plus `marker_height`
- Prop, environment, and player sprite draw order: same Painter sprite queue,
  sorted by camera-side lane depth, route depth, camera depth, and stable
  object id
- Font path: `assets/fonts/DotGothic16-Regular.ttf`
- Font license text: `assets/fonts/DotGothic16-OFL.txt`
- Active font target: DotGothic16 TTF, title 16 px, body 15 px
- Inspection panel rectangle: x=12, y=536, w=369, h=204
- Inspection panel bottom guard: 112 logical px
- Inspection text is drawn once per line without faux-bold shadowing.
- Font usage follows the Pyxel custom font sample: create `pyxel.Font(...)`
  after `pyxel.init(...)`, pass it to `pyxel.text(...)`, and use
  `font.text_width(...)` for measurement.
- Text layout uses `Font.text_width` first and falls back to a conservative
  Japanese width estimate only when `text_width` is unavailable.
- The layout cache is built per inspection text key, so wrapping is not
  recalculated every frame.

## Assets

- Editable sprite resource: `assets/player_sprites.pyxres`
- Embedded fallback: `src/three_line_explorer/player_sprite_data.py`
- Current sprite layout: 4 directions x 4 frames
- Frame size: 48x64
- Transparent color: Pyxel color 2
- Sprite draw anchor: X=24, Y=60 inside each 48x64 cell, tuned to place the
  cat's visible feet on the projected ground/shadow instead of aligning to the
  full transparent cell bottom.
- Frame selection: `frame 0` when idle, otherwise `walk_phase` selects the
  4-frame walk sequence.
- Walk phase source: actual player movement distance divided by
  `PLAYER_WALK_FRAME_DISTANCE`.
- Source-defined inspection prop sprites: `src/three_line_explorer/inspection_prop_sprites.py`
- Prop sprite atlas: 100 sprites x 32x24, generated once at runtime as two
  256x256 pages
- Prop sprite source: `src/three_line_explorer/drift_item_sprites.py`
- Prop sprite image files: none
- Source-defined environment pack: `src/three_line_explorer/generated_environment_assets.py`
- Environment sprite atlas: world scenery sprites generated once at runtime
- Environment sprite helper: `src/three_line_explorer/environment_sprites.py`
- Parallax helper: `src/three_line_explorer/parallax.py`
- Owner memory bubble source: `src/three_line_explorer/owner_memory_bubble_sprites.py`
- Owner memory bubble frames: 4 x 64x64
- Owner memory bubble atlas: 256x64, generated once after `pyxel.init`
- Owner memory bubble transparent color: Pyxel color 2
- Owner memory bubble draw anchor: X=32, Y=62
- Owner memory bubble loop: 0, 1, 2, 3, 2, 1 with 8-frame holds
- Parallax layers: FAR 64x32 x4, MID 64x48 x4, NEAR 64x64 x4
- Parallax sequence: `a -> b -> c -> d`, repeated per layer
- Parallax scroll: `player.x * camera_snapshot.right.x` converted to a
  layer-specific world offset
- Parallax placement: layers stand just beyond the far Z edge of the current
  expanded scene render bounds, with A/B using the inland edge and C using the river edge
- Parallax projection: each tile is a bottom-anchored billboard whose contact
  point is projected through the current camera

## Rendering Bounds

- Logical visible volume: player-following AABB used for gameplay framing and
  debug bound display.
- Scene render bounds: logical visible volume expanded by
  `SCENE_RENDER_MARGIN_X` on both X sides and by `SCENE_RENDER_FAR_MARGIN_Z` on
  the far camera-side Z edge.
- Floor, river, solid clipping, prop sprites, environment sprites, lane guides,
  and parallax placement use the scene render bounds.
- Debug visible-volume edges still use the logical bounds so the true gameplay
  window remains inspectable.
- Player movement, collision, camera zones, and inspection proximity do not use
  the scene render bounds.
- Environment pack manifest: `docs/RIV014_5_environment_asset_manifest.md`
- Shared pixel-map validation: `src/three_line_explorer/pixel_map_source.py`
- Japanese panel font: `assets/fonts/DotGothic16-Regular.ttf`
- Font third-party notice: `THIRD_PARTY_NOTICES.md`

## Web Publishing

- Pages entry point: `index.html`
- Runtime tag: `pyxel-play`
- Packaged app: `riverside.pyxapp`
- Published cache-specific app: `riverside-<commit-or-check-id>.pyxapp`
- Package command: `pyxel package riverside riverside/web_bootstrap.py`
- The `.pyxapp` contains `web_bootstrap.py`, `three_line_explorer/`, and `assets/`.
- Raw `.py` source files are not published separately on `gh-pages`.
- Mobile HTML fits the game to the visible viewport at 393:852 instead of
  stretching it to `100dvh`, with a minimum 40px browser-control guard in
  portrait mode.
- Local `index.html` uses `riverside.pyxapp`; the publish script rewrites the
  published copy to the cache-specific app filename.
