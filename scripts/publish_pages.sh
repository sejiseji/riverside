#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PUBLISH_DIR="$(mktemp -d /tmp/riverside-pages.XXXXXX)"

cleanup() {
  rm -rf "$PUBLISH_DIR"
}
trap cleanup EXIT

rsync -a "$ROOT_DIR/index.html" "$ROOT_DIR/web_bootstrap.py" "$ROOT_DIR/run.py" "$ROOT_DIR/src" "$PUBLISH_DIR/"
touch "$PUBLISH_DIR/.nojekyll"

git -C "$PUBLISH_DIR" init
git -C "$PUBLISH_DIR" branch -M gh-pages
git -C "$PUBLISH_DIR" remote add origin git@github.com:sejiseji/riverside.git
git -C "$PUBLISH_DIR" add .
git -C "$PUBLISH_DIR" commit -m "Publish Pyxel web page"
git -C "$PUBLISH_DIR" push --force-with-lease origin gh-pages
