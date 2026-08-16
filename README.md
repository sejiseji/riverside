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

- Keyboard: `W` / `Up` moves +X, `S` / `Down` moves -X, `Left` / `Right` changes the target lane in screen space.
- Touch / pointer: tap the camera buttons, or drag anywhere else as a virtual direction stick. Up/down drag moves along X while held; left/right drag changes lanes in screen space.

This first prototype intentionally uses only Pyxel primitives. No `.pyxres` asset file is created yet.

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
`index.html`, `web_bootstrap.py`, and `three_line_explorer/`. `run.py` and
`src/` are local development files and are not published.
