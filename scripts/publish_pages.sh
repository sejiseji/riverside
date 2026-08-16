#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUBLISH_DIR="$(mktemp -d /tmp/riverside-pages.XXXXXX)"
CACHE_BUST_ID="${1:-$(git -C "$ROOT_DIR" rev-parse --short HEAD)}"

cleanup() {
  rm -rf "$PUBLISH_DIR"
}
trap cleanup EXIT

copy_site() {
  local target_dir="$1"
  mkdir -p "$target_dir"
  rsync -a "$ROOT_DIR/index.html" "$ROOT_DIR/web_bootstrap.py" "$target_dir/"
  rsync -a \
    --exclude "__pycache__/" \
    --exclude "*.pyc" \
    "$ROOT_DIR/src/three_line_explorer" \
    "$target_dir/"
  touch "$target_dir/.nojekyll"
}

copy_site "$PUBLISH_DIR"
touch "$PUBLISH_DIR/.nojekyll"

git -C "$PUBLISH_DIR" init -b gh-pages
git -C "$PUBLISH_DIR" remote add origin git@github.com:sejiseji/riverside.git
git -C "$PUBLISH_DIR" fetch origin gh-pages
git -C "$PUBLISH_DIR" add .
git -C "$PUBLISH_DIR" commit -m "Publish Pyxel web page"
git -C "$PUBLISH_DIR" push --force-with-lease origin gh-pages

echo "Published: https://sejiseji.github.io/riverside/?v=$CACHE_BUST_ID"
