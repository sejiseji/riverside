from __future__ import annotations


def anchored_blt_origin(
    *,
    screen_x: float,
    screen_y: float,
    width: int,
    height: int,
    anchor_x: float,
    anchor_y: float,
    scale: float,
) -> tuple[int, int]:
    """Return the Pyxel blt origin that places a scaled source anchor at screen position."""
    center_x = (width - 1) * 0.5
    center_y = (height - 1) * 0.5
    return (
        round(screen_x - center_x - scale * (anchor_x - center_x)),
        round(screen_y - center_y - scale * (anchor_y - center_y)),
    )


def transformed_anchor(
    *,
    origin_x: float,
    origin_y: float,
    width: int,
    height: int,
    anchor_x: float,
    anchor_y: float,
    scale: float,
) -> tuple[float, float]:
    center_x = (width - 1) * 0.5
    center_y = (height - 1) * 0.5
    return (
        origin_x + center_x + scale * (anchor_x - center_x),
        origin_y + center_y + scale * (anchor_y - center_y),
    )


__all__ = [
    "anchored_blt_origin",
    "transformed_anchor",
]
