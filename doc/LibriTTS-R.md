# LibriTTS-R

LibriTTSの音声を改良版音声合成モデルで再合成し、音質を向上させたデータセット。元のテキスト・話者情報はLibriTTSと同一。

- 公式ページ: https://google.github.io/df-conformer/librittsr/
- ダウンロード: https://www.openslr.org/141/
- ライセンス: CC BY 4.0

## サブセット

| サブセット | tar.gz | 内容 |
|---|---|---|
| train-clean-100 | ~6 GB | クリーンな発話、約100時間 |
| train-clean-360 | ~28 GB | クリーンな発話、約360時間 |
| train-other-500 | ~33 GB | ややノイジーな発話、約500時間 |
| dev-clean | ~0.2 GB | 開発用 (クリーン) |
| dev-other | ~0.1 GB | 開発用 (その他) |
| test-clean | ~0.2 GB | テスト用 (クリーン) |
| test-other | ~0.2 GB | テスト用 (その他) |

## SiFiGAN作者の事前学習モデルでの使用

README.md (83行目) より:

> We used train-clean-100 and train-clean-360 in LibriTTS-R, and NUS-48E for training.

- **train-clean-100** と **train-clean-360** の両方を使用（合計約460時間）
- train-other-500は未使用
- 評価にはtest-cleanを使用（`egs/` のSCPファイルから確認）
- F0抽出パラメータ: `minf0=60 maxf0=1000`（デフォルトより広い範囲）
- 学習ステップ数: 1,000,000（デフォルト500kの2倍、`train=sifigan_1000k`）

## フルスクラッチ学習での使用計画

### ストレージ方針

pakariの永続ストレージ (`/repo`) は98GBしかないため、WAVファイル（展開後推定~60GB）はエフェメラルストレージに配置する。

| 保存先 | 内容 | 備考 |
|---|---|---|
| エフェメラル (150GB) | tar.gzダウンロード→展開→tar.gz削除→WAV | 再起動で消えるが再ダウンロード可 |
| 永続 (/repo) | HDF5特徴量、チェックポイント、統計ファイル | 特徴量抽出済みなら学習にWAVは不要 |

### 処理フロー

1. エフェメラルストレージにtrain-clean-100とtrain-clean-360をダウンロード・展開
2. tar.gzを削除してディスク節約
3. 特徴量抽出 → HDF5を永続ストレージに保存
4. 統計量計算 → 永続ストレージに保存
5. 学習開始（HDF5のみ参照、WAVは不要）
6. コンテナ再起動後もHDF5から学習再開可能

### 容量見積もり

| 項目 | サイズ (概算) | 保存先 |
|---|---|---|
| train-clean-100 (tar.gz) | ~6 GB | エフェメラル (一時) |
| train-clean-360 (tar.gz) | ~28 GB | エフェメラル (一時) |
| 展開後WAV | ~60 GB | エフェメラル |
| HDF5特徴量 | 5〜15 GB | 永続 |
| チェックポイント | 数GB | 永続 |
