# riverside

Pyxel prototype for a vertical three-line 2.5D exploration game.

Run locally:

```bash
python3 -m pip install -e .
python3 run.py
```

Run logic tests:

```bash
python3 -m unittest discover -s tests -t .
```

Prototype controls:

- Keyboard: `Left` / `A` and `Right` / `D` move along the route in screen space.
  `Up` / `W` and `Down` / `S` change the target lane in screen space.
  `H` toggles the debug HUD, `B` toggles bounds, and `L` toggles lane guides.
- Touch / pointer: tap the camera buttons, or drag anywhere else as a virtual direction stick.
  Horizontal drag moves along the route, and vertical drag changes lanes. Camera changes update
  the screen-space mapping from the last rendered camera state.
- Inspection: when a nearby riverside prop is active, tap the yellow marker to open its panel.
  While the panel is open, movement and manual camera input are suppressed; tap the panel or
  press `Z`, `Enter`, or `Space` to advance and close it.
  The panel uses bundled DotGothic16 Japanese TTF fonts at 16 px for titles and
  15 px for body text.
  Small riverside props are source-defined Pyxel color maps, generated into a
  runtime atlas once and rendered through the same sprite depth queue as the
  player.

Player sprites:

The editable player sprite sheet lives in:

```text
assets/player_sprites.pyxres
```

The game loads this `.pyxres` first. If it is missing, it falls back to the
embedded sprite data in `src/three_line_explorer/player_sprite_data.py`.

Inspectable prop sprites:

```text
src/three_line_explorer/inspection_prop_sprites.py
```

Each prop sprite is authored as 32x24 rows of Pyxel palette digits. `.` is
converted to transparent color `8` when the runtime atlas is built. The current
atlas contains the single sandal, clouded bottle, and driftwood sprites.

Japanese font:

```text
assets/fonts/DotGothic16-Regular.ttf
assets/fonts/DotGothic16-OFL.txt
```

This prototype follows the Pyxel custom font sample: create `pyxel.Font(...)`
after `pyxel.init(...)`, pass the font to `pyxel.text(...)`, and use
`font.text_width(...)` for text measurement. Inspection text layout uses the
measured width first, and falls back to a conservative Japanese width estimate
only if a font implementation does not expose `text_width`.

Third-party font notices are listed in `THIRD_PARTY_NOTICES.md`.

GitHub Pages publishing:

The published site is served from the `gh-pages` branch. To refresh it after changing the app:

```bash
scripts/publish_pages.sh
```

Published page:

https://sejiseji.github.io/riverside/?v=<commit-or-check-id>

The publish script prints the current commit version:

```text
https://sejiseji.github.io/riverside/?v=<commit-or-check-id>
```

The page propagates `v` to the generated `.pyxapp` and local asset loads so
Pyxel Web does not reuse stale app files.
On mobile browsers the canvas is fit to the visible viewport while preserving
the 393:852 game aspect ratio. The inspection panel also keeps a large logical
bottom margin so it stays above browser controls in embedded mobile browsers.

The publish script packages the app with `pyxel package` and places only
`index.html`, `riverside.pyxapp`, and `.nojekyll` at the Pages root. Raw source
files remain local and on the `main` branch; Pages runs the packaged app with
`pyxel-play`.
