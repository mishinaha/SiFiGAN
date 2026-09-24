# LibriTTS-R

LibriTTS-R は、LibriTTS の音声を改良版の音声合成モデルで再合成して音質を上げたデータセットである。
テキストと話者情報は LibriTTS と同じである。

- 公式ページ：https://google.github.io/df-conformer/librittsr/
- ダウンロード：https://www.openslr.org/141/
- ライセンス：CC BY 4.0

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

## SiFiGAN 作者の事前学習モデルでの使い方

README.md の 83 行目に次の記述がある。

> We used train-clean-100 and train-clean-360 in LibriTTS-R, and NUS-48E for training.

作者の事前学習モデルでの LibriTTS-R の使い方をまとめると、次のとおりである。

- train-clean-100 と train-clean-360 の両方を使う（合計約 460 時間）。
- train-other-500 は使っていない。
- 評価には test-clean を使う（`egs/` の SCP ファイルで確認した）。
- F0 抽出のパラメータは `minf0=60 maxf0=1000` で、デフォルトより範囲が広い。
- 学習ステップ数は 1,000,000 で、デフォルト（500k）の 2 倍である（`train=sifigan_1000k`）。

## フルスクラッチ学習での使用計画

### ストレージ方針

pakari の永続ストレージ（`/repo`）は 98GB しかない。
そこで、展開後に推定 ~60GB になる WAV ファイルはエフェメラルストレージに置く。

| 保存先 | 内容 | 備考 |
|---|---|---|
| エフェメラル (150GB) | tar.gzダウンロード→展開→tar.gz削除→WAV | 再起動で消えるが再ダウンロード可 |
| 永続 (/repo) | HDF5特徴量、チェックポイント、統計ファイル | 特徴量抽出済みなら学習にWAVは不要 |

### 処理の流れ

1. エフェメラルストレージに train-clean-100 と train-clean-360 をダウンロードして展開する。
2. ディスクを節約するため tar.gz を削除する。
3. 特徴量を抽出し、HDF5 を永続ストレージに保存する。
4. 統計量を計算し、永続ストレージに保存する。
5. 学習を始める。学習は HDF5 だけを参照し、WAV は使わない。
6. コンテナを再起動した後も、HDF5 から学習を再開できる。

### 容量の見積もり

| 項目 | サイズ (概算) | 保存先 |
|---|---|---|
| train-clean-100 (tar.gz) | ~6 GB | エフェメラル (一時) |
| train-clean-360 (tar.gz) | ~28 GB | エフェメラル (一時) |
| 展開後WAV | ~60 GB | エフェメラル |
| HDF5特徴量 | 5〜15 GB | 永続 |
| チェックポイント | 数GB | 永続 |
