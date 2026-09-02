from __future__ import annotations

from pathlib import Path
from unittest import TestCase


class WebEntryTests(TestCase):
    def test_pages_entry_uses_pyxapp_play_route(self) -> None:
        html = Path("index.html").read_text(encoding="utf-8")

        self.assertIn("<pyxel-play", html)
        self.assertIn('name="riverside.pyxapp"', html)
        self.assertIn('gamepad="disabled"', html)

    def test_mobile_layout_uses_visible_viewport_fit(self) -> None:
        html = Path("index.html").read_text(encoding="utf-8")

        self.assertIn("--viewport-height", html)
        self.assertIn("visualViewport", html)
        self.assertIn("100svh", html)
        self.assertNotIn("height: 100dvh", html)

    def test_publish_script_writes_id_specific_pyxapp(self) -> None:
        script = Path("scripts/publish_pages.sh").read_text(encoding="utf-8")

        self.assertIn("PUBLISHED_APP_NAME=", script)
        self.assertIn("riverside-${CACHE_BUST_ID", script)
        self.assertIn("cp \"$PUBLISH_DIR/riverside.pyxapp\"", script)
        self.assertIn('name=\\"$PUBLISHED_APP_NAME\\"', script)
