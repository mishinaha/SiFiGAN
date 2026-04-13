# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SiFiGAN (Source-Filter HiFi-GAN) — a PyTorch implementation of a fast and pitch-controllable high-fidelity neural vocoder. Based on ICASSP 2023 paper by Reo Yoneyama (Nagoya University).

## Setup

uvで環境構築済み（Python 3.11, PyTorch 2.11.0+cu130）。

```bash
uv sync --python 3.11
uv run sifigan-train ...   # コマンド実行は uv run 経由
```

pyproject.tomlで依存管理。setup.pyも残存するがpyproject.tomlが正。

## CLI Commands

All commands are installed as entry points. Hydra設定は `sifigan/bin/config/` 配下。

```bash
# Feature extraction (WORLD analysis → HDF5)
uv run sifigan-extract-features audio=data/scp/<dataset>.scp

# Compute normalization statistics
uv run sifigan-compute-statistics feats=data/scp/<dataset>.list stats=data/stats/<dataset>.joblib

# Training
uv run sifigan-train generator=sifigan discriminator=univnet train=sifigan data=<dataset> out_dir=exp/sifigan

# Inference / decoding
uv run sifigan-decode generator=sifigan data=<dataset> out_dir=exp/sifigan checkpoint_steps=400000

# Analysis-synthesis
uv run sifigan-anasyn generator=sifigan data=<dataset> out_dir=exp/sifigan checkpoint_steps=400000
```

## Architecture

### Two-Network Generator (SiFiGAN)

`sifigan/models/generator.py`: **SiFiGANGenerator** splits synthesis into a **Source Network** (excitation signal using `AdaptiveResidualBlock` with F0-dependent dilation factors) and a **Filter Network** (spectral resonance using standard `ResidualBlock`). **HiFiGANGenerator** is the baseline single-network variant.

### Signal Generation

`sifigan/utils/features.py`: `SignalGenerator` creates sine waves and noise from F0 contours. `dilated_factor()` computes pitch-adaptive dilation factors.

### Discriminators

`sifigan/models/discriminator.py`:
- **UnivNetMultiResolutionMultiPeriodDiscriminator**: multi-resolution spectral + multi-period (default for SiFiGAN)
- **HiFiGANMultiScaleMultiPeriodDiscriminator**: multi-scale + multi-period (baseline)

### Loss Functions

`sifigan/losses/`: mel.py (Mel-spectral L1, weight 45.0), reg.py (source regularization), adv.py (adversarial + feature matching)

### Training Pipeline

`sifigan/bin/train.py`: AudioFeatDataset → Collater (signal generation + dilation factors) → Generator → Discriminator → Loss (mel + reg + adv + fm)

### Feature Extraction

`sifigan/bin/extract_features.py`: WORLD vocoder analysis → HDF5 (`/f0`, `/cf0`, `/mcep`, `/bap`)。`path_replace()` で `in_dir="wav"` → `out_dir="hdf5"` の文字列置換を行うため、WAVファイルは `{speaker}/wav/{file}.wav` のパス構造が必要。

### Configuration

Hydra config hierarchy in `sifigan/bin/config/`:
- `generator/`: sifigan.yaml, hifigan.yaml
- `discriminator/`: univnet.yaml, hifigan.yaml
- `train/`: sifigan.yaml, hifigan.yaml, sifigan_1000k.yaml
- `data/`: dataset-specific (sample rate, hop size, dense factors)

## 現在の作業: フルスクラッチ学習

作者提供の事前学習モデルはLibriTTS-RとNUS-48Eで学習されているが、NUS-48Eはライセンスや入手方法が不明確で再現性に問題がある。そこでデータセットをLibriTTS-R (train-clean-100 + train-clean-360) とVocalSet 1.1 (straight + vibrato) に差し替えてフルスクラッチ学習を行う。

データセットの詳細は `doc/VocalSet.md`, `doc/LibriTTS-R.md` を参照。データ準備の作業記録は `doc/Prepare.md` を参照。

### 学習環境 (pakari)

- アクセス: `ssh pakari`
- OS: Ubuntu 24.04 (コンテナ)、エフェメラル（再起動で消える）
- GPU: NVIDIA RTX PRO 6000 Blackwell Server Edition (VRAM 96GB)
- CUDA: 13.0 / Driver 580.126.09
- CPU: 96コア / RAM: 1.5TB
- 永続ストレージ: `/data/share159` (NFS, 98GB)、`/repo` → `/data/share159` のシンボリックリンク（再起動で消えるため `sudo ln -sf /data/share159 /repo` で再作成）
- Python環境: uv (`/repo/.local/bin/uv`) + .venv (`/repo/SiFiGAN/.venv/`, Python 3.11)
- HDF5保存先: B2 Storage (`s3://pakari/`) にtar.gzでバックアップ、使用時にエフェメラルに展開

### 未解決の課題

- VocalSetのWAVは44.1kHzだが、SiFiGANは24kHzを期待 → 事前リサンプリングが必要
- VocalSet HDF5はリサンプリング後に再抽出・B2アップロード予定

## Git運用

- コミットメッセージは日本語で書くこと
- こまめにコミットすること
