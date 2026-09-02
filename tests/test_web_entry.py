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
