# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SiFiGAN (Source-Filter HiFi-GAN) — a PyTorch implementation of a fast and pitch-controllable high-fidelity neural vocoder. Based on ICASSP 2023 paper by Reo Yoneyama (Nagoya University).

## Setup

```bash
pip install -e .
```

Key dependencies: torch>=1.9.0, torchaudio, librosa, pyworld, pysptk, sprocket-vc, hydra-core>=1.2, h5py.

## CLI Commands

All commands are installed as entry points via setup.py:

```bash
# Feature extraction (WORLD analysis → HDF5)
sifigan-extract-features audio=data/scp/<dataset>.scp

# Compute normalization statistics
sifigan-compute-statistics feats=data/scp/<dataset>.list stats=data/stats/<dataset>.joblib

# Training
sifigan-train generator=sifigan discriminator=univnet train=sifigan data=<dataset> out_dir=exp/sifigan

# Inference / decoding
sifigan-decode generator=sifigan data=<dataset> out_dir=exp/sifigan checkpoint_steps=400000

# Analysis-synthesis (extract features from audio then resynthesize)
sifigan-anasyn generator=sifigan data=<dataset> out_dir=exp/sifigan checkpoint_steps=400000
```

All CLI commands use Hydra for configuration. Config files are in `sifigan/bin/config/`.

## Architecture

### Two-Network Generator (SiFiGAN)

The core innovation is the source-filter decomposition in `sifigan/models/generator.py`:

- **SiFiGANGenerator** splits synthesis into a **Source Network** (excitation signal using `AdaptiveResidualBlock` with F0-dependent dilation factors) and a **Filter Network** (spectral resonance using standard `ResidualBlock`). The source network takes sine/noise signals generated from F0 as input; the filter network shapes the spectral envelope.
- **HiFiGANGenerator** is the baseline single-network variant.

### Signal Generation

`sifigan/utils/features.py` contains `SignalGenerator` which creates sine waves and noise from F0 contours, and `dilated_factor()` which computes pitch-adaptive dilation factors for the source network's adaptive convolutions.

### Discriminators

`sifigan/models/discriminator.py` provides:
- **UnivNetMultiResolutionMultiPeriodDiscriminator**: combines multi-resolution spectral + multi-period discriminators (default for SiFiGAN)
- **HiFiGANMultiScaleMultiPeriodDiscriminator**: multi-scale + multi-period (baseline)

### Loss Functions

In `sifigan/losses/`:
- `mel.py`: Mel-spectral L1 loss (weight 45.0)
- `reg.py`: Source regularization — `FlattenLoss` (flat spectral envelope) and `ResidualLoss` (weight 1.0)
- `adv.py`: Adversarial (MSE/Hinge) + feature matching losses

### Training Pipeline

`sifigan/bin/train.py` — Trainer class handles:
1. `AudioFeatDataset` loads audio + HDF5 features (F0, mcep, bap)
2. `Collater` generates sine/noise input signals and computes dilation factors per batch
3. Generator produces waveform + source signal; discriminator judges real vs fake
4. Combined loss: mel-spectral + source regularization + adversarial + feature matching

### Feature Extraction

`sifigan/bin/extract_features.py` — WORLD vocoder analysis producing HDF5 files with keys: `/f0`, `/cf0` (continuous F0), `/mcep` (mel-cepstral coefficients), `/bap` (band aperiodicity).

### Data & Examples

`egs/` contains example recipes (shell scripts) for datasets like `namine_ritsu` and `libritts-r-clean+nus-48e_all`. Each has scripts for the full pipeline: feature extraction → statistics → training → decoding.

## Configuration

Hydra config hierarchy in `sifigan/bin/config/`:
- `generator/`: sifigan.yaml, hifigan.yaml
- `discriminator/`: univnet.yaml, hifigan.yaml
- `train/`: sifigan.yaml, hifigan.yaml (learning rates, loss weights, schedule)
- `data/`: dataset-specific (sample rate, hop size, dense factors)

Key training defaults: 500k steps, batch 16, lr 2e-4 (Adam β=[0.5, 0.9]), eval every 2000 steps, checkpoint every 100k steps.
