# riverside RIV014.5 環境アセットパック

## 収録内容

- FAR 64x32: 4枚。遠い木立ち、光、遠景の川
- MID 64x48: 4枚。木立ち、低木、朽ちた巨木
- NEAR 64x64: 4枚。濃い樹冠、近い幹、草、光条
- 衝突物: 朽ちた木の幹、苔むした岩、古い看板、地蔵
- 調査物: 古い看板 (`weathered_forest_sign`)
- 非衝突: 草、シダ、ワラビ、フキ、ツクシ、若木

ゲーム実行時の主ファイルは
`src/three_line_explorer/generated_environment_assets.py` です。
プレビューPNGは確認用であり、ランタイム依存ではありません。

## 透過契約

本パックは各アセットで `transparent_color=8` を使用します。
`.` はコンパイル時に8へ置換されます。これはグローバル予約ではなく、
そのアセットを `pyxel.blt(..., colkey=8)` で描く場合だけ有効です。
したがって、本パック内では可視色8を使っていません。

別アセットが `transparent_color=2` の場合、そのアセットでは色8を可視色にできます。

## 既存 PixelMapSource への接続

```python
from .generated_environment_assets import instantiate_pixel_map_sources

sources = instantiate_pixel_map_sources(PixelMapSource)
```

ファクトリは次を受け取る想定です。

```python
PixelMapSource(
    width=...,
    height=...,
    rows=...,
    transparent_color=...,
)
```

## パララックス順序

各レイヤーは `a -> b -> c -> d` の固定順です。4枚は256px幅の連続景観から
切り出しているので、この順で並べてループさせます。

初期速度係数案:

```python
FAR_PIXELS_PER_WORLD = 0.04
MID_PIXELS_PER_WORLD = 0.10
NEAR_PIXELS_PER_WORLD = 0.18
```

ショットIDでスクロール方向を分岐せず、現在のカメラ基底を使います。
背景はスクリーン上部の固定帯ではなく、可視領域の奥側Zエッジの外側へ
立てたビルボードタイルとして投影します。

```python
screen_x_orientation = camera_snapshot.right.x
scroll_world = (
    player.x * pixels_per_world * screen_x_orientation
)
layer_z = far_edge_z + farther_z_direction * z_offset
```

## 描画順

```text
空のベース色
FAR
MID
NEAR
3D床・川
3D固形AABB
ワールドスプライトとプレイヤーの統合深度キュー
調査マーカー
UI
```

背景タイルは非接触であり、可視直方体や衝突処理へ登録しません。

## ワールドスプライトの重なり順

草木、山菜、衝突物、調査物、プレイヤーを同じ接地点深度キューへ入れます。
ライン番号だけで固定ソートしないでください。

```python
relative = world_anchor - camera_snapshot.position
camera_depth = relative.dot(camera_snapshot.forward)
lane_depth = world_anchor.z * camera_snapshot.forward.z
route_depth = world_anchor.x * camera_snapshot.forward.x

items.sort(
    key=lambda item: (
        -item.lane_depth,
        -item.route_depth,
        -(item.camera_depth + item.depth_bias),
        item.object_id,
    )
)
```

- 深度座標は画像中央ではなく地面との接地点
- プレイヤーも同じキューへ入れる
- X位置、Zライン、カメラA/B/C/Dは投影深度へ自然に反映される
- 同深度時は `object_id` で安定化
- 直方体面との統合描画では、カメラの左右回り込みに合わせた
  `lane_depth` と `route_depth` を先に使い、左右/奥手前の反転を扱う

## 衝突と調査

`SOLID` と `SOLID_INSPECTABLE` のみ衝突フットプリントを持ちます。
草木・山菜は0です。画像の不透明範囲と衝突AABBは別管理です。
看板の調査範囲も衝突AABBとは分けます。

地蔵は初期状態では調査不可ですが、後から `inspectable_text_key` を追加できます。

## テスト

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m compileall src tests
```

検査対象:

- 行数と1行の文字数
- 透明色のローカル予約
- FAR/MID/NEAR各4枚
- 必須オブジェクト
- 看板の調査属性
- 衝突種別とフットプリント
- 接地点アンカー
- コンパイル後が0〜fのみであること
