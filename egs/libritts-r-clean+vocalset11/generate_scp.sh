#!/bin/bash
# VocalSet11 (straight + vibrato) と LibriTTS-R (train-clean-100 + train-clean-360) の
# SCPファイルを生成するスクリプト。
#
# 使い方: pakari上で実行
#   cd /repo/SiFiGAN && bash egs/libritts-r-clean+vocalset11/generate_scp.sh
#
# 前提:
#   - /repo/VocalSet11/FULL/ にVocalSet 1.1が展開済み
#   - LibriTTS_R/ に train-clean-100, train-clean-360, dev-clean, test-clean が展開済み
#
# VocalSet分割 (データセット付属のtrain/testに従う):
#   train (15名): female1,3,4,5,6,7,9 / male1,2,4,6,7,8,9,11
#   eval  (5名):  female2,8 / male3,5,10

set -euo pipefail

OUTDIR="egs/libritts-r-clean+vocalset11/data/scp"
PREFIX="libritts_r_clean+vocalset11"

VOCALSET_TRAIN_SINGERS="female1 female3 female4 female5 female6 female7 female9 male1 male2 male4 male6 male7 male8 male9 male11"
VOCALSET_EVAL_SINGERS="female2 female8 male3 male5 male10"

mkdir -p "$OUTDIR"

# --- train_no_dev.scp ---
# LibriTTS-R: train-clean-100 + train-clean-360
find LibriTTS_R/train-clean-100 LibriTTS_R/train-clean-360 \
    -type f -name '*.wav' | sort > "$OUTDIR/${PREFIX}_train_no_dev.scp.tmp"

# VocalSet: train歌手のstraight + vibrato
for singer in $VOCALSET_TRAIN_SINGERS; do
    find "VocalSet11/FULL/$singer" -type f -name '*.wav' \
        \( -path '*/straight/*' -o -path '*/vibrato/*' \)
done | sort >> "$OUTDIR/${PREFIX}_train_no_dev.scp.tmp"

mv "$OUTDIR/${PREFIX}_train_no_dev.scp.tmp" "$OUTDIR/${PREFIX}_train_no_dev.scp"

# --- train_no_dev.list (scp の .wav → hdf5/.h5) ---
sed 's|/wav/|/hdf5/|;s|\.wav$|.h5|' \
    "$OUTDIR/${PREFIX}_train_no_dev.scp" \
    | sed 's|VocalSet11/FULL/|VocalSet11/hdf5/|' \
    > "$OUTDIR/${PREFIX}_train_no_dev.list"

# --- dev.scp ---
find LibriTTS_R/dev-clean -type f -name '*.wav' | sort \
    > "$OUTDIR/${PREFIX}_dev.scp"

# --- dev.list ---
sed 's|/wav/|/hdf5/|;s|\.wav$|.h5|' \
    "$OUTDIR/${PREFIX}_dev.scp" \
    > "$OUTDIR/${PREFIX}_dev.list"

# --- eval.scp ---
# LibriTTS-R: test-clean
find LibriTTS_R/test-clean -type f -name '*.wav' | sort \
    > "$OUTDIR/${PREFIX}_eval.scp.tmp"

# VocalSet: eval歌手のstraight + vibrato
for singer in $VOCALSET_EVAL_SINGERS; do
    find "VocalSet11/FULL/$singer" -type f -name '*.wav' \
        \( -path '*/straight/*' -o -path '*/vibrato/*' \)
done | sort >> "$OUTDIR/${PREFIX}_eval.scp.tmp"

mv "$OUTDIR/${PREFIX}_eval.scp.tmp" "$OUTDIR/${PREFIX}_eval.scp"

# --- eval.list ---
sed 's|/wav/|/hdf5/|;s|\.wav$|.h5|' \
    "$OUTDIR/${PREFIX}_eval.scp" \
    | sed 's|VocalSet11/FULL/|VocalSet11/hdf5/|' \
    > "$OUTDIR/${PREFIX}_eval.list"

# --- 集計 ---
echo "Generated SCP files:"
wc -l "$OUTDIR"/${PREFIX}_*.scp "$OUTDIR"/${PREFIX}_*.list
