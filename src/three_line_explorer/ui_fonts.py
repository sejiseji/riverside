from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from three_line_explorer.config import (
    INSPECTION_BODY_FONT_SIZE,
    INSPECTION_FONT_PATH,
    INSPECTION_TITLE_FONT_SIZE,
)


@dataclass(frozen=True, slots=True)
class UIFontSet:
    title: Any
    body: Any


def load_ui_fonts(pyxel: Any, font_path: str = INSPECTION_FONT_PATH) -> UIFontSet:
    errors: list[str] = []
    for path in asset_path_candidates(font_path):
        try:
            return UIFontSet(
                title=pyxel.Font(path, INSPECTION_TITLE_FONT_SIZE),
                body=pyxel.Font(path, INSPECTION_BODY_FONT_SIZE),
            )
        except Exception as exc:
            errors.append(f"{path}: {type(exc).__name__}")
    raise FileNotFoundError(
        "Japanese UI font could not be loaded. Tried: " + " / ".join(errors)
    )


def asset_path_candidates(relative_path: str) -> tuple[str, ...]:
    module_dir = Path(__file__).resolve().parent
    candidates = [
        relative_path,
        f"riverside/{relative_path}",
        str(module_dir.parent / relative_path),
        str(module_dir.parent.parent / relative_path),
    ]
    return tuple(dict.fromkeys(candidates))
