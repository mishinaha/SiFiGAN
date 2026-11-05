# 2026-04-17 学習作業で ruthor 上で使ったスクリプト群

SiFiGAN フルスクラッチ学習 (→ `doc/260417-1-train.md`) の際に ruthor の `/tmp/` で作ったその場限りのスクリプト。
永続化のため参照用として収録している。
実行は想定していない。

egs 配下にも同作業に関連する再利用想定のスクリプトがある (使う順序と変更が必要な箇所は `egs/libritts-r-clean+vocalset11/README.md`):
- `egs/libritts-r-clean+vocalset11/run_train_ruthor.sh`：学習起動 (resume=300000 前提)
- `egs/libritts-r-clean+vocalset11/checkpoint_uploader.sh`：inotifywait による B2 自動アップロード
- `egs/libritts-r-clean+vocalset11/run_prepare.sh`：pakari 向けデータ準備 (ruthor では未使用)

## ファイル

### `resample_and_symlink.py`

pakari 消滅後に ruthor のエフェメラル `/root/data/` へ復元した WAV に対して:
1. VocalSet (44.1kHz) を soxr で 24 kHz にリサンプリング → `{singer}/wav_24k/` へ
2. VocalSet `{singer}/wav/` に wav_24k/ へのシンボリックリンク (straight + vibrato のみ)
3. LibriTTS-R の `{subset}/{speaker}/{chapter}/*.wav` を `{speaker}/wav/` へフラット化 (シンボリックリンク)

`path_replace()` が `"wav"` → `"hdf5"` の文字列置換を行う前提の SiFiGAN のパス規約に合わせる。

### `resample_24k.py`

`/root/anasyn/in/` の入力 WAV を単純に 24 kHz リサンプリングして `*_original_24k.wav` として `/root/anasyn/out/` に書き出す。
ボコーダ合成との比較用参照。

### `analyze_loss.py`

`/workspace/exp/sifigan_1000k/events.out.tfevents.*` のうち最大サイズのものから学習ロスを集計:
- 指定マイルストーン (300k, 400k, ..., 900k) での値
- 特定ステップ以降の「最初 10 点 vs 最新 10 点」平均の傾向 (収束判定用)
- 最終ステップでの全ロス

TensorBoard サーバを起動せずに CLI で進捗を確認するためのヘルパ。
