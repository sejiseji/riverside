from __future__ import annotations

from dataclasses import dataclass

from three_line_explorer.inspection_content_registry import instantiate_all_inspection_texts


@dataclass(frozen=True, slots=True)
class InspectionText:
    title: str
    pages: tuple[str, ...]


STAGE_INSPECTION_TEXTS: dict[str, InspectionText] = {
    "weathered_forest_sign": InspectionText(
        title="古びた看板",
        pages=(
            "文字はほとんど消えている。かろうじて、川へ近づくな、という一文だけが読める。",
            "板の裏側には、誰かが小さく日付を刻んだ跡がある。",
        ),
    ),
}


INSPECTION_TEXTS: dict[str, InspectionText] = {
    **instantiate_all_inspection_texts(InspectionText),
    **STAGE_INSPECTION_TEXTS,
}
