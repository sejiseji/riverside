from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InspectionText:
    title: str
    pages: tuple[str, ...]


INSPECTION_TEXTS: dict[str, InspectionText] = {
    "single_sandal": InspectionText(
        title="片方だけのサンダル",
        pages=(
            "水を吸って、すっかり重くなっている。片方だけが、川辺に残されていた。",
            "靴底には名前らしき文字がある。半分ほど削れていて、もう読めない。",
        ),
    ),
    "clouded_bottle": InspectionText(
        title="くもった小瓶",
        pages=(
            "中には水が少し入っている。蓋は固く閉じられていて、開きそうにない。",
            "長いあいだ流されていたのか、ガラスは白くくもっている。",
        ),
    ),
    "folded_note": InspectionText(
        title="折りたたまれたメモ",
        pages=(
            "紙は濡れているが、黒い線がいくつか透けて見える。",
            "ただのごみというより、誰かが大事に持っていたものに見える。",
        ),
    ),
}
