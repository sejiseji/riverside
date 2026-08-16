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
- Touch / pointer: tap the camera buttons, or drag anywhere else as a virtual direction stick.
  Horizontal drag moves along the route, and vertical drag changes lanes. Camera changes update
  the screen-space mapping from the last rendered camera state.

Player sprites:

The editable player sprite sheet lives in:

```text
assets/player_sprites.pyxres
```

The game loads this `.pyxres` first. If it is missing, it falls back to the
embedded sprite data in `src/three_line_explorer/player_sprite_data.py`.

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

The page propagates `v` to local `.py` and `.pyxres` loads so Pyxel Web does
not reuse stale app files.

The publish script places only the Pyxel Web entry files at the Pages root:
`index.html`, `web_bootstrap.py`, `three_line_explorer/`, and `assets/`.
`run.py` and `src/` are local development files and are not published.
