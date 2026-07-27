# -*- coding: utf-8 -*-

# Copyright 2022 Reo Yoneyama (Nagoya University)
#  MIT License (https://opensource.org/licenses/MIT)

"""Analysis-synthesis script.

Analysis: WORLD vocoder
Synthesis: Pre-trained neural vocoder

"""

# A logger for this file
import copy
import os
from logging import getLogger

import hydra
import librosa
import numpy as np
import pysptk
import pyworld as pw
import soundfile as sf
import torch
from hydra.utils import instantiate, to_absolute_path
from joblib import load
from omegaconf import DictConfig
from scipy.interpolate import interp1d
from sifigan.utils.features import SignalGenerator, dilated_factor

logger = getLogger(__name__)

# All-pass-filter coefficients {key -> sampling rate : value -> coefficient}
ALPHA = {
    8000: 0.312,
    12000: 0.369,
    16000: 0.410,
    22050: 0.455,
    24000: 0.466,
    32000: 0.504,
    44100: 0.544,
    48000: 0.554,
}


def convert_continuos_f0(f0):
    # get uv information as binary
    uv = np.float32(f0 != 0)
    # get start and end of f0
    if (f0 == 0).all():
        logger.warn("all of the f0 values are 0.")
        return uv, f0, False
    start_f0 = f0[f0 != 0][0]
    end_f0 = f0[f0 != 0][-1]
    # padding start and end of f0 sequence
    cont_f0 = copy.deepcopy(f0)
    start_idx = np.where(cont_f0 == start_f0)[0][0]
    end_idx = np.where(cont_f0 == end_f0)[0][-1]
    cont_f0[:start_idx] = start_f0
    cont_f0[end_idx:] = end_f0
    # get non-zero frame index
    nz_frames = np.where(cont_f0 != 0)[0]
    # perform linear interpolation
    f = interp1d(nz_frames, cont_f0[nz_frames])
    cont_f0 = f(np.arange(0, cont_f0.shape[0]))

    return uv, cont_f0


def reject_f0_octave_drop(f0, window=20, threshold_semitones=6.0, min_voiced=5):
    """Reject harvest octave-down errors (doc/260728-1-report.md Fix C).

    Voiced frames whose F0 is more than threshold_semitones below the local
    voiced median are treated as unvoiced. Local medians are computed on the
    original contour so consecutive errors cannot mask each other.
    """
    ratio = 2.0 ** (-threshold_semitones / 12.0)
    corrected = f0.copy()
    rejected = 0
    for i in np.where(f0 > 0)[0]:
        local = f0[max(0, i - window) : i + window + 1]
        local = local[local > 0]
        if len(local) >= min_voiced and f0[i] < np.median(local) * ratio:
            corrected[i] = 0.0
            rejected += 1
    return corrected, rejected


def repair_saturated_ap(ap, f0, threshold=0.999):
    """Repair D4C LoveTrain mis-fires (doc/260728-1-report.md Fix A).

    D4C's binary LoveTrain decision floods all bins of a frame with 1 - 1e-12
    ("pure noise") and mis-fires on high-pitched voiced frames, which makes the
    vocoder synthesize noise. Such frames are replaced by log-domain linear
    interpolation between the nearest non-saturated voiced frames. Unvoiced
    frames are saturated by design and left untouched.
    """
    saturated = ap.min(axis=1) > threshold
    voiced = f0 > 0
    bad_idx = np.where(voiced & saturated)[0]
    good_idx = np.where(voiced & ~saturated)[0]
    if len(bad_idx) == 0 or len(good_idx) == 0:
        return ap, 0
    repaired = ap.copy()
    log_ap = np.log(np.clip(ap, 1e-12, None))
    for i in bad_idx:
        prev_good = good_idx[good_idx < i]
        next_good = good_idx[good_idx > i]
        if len(prev_good) and len(next_good):
            p, n = prev_good[-1], next_good[0]
            w = (i - p) / (n - p)
            log_interp = (1.0 - w) * log_ap[p] + w * log_ap[n]
        elif len(prev_good):
            log_interp = log_ap[prev_good[-1]]
        else:
            log_interp = log_ap[next_good[0]]
        repaired[i] = np.minimum(np.exp(log_interp), 1.0)
    return repaired, len(bad_idx)


@torch.no_grad()
@hydra.main(version_base=None, config_path="config", config_name="anasyn")
def main(config: DictConfig) -> None:
    """Run analysis-synthesis process."""

    np.random.seed(config.seed)
    torch.manual_seed(config.seed)
    torch.cuda.manual_seed(config.seed)
    os.environ["PYTHONHASHSEED"] = str(config.seed)

    # set device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Synthesize on {device}.")

    # load pre-trained model from checkpoint file
    model = instantiate(config.generator)
    state_dict = torch.load(to_absolute_path(config.checkpoint_path), map_location="cpu", weights_only=False)
    model.load_state_dict(state_dict["model"]["generator"])
    logger.info(f"Loaded model parameters from {config.checkpoint_path}.")
    model.remove_weight_norm()
    model.eval().to(device)

    # get scaler
    scaler = load(config.stats)

    # get data processor
    signal_generator = SignalGenerator(
        sample_rate=config.sample_rate,
        hop_size=int(config.sample_rate * config.frame_period * 0.001),
        sine_amp=config.sine_amp,
        noise_amp=config.noise_amp,
        signal_types=config.signal_types,
    )

    # create output directory
    os.makedirs(config.out_dir, exist_ok=True)

    # loop all wav files in in_dir
    for wav_file in os.listdir(config.in_dir):
        logger.info(f"Start processing {wav_file}")
        if os.path.splitext(wav_file)[1] != ".wav":
            continue
        wav_path = os.path.join(config.in_dir, wav_file)

        # WORLD analysis
        x, sr = sf.read(to_absolute_path(wav_path))
        if sr != config.sample_rate:
            x = librosa.resample(x, orig_sr=sr, target_sr=config.sample_rate)
        f0_, t = pw.harvest(
            x,
            config.sample_rate,
            f0_floor=config.f0_floor,
            f0_ceil=config.f0_ceil,
            frame_period=config.frame_period,
        )
        sp = pw.cheaptrick(x, f0_, t, config.sample_rate)
        ap = pw.d4c(x, f0_, t, config.sample_rate)
        if config.correct_ap_saturation:
            ap, n_repaired = repair_saturated_ap(ap, f0_, threshold=config.ap_saturation_threshold)
            logger.info(f"Fix A: repaired {n_repaired} voiced frames with saturated aperiodicity.")
        mcep = pysptk.sp2mc(sp, order=config.mcep_dim, alpha=ALPHA[config.sample_rate])
        mcap = pysptk.sp2mc(ap, order=config.mcap_dim, alpha=ALPHA[config.sample_rate])
        bap = pw.code_aperiodicity(ap, config.sample_rate)
        if config.correct_bap_clip:
            bap = np.clip(
                bap,
                scaler["bap"].mean_ - config.bap_clip_z * scaler["bap"].scale_,
                scaler["bap"].mean_ + config.bap_clip_z * scaler["bap"].scale_,
            )
            logger.info(f"Fix D: clipped bap to |z| <= {config.bap_clip_z}.")

        # prepare f0 related features
        if config.correct_f0_octave_drop:
            f0_, n_rejected = reject_f0_octave_drop(
                f0_,
                window=config.octave_drop_window,
                threshold_semitones=config.octave_drop_semitones,
            )
            logger.info(f"Fix C: rejected {n_rejected} octave-down F0 frames.")
        uv, cf0_ = convert_continuos_f0(f0_)
        uv = uv[:, np.newaxis]  # (T, 1)
        f0_ = f0_[:, np.newaxis]  # (T, 1)
        cf0_ = cf0_[:, np.newaxis]  # (T, 1)

        for f0_factor in config.f0_factors:

            f0 = f0_ * f0_factor
            cf0 = cf0_ * f0_factor

            # prepare input acoustic features
            c = []
            for feat_type in config.aux_feats:
                if feat_type == "f0":
                    c += [scaler[feat_type].transform(f0)]
                elif feat_type == "cf0":
                    c += [scaler[feat_type].transform(cf0)]
                elif feat_type == "uv":
                    c += [scaler[feat_type].transform(uv)]
                elif feat_type == "mcep":
                    c += [scaler[feat_type].transform(mcep)]
                elif feat_type == "mcap":
                    c += [scaler[feat_type].transform(mcap)]
                elif feat_type == "bap":
                    c += [scaler[feat_type].transform(bap)]
            c = np.concatenate(c, axis=1)

            # prepare dense factors
            dfs = []
            for df, us in zip(
                config.dense_factors,
                np.cumprod(config.generator.upsample_scales),
            ):
                dfs += [
                    np.repeat(dilated_factor(cf0, config.sample_rate, df), us)
                    if config.df_f0_type == "cf0"
                    else np.repeat(dilated_factor(f0, config.sample_rate, df), us)
                ]

            # convert to torch tensors
            f0 = torch.FloatTensor(f0).view(1, 1, -1).to(device)
            cf0 = torch.FloatTensor(cf0).view(1, 1, -1).to(device)
            c = torch.FloatTensor(c).unsqueeze(0).transpose(2, 1).to(device)
            dfs = [torch.FloatTensor(np.array(df)).view(1, 1, -1).to(device) for df in dfs]

            # generate input signals
            if config.sine_f0_type == "cf0":
                in_signal = signal_generator(cf0)
            elif config.sine_f0_type == "f0":
                in_signal = signal_generator(f0)

            # synthesize with the neural vocoder
            y = model(in_signal, c, dfs)[0]

            # save output signal as PCM 16 bit wav file
            out_path = os.path.join(config.out_dir, wav_file).replace(".wav", f"_{f0_factor:.2f}.wav")
            sf.write(
                to_absolute_path(out_path),
                y.view(-1).cpu().numpy(),
                config.sample_rate,
                "PCM_16",
            )


if __name__ == "__main__":
    main()
