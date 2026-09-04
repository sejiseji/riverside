# riverside Asset Contract v1

This document defines the image data that can be prepared outside the codebase
and then integrated into the Pyxel prototype.

## Shared Rules

- Use Pyxel palette indexes, written as lowercase hexadecimal digits.
- Use no anti-aliasing, alpha blending, soft shadows, blur, or semi-transparent
  pixels.
- For transparent source maps, `.` means transparent.
- `.` is converted to the asset's own `transparent_color` at compile time.
- The transparent color restriction is per asset and per `pyxel.blt()` call, not
  global.
- A transparent source map must not use its own `transparent_color` as a visible
  color.
- For opaque source maps, `.` is invalid and all `0..f` digits are available.

Allowed source characters:

```python
OPAQUE_SOURCE_CHARS = "0123456789abcdef"
TRANSPARENT_8_SOURCE_CHARS = ".012345679abcdef"
PLAYER_VISIBLE_SOURCE_CHARS = "013456789abcdef"
```

For example, prop and parallax assets currently use `transparent_color=8`, so
visible color `8` is unavailable inside those assets. Player sprites use
`transparent_color=2`, so visible color `8` is still available to the player.

## Player Sprite Sheet

```text
Purpose: player character
Current subject: four-direction walking character
Storage: assets/player_sprites.pyxres first, embedded fallback second

Runtime draw anchor:
  x = 24
  y = 60
Cell size: 48x64 px
Grid: 4 columns x 4 rows
Total cells: 16
Sheet size: 192x256 px
Columns: frame 0, frame 1, frame 2, frame 3
Rows: FRONT, RIGHT, LEFT, BACK
Transparent color: Pyxel color 2
Visible color rule: color 2 cannot be used as visible player pixels
```

The runtime anchor is slightly above the full 64 px cell bottom so transparent
bottom padding does not make the character appear to float.

Frame 0 must be usable as a neutral idle pose. The walking loop may include
frame 0, but individual character tuning can later choose a different sequence.

Placement rules:

- Visual center should be around x=24 in every cell.
- Contact point should stay around y=62 in every cell.
- Keep at least 1 px of head and side margin.
- Do not let the contact point drift between frames.

## Inspectable Prop Sprites

```text
Purpose: small riverside inspection props
Storage: source-defined Pyxel color maps
Cell size: 32x24 px
Animation: none
One prop: one sprite
Runtime transparent_color: Pyxel color 8
Source transparent char: .
Allowed transparent source chars: .012345679abcdef
Visible color rule: color 8 cannot be used as visible pixels in this prop asset
Current count: 100
Runtime atlas: two 256x256 pages
Content split: 86 ambient, 8 owner letters, 6 memory echoes
```

Required metadata:

```python
DriftItemDefinition(
    item_id=...,
    title=...,
    body=...,
    spawn_weight=...,
    min_area_index=...,
    world_width=...,
    marker_offset_y=...,
    acquire_padding_x=...,
    acquire_padding_z=...,
)
```

The current runtime calculates `anchor_x` and `anchor_y` from the visible pixel
bounds. The 14 fixed story entries reuse existing physical sprite slots and are
excluded from the default ambient random pool.

GPT handoff prompt:

```text
Create a riverside Pyxel prop sprite as a 32x24 color-index map.
Return exactly 24 rows, each exactly 32 characters.
Use only .012345679abcdef.
. is transparent. This prop uses transparent_color 8, so do not use visible color 8.
No anti-aliasing, semi-transparency, or extra whitespace.
Keep the object readable as a small silhouette.
Also provide item_id, Japanese title/body, world_width, marker_offset_y,
acquire_padding_x, acquire_padding_z, rarity/spawn_weight, and min_area_index.
```

## Parallax Background Tiles

```text
Purpose: sky-adjacent distant scenery behind the 3D floor and river
Storage: source-defined Pyxel color maps
Drawing: 2D layers before world rendering
Full-screen image: not used
Initial layers: FAR, MID, NEAR
Initial tile count: 12 total
```

Initial tile set:

```text
FAR:  64x32 px x 4 tiles
MID:  64x48 px x 4 tiles
NEAR: 64x64 px x 4 tiles
```

Transparent layer rules:

- Use `.012345679abcdef` when the runtime `transparent_color` is color 8.
- Do not use visible color 8 in those transparent layer assets.
- Align rows top to bottom.
- Draw each tile by bottom alignment:

```python
draw_y = layer_bottom_y - tile_height
```

Opaque sky rules:

- Use `0123456789abcdef`.
- Do not use `.`.
- Prefer Pyxel primitives or a small opaque repeated map before adding large
  image data.

Tile seam rules:

- Do not place major trees or buildings cut through the left/right edge.
- Do not leave unintended empty columns at tile boundaries.
- Keep left and right edge heights compatible with arbitrary neighboring tiles.
- Keep tile sequence fixed in stage data; do not use runtime random generation.

## World Environment Sprites

```text
Purpose: nearby scenery and small obstacles placed on the stage
Storage: source-defined Pyxel color maps
Drawing: contact-point billboard sprites in the normal stage-order sprite queue
Collision: optional separate X/Z footprint
Current count: 10
Runtime transparent_color: Pyxel color 8
Source transparent char: .
Allowed transparent source chars: .012345679abcdef
```

Current generated set:

```text
Collidable: dead_tree_trunk, mossy_rock, weathered_sign, jizo
Inspectable: weathered_sign
Non-collidable: grass_tuft, fern, bracken, butterbur, horsetail, sapling
```

Required metadata:

```python
WorldSpriteSpec(
    source=PixelMapSpec(...),
    kind=...,
    anchor_x=...,
    anchor_y=...,
    world_width=...,
    collision_half_x=...,
    collision_half_z=...,
    inspectable_text_key=...,
    depth_bias=...,
)
```

World environment sprites are not converted into visible AABB solids. When a
sprite is collidable, its collision footprint is registered separately and used
only by player movement.

## Owner Memory Bubble

```text
Purpose: owner recollection visual shown above the player during story panels
Storage: source-defined Pyxel color maps
Frame size: 64x64 px
Frame count: 4
Atlas size: 256x64 px
Transparent color: Pyxel color 2
Source transparent char: .
Visible color rule: color 2 cannot be used as visible pixels in this asset
Anchor: x=32, y=62
Loop: 0, 1, 2, 3, 2, 1
Frame hold: 8 game frames
Display policy: OWNER_LETTER and MEMORY_ECHO panels only
```

GPT handoff prompt:

```text
Create a riverside owner-memory bubble as Pyxel color-index maps.
Return 4 frames.
Each frame must be exactly 64 rows, each exactly 64 characters.
Use . as transparent and Pyxel color 2 as transparent_color.
Do not use visible color 2 in this asset.
No anti-aliasing, semi-transparency, blur, or extra whitespace.
Keep the lower-center puff near anchor (32, 62) so it attaches to the player's head.
The animation should loop as 0, 1, 2, 3, 2, 1 with gentle motion.
```
