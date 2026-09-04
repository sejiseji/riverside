"""Fixed story content for riverside's drift-item system.

This module deliberately separates three narrative channels:

* ambient drift items: compact, randomly selected world fragments
* owner letters: long, fixed-order messages that advance the main story
* memory echoes: short, fixed-order recollections of the cat's former life

The owner letters never contain the detailed hospital / shower / nail-clipping /
belly / winter / seasonal episodes. Those are isolated in MEMORY_ECHOES so the
main letter sequence stays focused on the owner's current situation, the city's
collapse, and the cat's safety.

The 14 story entries reuse 14 sprite slots from the original 100-item source
atlas. Those slots are excluded from the default ambient random pool. This keeps
one stable 100-sprite atlas while changing the content split to:

    86 ambient random items + 8 owner letters + 6 memory echoes = 100 entries
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final, TypeVar


class StoryContentKind(str, Enum):
    OWNER_LETTER = "owner_letter"
    MEMORY_ECHO = "memory_echo"


@dataclass(frozen=True, slots=True)
class StoryInspectionDefinition:
    content_id: str
    title: str
    lead: str
    pages: tuple[str, ...]
    kind: StoryContentKind

    # Position in the single intentional story sequence.
    sequence_index: int

    # A..R is represented as 0..17.
    min_area_index: int
    max_area_index: int

    # Ambient items that should normally be inspected after the previous
    # story beat before this beat is eligible. Passing max_area_index forces
    # eligibility so the player cannot permanently miss the beat.
    min_ambient_inspections_before: int

    # Existing 32x24 source sprite reused by this logical story item.
    sprite_id: str

    archive_key: str
    owner_handwriting: bool
    persistent_until_read: bool = True

    @property
    def text_key(self) -> str:
        return self.content_id


OWNER_LETTERS: Final[tuple[StoryInspectionDefinition, ...]] = (
    StoryInspectionDefinition(
        content_id="owner_letter_01",
        title="青い袋の切れ端",
        lead="見覚えのある筆跡。目で追うと、主人の声になる。",
        pages=(
            "預かってくれて助かる。カリカリは青い袋。朝と夜、器の内側の線まで。空の皿を見せてくると思うけれど、追加は少しだけにしてくれ。",
            "中央水路の点検が終わらない。小さな水源が一つ、止めてもすぐに動き出す。今夜には戻れると思っていたけれど、もう少しかかりそうだ。",
            "戸口で待っていたら、今日は帰らないと話してやってほしい。言葉は分からなくても、声は覚えている。帰ったら、私からもちゃんと謝る。",
        ),
        kind=StoryContentKind.OWNER_LETTER,
        sequence_index=0,
        min_area_index=2,
        max_area_index=3,
        min_ambient_inspections_before=1,
        sprite_id="grocery_note",
        archive_key="owner_letter_01",
        owner_handwriting=True,
    ),
    StoryInspectionDefinition(
        content_id="owner_letter_02",
        title="防水作業票",
        lead="水に濡れても、文字だけははっきり残っている。",
        pages=(
            "西区の小水源が連続して起動している。一つずつは弱い。それなのに、近くの術式を呼び起こし、止めた場所からまた動き始める。",
            "市の技師は、明朝までには閉じられると言っている。念のため、窓を閉めておいてくれ。水音が近くなったら、あいつと一緒に上の階へ移ってほしい。",
            "水は多めに置いてやってくれ。私がいないと飲まないことがある。器をいつもの場所へ置けば、そのうち諦めて飲むはずだ。",
        ),
        kind=StoryContentKind.OWNER_LETTER,
        sequence_index=2,
        min_area_index=4,
        max_area_index=5,
        min_ambient_inspections_before=2,
        sprite_id="calibration_tag",
        archive_key="owner_letter_02",
        owner_handwriting=True,
    ),
    StoryInspectionDefinition(
        content_id="owner_letter_03",
        title="警報板の裏",
        lead="表には避難経路。裏側には、急いで書かれた文字。",
        pages=(
            "警報が三度鳴った。一度目は誤作動だと思った。二度目には南水門が開き、三度目の今は、誰も原因を断定できていない。",
            "小さな術式同士が、互いを起こし続けているらしい。壊れているというより、勝手に役目を増やしているように見える。私は中央の制御区画へ移る。",
            "そちらまで音が届いていたら、あいつの近くにいてやってくれ。隠れているなら、無理に出さなくていい。姿が見えなくても、同じ部屋に誰かがいれば落ち着く。",
        ),
        kind=StoryContentKind.OWNER_LETTER,
        sequence_index=4,
        min_area_index=6,
        max_area_index=7,
        min_ambient_inspections_before=2,
        sprite_id="marker_warning_plate",
        archive_key="owner_letter_03",
        owner_handwriting=True,
    ),
    StoryInspectionDefinition(
        content_id="owner_letter_04",
        title="浮いた通信ケース",
        lead="通信機は空だった。内側に折り畳まれた紙が入っている。",
        pages=(
            "通話が止まった。送信灯は点くけれど、どこにもつながらない。これが届くか分からないから、封をして川へ流す。",
            "橋の南側は沈んだ。まだ通れる道もあるが、こちらへ来ないでくれ。もしこの手紙を受け取ったら、古い橋の手すりへ青い布を結んでほしい。",
            "中央塔から見えるかもしれない。君たちが無事だと分かるだけでいい。あいつの姿まで見えなくても、そちらにいると信じられる。",
        ),
        kind=StoryContentKind.OWNER_LETTER,
        sequence_index=6,
        min_area_index=8,
        max_area_index=9,
        min_ambient_inspections_before=2,
        sprite_id="voice_reed",
        archive_key="owner_letter_04",
        owner_handwriting=True,
    ),
    StoryInspectionDefinition(
        content_id="owner_letter_05",
        title="避難扉の番号札",
        lead="番号札の裏まで文字で埋まっている。",
        pages=(
            "避難扉が何度も勝手に開く。閉めても、別の区画で同じことが起きる。扉だけでなく、昇降機や搬送路まで水の流れに合わせて動き始めた。",
            "そちらの戸締まりを確認してくれ。もしあいつが外へ出たら、川沿いを上る可能性がある。追い立てると余計に離れる。川とあいつの間へ回ってほしい。",
            "カリカリの袋を鳴らせば、少なくとも一度は振り向く。見つけても叱らないでくれ。私の匂いを追っているだけかもしれない。",
        ),
        kind=StoryContentKind.OWNER_LETTER,
        sequence_index=8,
        min_area_index=10,
        max_area_index=11,
        min_ambient_inspections_before=2,
        sprite_id="closure_tag",
        archive_key="owner_letter_05",
        owner_handwriting=True,
    ),
    StoryInspectionDefinition(
        content_id="owner_letter_06",
        title="導水管の覆い",
        lead="金属板は大きく曲がっている。文字は、そのへこみを避けて続いている。",
        pages=(
            "水が通りを越えた。低い区画は、もう屋根しか見えない。浮上設備が壊れたはずなのに、都市の一部は沈まず、水を抱えたまま上へ動いている。",
            "私は中央塔の排水を止めに行く。完全には止められなくても、下流へ出る量を減らせるかもしれない。ここを離れると、開いた水路がさらに広がる。",
            "迎えには行けない。行かないんじゃない。君にも、あいつにも、それを直接伝える方法がないことがつらい。",
            "あいつを上流へ近づけないでくれ。こちらの水は、もう普通の水ではない。物も、音も、触れた者の考えまで運んでいるように見える。",
        ),
        kind=StoryContentKind.OWNER_LETTER,
        sequence_index=10,
        min_area_index=12,
        max_area_index=13,
        min_ambient_inspections_before=2,
        sprite_id="shutoff_handle",
        archive_key="owner_letter_06",
        owner_handwriting=True,
    ),
    StoryInspectionDefinition(
        content_id="owner_letter_07",
        title="表札の欠片",
        lead="爪で引っかいた古い傷が残っている。その横に、主人の文字がある。",
        pages=(
            "家の一階まで水が入った。表札を外し、玄関の鈴を上の窓へ結んだ。家そのものが残るかは分からない。それでも、目印くらいは置いておきたい。",
            "水に触れた道具が、持ち主の動きを繰り返すことがある。誰もいない机でペンが走り、空の部屋で照明が点く。単なる記録の再生ではないらしい。",
            "昨夜、しばらく自分ではない高さから部屋を見ていた。床が近く、音が大きく、匂いに形があるように感じた。気のせいだと思いたい。",
            "もしあいつが何もない場所を見つめるようになったら、怖がらせないでくれ。こちらからも、何かが触れているのかもしれない。ただし、近づけさせてはいけない。",
        ),
        kind=StoryContentKind.OWNER_LETTER,
        sequence_index=12,
        min_area_index=14,
        max_area_index=15,
        min_ambient_inspections_before=2,
        sprite_id="half_doorplate",
        archive_key="owner_letter_07",
        owner_handwriting=True,
    ),
    StoryInspectionDefinition(
        content_id="owner_letter_08",
        title="密封された伝言筒",
        lead="筒は古い。けれど、文字だけはまだ乾ききっていない。",
        pages=(
            "君へ。これが何通目なのか分からない。塔の時計と空の明るさが合わなくなり、書いたはずの紙が、書く前の机へ戻っていることがある。",
            "中央区画は、都市から切り離された。上にいるのか、水底にいるのか、それさえ正しく言えない。外へ出る道を探しているが、同じ階段へ何度も戻される。",
            "もしあいつがもうそちらにいないなら、川を上っている。私なら、あいつはそうすると考える。見つけても叱らないでくれ。置いていかれたと思っているかもしれない。",
            "ここから先は、あいつに読んで聞かせてほしい。置いていったんじゃない。帰れなくなっただけだ。私が帰らないことを、おまえのせいにしなくていい。",
            "待っていてとは言わない。おまえは自分で行く場所を決めるから。危ない水を避けて、生きていてくれ。私も、まだ帰る道を探している。",
        ),
        kind=StoryContentKind.OWNER_LETTER,
        sequence_index=13,
        min_area_index=16,
        max_area_index=17,
        min_ambient_inspections_before=1,
        sprite_id="sealed_message_tube",
        archive_key="owner_letter_08",
        owner_handwriting=True,
    ),
)


MEMORY_ECHOES: Final[tuple[StoryInspectionDefinition, ...]] = (
    StoryInspectionDefinition(
        content_id="memory_echo_01_spring_clinic",
        title="錆びた診療帯",
        lead="苦い匂いが、白い壁の記憶を連れてくる。",
        pages=(
            "金属の扉。白い壁。知らない匂い。帰り道、主人は何度も名前を呼んだ。家に着いてから、しばらく顔を見ないことにした。",
        ),
        kind=StoryContentKind.MEMORY_ECHO,
        sequence_index=1,
        min_area_index=3,
        max_area_index=4,
        min_ambient_inspections_before=1,
        sprite_id="clinic_band",
        archive_key="memory_echo_01_spring_clinic",
        owner_handwriting=False,
    ),
    StoryInspectionDefinition(
        content_id="memory_echo_02_summer_shower",
        title="肉球柄のタオル",
        lead="水と泡の匂いが残っている。",
        pages=(
            "水。泡。逃げられない腕。鏡の中に、脚ばかり長いガリガリの謎生物がいた。乾くと、いつもの自分に戻った。",
        ),
        kind=StoryContentKind.MEMORY_ECHO,
        sequence_index=3,
        min_area_index=5,
        max_area_index=6,
        min_ambient_inspections_before=1,
        sprite_id="paw_print_towel",
        archive_key="memory_echo_02_summer_shower",
        owner_handwriting=False,
    ),
    StoryInspectionDefinition(
        content_id="memory_echo_03_autumn_nails",
        title="毛の残るブラシ",
        lead="手入れ道具の匂いに、逃げ道を探した感覚が重なる。",
        pages=(
            "主人の手。友人の手。大きなタオル。逃げる。捕まる。また逃げる。前脚一本だけで、みんな疲れていた。",
        ),
        kind=StoryContentKind.MEMORY_ECHO,
        sequence_index=5,
        min_area_index=7,
        max_area_index=8,
        min_ambient_inspections_before=1,
        sprite_id="furred_brush",
        archive_key="memory_echo_03_autumn_nails",
        owner_handwriting=False,
    ),
    StoryInspectionDefinition(
        content_id="memory_echo_04_winter_blanket",
        title="色あせた布",
        lead="乾いた布の奥に、冬の匂いがある。",
        pages=(
            "寒い夜。主人の胸はあたたかく、少しうるさい。降ろされても戻る。そこは自分の場所だった。",
        ),
        kind=StoryContentKind.MEMORY_ECHO,
        sequence_index=7,
        min_area_index=9,
        max_area_index=10,
        min_ambient_inspections_before=1,
        sprite_id="faded_towel",
        archive_key="memory_echo_04_winter_blanket",
        owner_handwriting=False,
    ),
    StoryInspectionDefinition(
        content_id="memory_echo_05_belly_trap",
        title="片方の手袋",
        lead="手の形を見ていると、腹の毛がむずむずする。",
        pages=(
            "腹を見せる。主人の手が来る。噛む。後ろ脚で蹴る。主人が痛いと言う。次の日も、同じ罠にかかった。",
        ),
        kind=StoryContentKind.MEMORY_ECHO,
        sequence_index=9,
        min_area_index=11,
        max_area_index=12,
        min_ambient_inspections_before=1,
        sprite_id="single_glove",
        archive_key="memory_echo_05_belly_trap",
        owner_handwriting=False,
    ),
    StoryInspectionDefinition(
        content_id="memory_echo_06_four_seasons_window",
        title="窓の留め金",
        lead="いつも届かなかった高さの金具。今なら簡単に触れられる。",
        pages=(
            "春は、床にできる光の四角。夏は、廊下の冷たい場所。秋は、積まれた毛布。冬は、主人の体温。家は季節ごとに、違う匂いがした。",
        ),
        kind=StoryContentKind.MEMORY_ECHO,
        sequence_index=11,
        min_area_index=13,
        max_area_index=14,
        min_ambient_inspections_before=1,
        sprite_id="window_latch",
        archive_key="memory_echo_06_four_seasons_window",
        owner_handwriting=False,
    ),
)


STORY_CONTENT: Final[tuple[StoryInspectionDefinition, ...]] = tuple(
    sorted((*OWNER_LETTERS, *MEMORY_ECHOES), key=lambda item: item.sequence_index)
)

STORY_CONTENT_BY_ID: Final[dict[str, StoryInspectionDefinition]] = {
    item.content_id: item for item in STORY_CONTENT
}

STORY_SEQUENCE_IDS: Final[tuple[str, ...]] = tuple(
    item.content_id for item in STORY_CONTENT
)

STORY_RESERVED_SPRITE_IDS: Final[frozenset[str]] = frozenset(
    item.sprite_id for item in STORY_CONTENT
)

OWNER_LETTER_IDS: Final[tuple[str, ...]] = tuple(
    item.content_id for item in OWNER_LETTERS
)

MEMORY_ECHO_IDS: Final[tuple[str, ...]] = tuple(
    item.content_id for item in MEMORY_ECHOES
)


InspectionTextT = TypeVar("InspectionTextT")


def instantiate_story_inspection_texts(
    inspection_text_type: type[InspectionTextT],
) -> dict[str, InspectionTextT]:
    """Adapt all fixed story entries to riverside's InspectionText class."""

    return {
        item.text_key: inspection_text_type(
            title=item.title,
            pages=item.pages,
        )
        for item in STORY_CONTENT
    }


def get_story_content(content_id: str) -> StoryInspectionDefinition:
    try:
        return STORY_CONTENT_BY_ID[content_id]
    except KeyError as exc:
        raise KeyError(f"Unknown story content id: {content_id}") from exc


def validate_story_content() -> None:
    if len(OWNER_LETTERS) != 8:
        raise ValueError(f"Expected 8 owner letters, got {len(OWNER_LETTERS)}")

    if len(MEMORY_ECHOES) != 6:
        raise ValueError(f"Expected 6 memory echoes, got {len(MEMORY_ECHOES)}")

    if len(STORY_CONTENT) != 14:
        raise ValueError(f"Expected 14 story entries, got {len(STORY_CONTENT)}")

    if len(STORY_CONTENT_BY_ID) != len(STORY_CONTENT):
        raise ValueError("Duplicate story content_id detected")

    if len(STORY_RESERVED_SPRITE_IDS) != len(STORY_CONTENT):
        raise ValueError("Each story entry must use a distinct sprite slot")

    expected_indexes = tuple(range(len(STORY_CONTENT)))
    actual_indexes = tuple(item.sequence_index for item in STORY_CONTENT)
    if actual_indexes != expected_indexes:
        raise ValueError(
            f"Story sequence indexes must be contiguous: {actual_indexes}"
        )

    forbidden_memory_terms = (
        "病院",
        "シャワー",
        "爪切り",
        "ガリガリの謎生物",
        "腹を見せ",
        "後ろ脚で蹴",
        "毛布を半分",
    )

    for item in STORY_CONTENT:
        if not item.content_id:
            raise ValueError("Empty story content_id")
        if not item.title.strip():
            raise ValueError(f"{item.content_id}: empty title")
        if not item.lead.strip():
            raise ValueError(f"{item.content_id}: empty lead")
        if not item.pages or any(not page.strip() for page in item.pages):
            raise ValueError(f"{item.content_id}: empty page")
        if not 0 <= item.min_area_index <= item.max_area_index <= 17:
            raise ValueError(f"{item.content_id}: invalid area band")
        if item.min_ambient_inspections_before < 0:
            raise ValueError(
                f"{item.content_id}: invalid ambient inspection threshold"
            )

        if item.kind is StoryContentKind.OWNER_LETTER:
            if not 3 <= len(item.pages) <= 5:
                raise ValueError(
                    f"{item.content_id}: owner letter must have 3..5 pages"
                )
            joined = "".join(item.pages)
            for term in forbidden_memory_terms:
                if term in joined:
                    raise ValueError(
                        f"{item.content_id}: memory episode leaked into letter: {term}"
                    )
        elif item.kind is StoryContentKind.MEMORY_ECHO:
            if len(item.pages) != 1:
                raise ValueError(
                    f"{item.content_id}: memory echo must be one page"
                )


validate_story_content()
