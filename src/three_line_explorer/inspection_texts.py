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
    "driftwood": InspectionText(
        title="流木",
        pages=(
            "角の丸くなった木片が、浅瀬に引っかかっている。",
            "水に削られた表面だけが、妙にすべすべしている。",
        ),
    ),
    "weathered_forest_sign": InspectionText(
        title="古びた看板",
        pages=(
            "文字はほとんど消えている。かろうじて、川へ近づくな、という一文だけが読める。",
            "板の裏側には、誰かが小さく日付を刻んだ跡がある。",
        ),
    ),
}
