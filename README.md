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
