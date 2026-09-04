# RIV013 統合コンテンツ・マニフェスト

## 集計

| 項目 | 件数 |
|---|---:|
| ベーススプライト枠 | 100 |
| 通常ランダム漂着物 | 86 |
| 主人の手紙 | 8 |
| 記憶エピソード | 6 |
| 有効調査コンテンツ | 100 |

## 予約した14スプライト枠

以下は標準ランダム抽選から除外し、固定物語コンテンツに再利用する。

- `calibration_tag`
- `clinic_band`
- `closure_tag`
- `faded_towel`
- `furred_brush`
- `grocery_note`
- `half_doorplate`
- `marker_warning_plate`
- `paw_print_towel`
- `sealed_message_tube`
- `shutoff_handle`
- `single_glove`
- `voice_reed`
- `window_latch`

## 実装契約

- スプライトはすべて32×24。
- 透過表記は `.`、実行時 `transparent_color=8`。
- 主人の手紙と記憶は `content_id` と `sprite_id` を分離する。
- 通常ランダム抽選は `exclude_story_reserved=True` が標準。
- 物語アイテムは出現時ではなく読了時に進行する。
- 未読の物語アイテムは消去しない。
- 有効なテキストレジストリは `instantiate_all_inspection_texts()` から生成する。
