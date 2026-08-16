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

This first prototype intentionally uses only Pyxel primitives. No `.pyxres` asset file is created yet.

GitHub Pages publishing:

The published site is served from the `gh-pages` branch. To refresh it after changing the app:

```bash
scripts/publish_pages.sh
```

Published page:

https://sejiseji.github.io/riverside/

For cache-explicit checks, use a versioned URL:

```text
https://sejiseji.github.io/riverside/?v=<commit-or-check-id>
```

The page propagates `v`, `id`, or `riverside_bust` to local `.py` and `.pyxres`
loads so Pyxel Web does not reuse stale app files.
