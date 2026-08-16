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

GitHub Pages build:

The repository publishes `index.html`, `web_bootstrap.py`, `run.py`, and `src/` through
`.github/workflows/pages.yml`.

Published page:

https://sejiseji.github.io/riverside/
