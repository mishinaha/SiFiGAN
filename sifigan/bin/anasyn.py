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
from scipy.signal import butter, filtfilt
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


def highpass_analysis(x, sample_rate, cutoff_hz=70.0, order=4):
    """High-pass the analysis signal (doc/260728-1-report.md Fix E).

    Sub-60 Hz rumble in the input makes WORLD harvest undershoot the true F0
    (e.g. tracking 216 Hz against a true 390 Hz), which the vocoder then
    renders as noise. Filtering only the analysis signal removes the failure;
    the synthesis conditioning path is unaffected by design.
    """
    b, a = butter(order, cutoff_hz / (sample_rate / 2), btype="high")
    return np.ascontiguousarray(filtfilt(b, a, x))


_COMB_CACHE = {}


def _comb_grid(sample_rate, n_fft=2048, fmin=100.0, fmax=840.0, n_grid=300, band_hz=4000.0):
    key = (sample_rate, n_fft, fmin, fmax, n_grid, band_hz)
    if key not in _COMB_CACHE:
        freq = np.fft.rfftfreq(n_fft, 1.0 / sample_rate)
        band = freq < band_hz
        grid = fmin * (fmax / fmin) ** (np.arange(n_grid) / (n_grid - 1))
        mh, mn = [], []
        for f in grid:
            hw = max(f * 0.10, sample_rate / n_fft * 1.5)
            harm = np.zeros(len(freq), dtype=bool)
            k = 1
            while k * f < sample_rate / 2:
                harm |= np.abs(freq - k * f) <= hw
                k += 1
            mh.append((band & harm) / max((band & harm).sum(), 1))
            mn.append((band & ~harm) / max((band & ~harm).sum(), 1))
        _COMB_CACHE[key] = (grid, np.array(mh).T, np.array(mn).T, n_fft)
    return _COMB_CACHE[key]


def _make_ncc(x, hop_size, sample_rate, win=1024, fmin=100.0, fmax=920.0):
    """Per-frame normalized autocorrelation at a pitch lag, computed lazily."""
    lmin = int(round(sample_rate / fmax))
    lmax = int(round(sample_rate / fmin))
    xp = np.pad(np.asarray(x, np.float64), (win // 2, win + lmax), mode="constant")
    cache = {}

    def ncc_at(i, f):
        if f <= 0:
            return np.nan
        lag = int(round(sample_rate / f))
        if not (lmin <= lag <= lmax):
            return np.nan
        if (i, lag) not in cache:
            seg = xp[i * hop_size : i * hop_size + win + lmax]
            s1 = seg[:win] - seg[:win].mean()
            s2 = seg[lag : lag + win] - seg[lag : lag + win].mean()
            e1, e2 = np.dot(s1, s1), np.dot(s2, s2)
            cache[(i, lag)] = np.dot(s1, s2) / np.sqrt(e1 * e2) if e1 > 1e-18 and e2 > 1e-18 else 0.0
        return cache[(i, lag)]

    return ncc_at


def correct_f0_undershoot(
    x,
    f0,
    sample_rate,
    hop_size,
    ratio_min=1.15,
    ratio_max=1.9,
    ncc_min=0.6,
    ncc_margin=0.2,
    hnr_min_db=3.0,
    grow_window=20,
    grow_semitones=1.0,
    grow_ncc=0.5,
    grow_margin=0.15,
    max_grow=20,
):
    """Replace reference-verified undershot F0 frames (doc/260728-1-report.md Fix G).

    A comb-HNR grid search over the analysis signal provides a pitch reference
    that is independent of harvest. Voiced frames whose reference lies
    ratio_min..ratio_max above harvest, and whose reference lag also wins the
    frame's normalized autocorrelation by ncc_margin, get the reference value
    (never zero, unlike the retired octave-drop rejection). Seeds then extend
    into neighbours that sit at least grow_semitones below the repaired local
    trend while the trend lag keeps winning the autocorrelation.
    """
    n_frames = len(f0)
    grid, mh, mn, n_fft = _comb_grid(sample_rate)
    xp = np.pad(np.asarray(x, np.float64), (n_fft // 2, n_fft), mode="constant")
    idx = np.minimum(np.arange(n_fft)[None, :] + (np.arange(n_frames) * hop_size)[:, None], len(xp) - 1)
    power = np.abs(np.fft.rfft(xp[idx] * np.hanning(n_fft), axis=1)) ** 2
    hnr = 10 * np.log10(np.maximum(power @ mh, 1e-30) / np.maximum(power @ mn, 1e-30))
    best = np.argmax(hnr, axis=1)
    f_ref = np.where(hnr[np.arange(n_frames), best] > hnr_min_db, grid[best], 0.0)
    ncc_at = _make_ncc(x, hop_size, sample_rate)

    corrected = f0.copy()
    seeds = []
    for i in np.where(f0 > 0)[0]:
        if f_ref[i] <= 0 or not (ratio_min <= f_ref[i] / f0[i] <= ratio_max):
            continue
        nh, nr = ncc_at(i, f0[i]), ncc_at(i, f_ref[i])
        if nr == nr and nr > ncc_min and (nh != nh or nr > nh + ncc_margin):
            corrected[i] = f_ref[i]
            seeds.append(i)
    grown = 0
    for i in seeds:
        for step in (-1, 1):
            j, n = i + step, 0
            while 0 <= j < n_frames and f0[j] > 0 and n < max_grow:
                local = corrected[max(0, j - grow_window) : j + grow_window + 1]
                local = local[local > 0]
                if len(local) < 5:
                    break
                trend = np.percentile(local, 75)
                if 12 * np.log2(trend / f0[j]) < grow_semitones:
                    break
                nh, nt = ncc_at(j, f0[j]), ncc_at(j, trend)
                if not (nt == nt and nt > grow_ncc and (nh != nh or nt > nh + grow_margin)):
                    break
                corrected[j] = trend
                grown += 1
                n += 1
                j += step
    return corrected, len(seeds), grown


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
        if config.correct_analysis_hp:
            x = highpass_analysis(x, config.sample_rate, cutoff_hz=config.analysis_hp_hz)
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
        if config.correct_f0_undershoot:
            f0_, n_seed, n_grown = correct_f0_undershoot(
                x,
                f0_,
                config.sample_rate,
                int(config.sample_rate * config.frame_period * 0.001),
                ratio_max=config.undershoot_ratio_max,
            )
            logger.info(f"Fix G: replaced {n_seed} undershot F0 frames (+{n_grown} extended).")
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
