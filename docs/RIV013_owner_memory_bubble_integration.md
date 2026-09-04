# Integration example

```python
from .owner_memory_bubble_sprites import (
    animation_frame_index,
    build_owner_memory_bubble_atlas,
    draw_owner_memory_bubble,
)


class App:
    def __init__(self) -> None:
        # pyxel.init(...) の後
        self.owner_memory_atlas = build_owner_memory_bubble_atlas()
        self.owner_memory_elapsed = 0

    def open_inspection_panel(self, object_id: str) -> None:
        self.owner_memory_elapsed = 0
        # 既存のパネル開始処理

    def update(self) -> None:
        if self.inspection.panel_open:
            self.owner_memory_elapsed += 1

    def draw(self) -> None:
        self.draw_world()
        self.draw_player()

        if self.inspection.panel_open:
            head_screen = self.project_player_head()

            if head_screen is not None:
                frame = animation_frame_index(
                    self.owner_memory_elapsed
                )
                draw_owner_memory_bubble(
                    self.owner_memory_atlas,
                    frame_index=frame,
                    cat_head_screen_x=head_screen.x,
                    cat_head_screen_y=head_screen.y,
                )

        self.draw_inspection_panel()
```

## Suggested display policy

主人の存在感を特別に保つ場合は、以下の条件が自然です。

```python
show_owner_memory = content_kind in {
    InspectionContentKind.OWNER_LETTER,
    InspectionContentKind.MEMORY_ECHO,
}
```

通常漂着物でも常時表示したい場合、上の条件を
`self.inspection.panel_open` のみに変更できます。
