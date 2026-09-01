#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUBLISH_DIR="$(mktemp -d /tmp/riverside-pages.XXXXXX)"
APP_DIR="$PUBLISH_DIR/riverside"
CACHE_BUST_ID="${1:-$(git -C "$ROOT_DIR" rev-parse --short HEAD)}"
PYXEL_BIN="$ROOT_DIR/.venv/bin/pyxel"
if [ ! -x "$PYXEL_BIN" ]; then
  PYXEL_BIN="pyxel"
fi

cleanup() {
  rm -rf "$PUBLISH_DIR"
}
trap cleanup EXIT

copy_app() {
  local target_dir="$1"
  mkdir -p "$target_dir"
  rsync -a "$ROOT_DIR/web_bootstrap.py" "$target_dir/"
  rsync -a \
    --exclude "__pycache__/" \
    --exclude "*.pyc" \
    "$ROOT_DIR/src/three_line_explorer" \
    "$target_dir/"
  if [ -d "$ROOT_DIR/assets" ]; then
    rsync -a "$ROOT_DIR/assets" "$target_dir/"
  fi
}

copy_app "$APP_DIR"
rsync -a "$ROOT_DIR/index.html" "$PUBLISH_DIR/"
(
  cd "$PUBLISH_DIR"
  "$PYXEL_BIN" package riverside riverside/web_bootstrap.py
)
rm -rf "$APP_DIR"
touch "$PUBLISH_DIR/.nojekyll"

git -C "$PUBLISH_DIR" init -b gh-pages
git -C "$PUBLISH_DIR" remote add origin git@github.com:sejiseji/riverside.git
git -C "$PUBLISH_DIR" fetch origin gh-pages
git -C "$PUBLISH_DIR" add .
git -C "$PUBLISH_DIR" commit -m "Publish Pyxel web page"
git -C "$PUBLISH_DIR" push --force-with-lease origin gh-pages

echo "Published: https://sejiseji.github.io/riverside/?v=$CACHE_BUST_ID"
