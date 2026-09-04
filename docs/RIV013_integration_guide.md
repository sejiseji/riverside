# Codex統合手順

## 1. コピー対象

`src/three_line_explorer/` の次の3ファイルを追加してください。

- `story_content.py`
- `story_progression.py`
- `inspection_content_registry.py`

`drift_item_randomizer.py` は、固定物語用14スロットを標準抽選から除外する
更新版で置換します。

## 2. テキストレジストリ

従来の `instantiate_inspection_texts()` を全面削除する必要はありません。
実ゲーム側では、新しい統合関数を使います。

```python
INSPECTION_TEXTS = instantiate_all_inspection_texts(InspectionText)
```

これにより、ランダム通常物86件と固定物語14件が、重複なしの100件に
なります。

## 3. スプライト

新規画像は不要です。物語14件は既存atlasの14スロットを再利用します。
`StoryInspectionDefinition.sprite_id` を描画側へ渡してください。

論理IDと画像IDは別です。

```text
text_key   = owner_letter_01
sprite_id  = grocery_note
```

## 4. ランダム出現

`select_drift_items()` の標準ポリシーは、物語予約スロットを除外します。
デバッグ時に旧100件を直接抽選したい場合のみ、次を指定します。

```python
DriftSelectionPolicy(exclude_story_reserved=False)
```

## 5. 固定物語出現

- 通常物の調査完了時に `record_ambient_inspection()`
- 配置更新時に `activate_next_story_item_if_due()`
- パネル読了時に `mark_story_item_read()`
- `StoryProgressState` をセーブ対象へ含める

物語アイテムの表示中断・カメラ移動で進行させず、最後のページを閉じた
時点でのみ `mark_story_item_read()` を呼ぶのが安全です。

## 6. UI

既存 `InspectionText` が `title` と `pages` のみでも動きます。
表示差分は `CONTENT_METADATA[text_key].kind` から判定できます。

- `AMBIENT`: コンパクト、ページ番号は1ページなら非表示
- `MEMORY_ECHO`: 1ページ、少し間を取る演出は任意
- `OWNER_LETTER`: 複数ページ、ページ番号・アーカイブ対象
