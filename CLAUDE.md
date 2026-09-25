# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SiFiGAN (Source-Filter HiFi-GAN) — a PyTorch implementation of a fast and pitch-controllable high-fidelity neural vocoder. Based on ICASSP 2023 paper by Reo Yoneyama (Nagoya University).

フォークしてフルスクラッチ学習を完遂済み (1,000,000ステップ、2026-04-16完了)。
経緯と学び: `doc/260417-1-train.md`、関連文書: `doc/Prepare.md`, `doc/VocalSet.md`, `doc/LibriTTS-R.md`。

## Setup

uv (Python 3.11) で環境管理。

```bash
uv sync --python 3.11
uv run sifigan-train ...   # コマンドは uv run 経由
```

`pyproject.toml` が正、`setup.py` も残存するが従属。PyTorch は `find-links = ["https://download.pytorch.org/whl/cu128"]` 指定。
新しい GPU 環境では `uv pip install --index-url https://download.pytorch.org/whl/cu128 torch==2.11.0 torchaudio==2.11.0`
で CUDA ABI を合わせる必要がある場合あり (PyTorch 2.11.0+cu130 は Driver 12.8 系だと CUDA: False になる)。

## CLI Commands

All commands are installed as entry points. Hydra 設定は `sifigan/bin/config/` 配下。

```bash
uv run sifigan-extract-features audio=data/scp/<dataset>.scp
uv run sifigan-compute-statistics feats=data/scp/<dataset>.list stats=data/stats/<dataset>.joblib
uv run sifigan-train generator=sifigan discriminator=univnet train=sifigan_1000k data=<dataset> out_dir=exp/sifigan
uv run sifigan-decode  generator=sifigan data=<dataset> out_dir=exp/sifigan checkpoint_steps=1000000
uv run sifigan-anasyn  generator=sifigan in_dir=<wav_dir> out_dir=<out> stats=<stats.joblib> checkpoint_path=<ckpt.pkl> "f0_factors=[0.5,1.0,2.0]"
```

学習再開は `train.resume=<steps>` を追加。`sifigan-anasyn` は作者提供の旧形式チェックポイントも
`weights_only=False` 指定で読み込める (commit `a6e3813` で対応済み)。

## Architecture

### Two-Network Generator (SiFiGAN)

`sifigan/models/generator.py`: **SiFiGANGenerator** は合成を **Source Network** (F0依存ダイレーションを持つ `AdaptiveResidualBlock` による励振信号生成) と **Filter Network** (通常の `ResidualBlock` によるスペクトル共鳴) に分離。**HiFiGANGenerator** はベースライン単一ネットワーク版。

### Signal Generation

`sifigan/utils/features.py`: `SignalGenerator` が F0 輪郭から正弦波とノイズを生成。`dilated_factor()` はピッチ適応ダイレーション係数を計算。
**注**: `sinusoid()`/`sinusoids()` は数値精度のため内部で `float64` を使うが、出力は入力 dtype に戻す (そうしないと generator で dtype 不一致エラー)。

### Discriminators

`sifigan/models/discriminator.py`:
- **UnivNetMultiResolutionMultiPeriodDiscriminator**: SiFiGAN のデフォルト
- **HiFiGANMultiScaleMultiPeriodDiscriminator**: HiFi-GAN ベースライン

### Training Pipeline

`sifigan/bin/train.py`: `AudioFeatDataset` → `Collater` (signal generation + dilation factors) → Generator → Discriminator → Loss (mel=45.0 + reg=1.0 + adv=1.0 + fm=2.0)。
チェックポイントは `save_interval_steps` (既定 100k) ごと、評価は `eval_interval_steps` (既定 2k) ごと。

### Feature Extraction

`sifigan/bin/extract_features.py`: WORLD vocoder 分析 → HDF5 (`/f0`, `/cf0`, `/mcep`, `/bap`, `/uv`)。
**重要**: `path_replace()` で `in_dir="wav"` → `out_dir="hdf5"` の**文字列置換**を行うため、
WAVは必ず `{speaker}/wav/{file}.wav` のパス構造にシンボリックリンクで再配置する必要がある。

### Configuration

Hydra config は `sifigan/bin/config/` 配下:
- `generator/`: sifigan.yaml, hifigan.yaml
- `discriminator/`: univnet.yaml, hifigan.yaml
- `train/`: sifigan.yaml, hifigan.yaml, sifigan_1000k.yaml (LRスケジュール [200k/400k/600k/800k] で半減)
- `data/`: データセット別 (sample_rate, hop_size, dense_factors, batch_size, num_workers)

## 学習成果物の在処

B2 Storage `s3://pakari/` (Backblaze, endpoint `s3.us-west-004.backblazeb2.com`, bucket `pakari`):
- `exp/sifigan_1000k/checkpoints/checkpoint-{100000..1000000}steps.pkl` (各 584 MiB)
- `exp/sifigan_1000k/events.out.tfevents.*` (TensorBoardログ, pakari期 + ruthor期)
- `exp/sifigan_1000k/config.yaml` (学習時設定)
- `stats/libritts_r_clean+vocalset11_train_no_dev.joblib`
- `libritts_r_hdf5.tar.gz` (59.3 GiB), `vocalset11_hdf5.tar.gz` (508 MiB, 24kHzリサンプリング済み)
- `logs/*.log` (prepare, vocalset_resample, compute_statistics, train, checkpoint_upload)
- `author/` (比較検証用の作者事前学習モデル + stats)

認証情報は `.env` の `B2_APPLICATION_KEY_ID` (キー ID) と `B2_APPLICATION_KEY` (シークレット) を参照。CLI は `uv tool install awscli` で導入し、
`aws --endpoint-url https://s3.us-west-004.backblazeb2.com s3 ...` で操作。

## 学習環境 (参考)

### ruthor (現行、RunPod RTX 5090 Pod)

- `ssh ruthor`、Ubuntu 24.04、エフェメラル300GB + `/workspace` 100GB (MooseFS)
- GPU: RTX 5090 32GB (Driver 12.8 系)
- 学習データは必ず**エフェメラル** `/root/data/` に配置すること。MooseFS は小ファイル書き込みが60-90倍遅い
- Pod 停止中でもディスクは残るが、Pod 消滅時は B2 から復元する想定で設計 (`doc/260417-1-train.md` 参照)

### 再学習・推論の入り口

- 学習再開: `egs/libritts-r-clean+vocalset11/run_train_ruthor.sh` (resume=300000 前提、パス調整して使う)
- B2自動アップロード: `egs/libritts-r-clean+vocalset11/checkpoint_uploader.sh` (inotifywait で `.pkl` を監視)
- データ準備: `egs/libritts-r-clean+vocalset11/run_prepare.sh` (pakari向けだがロジックは流用可能)

`reference/script/260417/` に ruthor 上で使ったその場限りスクリプト (リサンプリング, ロス集計等) も保全。

## 開発上の留意点

### tmux + ログのリダイレクト

長時間タスクは必ず tmux セッション内で実行し、**stderr をファイルにリダイレクト**する。
ssh 切断時にパイプブロックで1時間以上フリーズした事例あり (tar の uid/gid 警告が stderr に流れ続けてパイプが詰まる)。

### シンボリックリンクと find

`egs/.../LibriTTS_R` や `VocalSet11` はシンボリックリンクなので、`find` は **必ず `-L` オプション** で辿ること
(`find -L path -name "*.h5"`)。`-type l` は指定しない。

### 長時間タスクの待ち方

`ScheduleWakeup` によるポーリングは使わない (`.claude/rules/long-running-tasks.md`)。
SSH 先でブロッキングループし、Bash tool の foreground (最大10分) で待つのが定石。

### ロギングの必須項目

学習・前処理実行時は以下を必ずログに残す (`.claude/rules/logging.md`):
- 実行時の Git コミットハッシュとブランチ
- 実行コマンド全文とパラメータ
- 入出力ファイル数・サイズ、所要時間
- 永続ストレージ (`/workspace/logs/`) + B2 (`s3://pakari/logs/`) の両方に保存

## Git 運用

- コミットメッセージは**日本語**で書く
- こまめにコミット (機能単位、修正単位で区切る)
- メインブランチは `main`、現行作業は `bleeding`
- 破壊的操作 (force push 等) は明示的に指示されない限り行わない

## 既知の制約

- 極端な F0 (非常に低い声/高い声) でノイズ化や F0 変更が効かない区間が散発的に発生する。
  作者の事前学習モデルでも同様に再現するため、SiFiGAN のアーキテクチャ/特徴量抽出パイプライン起因と推測。
  現状は未対応 (詳細は `doc/260417-1-train.md` §5)。
