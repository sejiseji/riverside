# Owner memory bubble asset manifest

## Asset ID

`owner_memory_bubble_0` 〜 `owner_memory_bubble_3`

## Layout

| 項目 | 値 |
|---|---:|
| Frame width | 64 |
| Frame height | 64 |
| Frame count | 4 |
| Atlas width | 256 |
| Atlas height | 64 |
| Transparent color | 2 |
| Anchor X | 32 |
| Anchor Y | 62 |

## Frame intent

| Frame | 意図 |
|---:|---|
| 0 | 記憶が現れ始め、小さく微笑む |
| 1 | 目元と頬がやわらぐ |
| 2 | 目を細めて明確に微笑む |
| 3 | 最も穏やかな笑顔になり、雲が落ち着く |

標準ループは `0, 1, 2, 3, 2, 1`。主人の顔を高速に動かすのではなく、
雲と表情がゆっくり呼吸する程度の動きに留めます。

## Recommended draw anchor

猫のワールド頭部位置を画面へ投影し、その座標を
`draw_owner_memory_bubble()` へ渡します。

```python
head_world = Vec3(
    player.x,
    PLAYER_SIZE_Y + 5.0,
    player.z,
)
head_screen = projection.project(head_world, camera_snapshot)
```

プレイヤースプライトの画面矩形を既に持つ場合は、上辺中央を使用しても構いません。

## Layering

```text
背景
3D床・川
ワールドオブジェクト
プレイヤー
主人の記憶吹き出し
調査パネル
HUD
```

吹き出しはワールド衝突やPainterキューへ入れない2D演出です。
ただし3Dビューポートのクリップは適用してください。
