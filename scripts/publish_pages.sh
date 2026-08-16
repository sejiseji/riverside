#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUBLISH_DIR="$(mktemp -d /tmp/riverside-pages.XXXXXX)"
PUBLISH_ID="${1:-$(git -C "$ROOT_DIR" rev-parse --short HEAD)}"
BUILD_DIR="$PUBLISH_DIR/builds/$PUBLISH_ID"

cleanup() {
  rm -rf "$PUBLISH_DIR"
}
trap cleanup EXIT

copy_site() {
  local target_dir="$1"
  mkdir -p "$target_dir"
  rsync -a "$ROOT_DIR/index.html" "$ROOT_DIR/web_bootstrap.py" "$ROOT_DIR/run.py" "$ROOT_DIR/src" "$target_dir/"
  touch "$target_dir/.nojekyll"
}

copy_site "$PUBLISH_DIR"
copy_site "$BUILD_DIR"
touch "$PUBLISH_DIR/.nojekyll"

git -C "$PUBLISH_DIR" init
git -C "$PUBLISH_DIR" branch -M gh-pages
git -C "$PUBLISH_DIR" remote add origin git@github.com:sejiseji/riverside.git
git -C "$PUBLISH_DIR" fetch origin gh-pages
git -C "$PUBLISH_DIR" add .
git -C "$PUBLISH_DIR" commit -m "Publish Pyxel web page"
git -C "$PUBLISH_DIR" push --force-with-lease origin gh-pages

echo "Published: https://sejiseji.github.io/riverside/builds/$PUBLISH_ID/"
