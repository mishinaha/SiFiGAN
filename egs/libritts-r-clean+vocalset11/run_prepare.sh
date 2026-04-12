#!/bin/bash
# LibriTTS-R + VocalSet11 データ準備スクリプト
#
# 実行方法 (pakari上):
#   cd /repo/SiFiGAN/egs/libritts-r-clean+vocalset11 && \
#   bash run_prepare.sh 2>&1 | tee -a /repo/logs/prepare.log
#
# 前提:
#   - /repo/VocalSet11/FULL/ にVocalSet 1.1が展開済み
#   - uv が /repo/.local/bin/uv にインストール済み
#
# 処理内容:
#   1. LibriTTS-R のダウンロード (エフェメラルストレージ)
#   2. 展開、ディレクトリ再配置、tar.gz削除
#   3. VocalSet WAV を wav/ ディレクトリにシンボリックリンク
#   4. SCPファイル生成
#   5. 特徴量抽出 (HDF5 → 永続ストレージ)
#   6. 統計量計算
#
# ストレージ方針:
#   - WAVファイル (大): エフェメラル /tmp/libritts_r/ (再起動で消失)
#   - HDF5特徴量 (中): 永続 /repo/ 配下
#   - VocalSet HDF5:   永続 /repo/VocalSet11/hdf5/

set -euo pipefail

export PATH="/repo/.local/bin:$PATH"

LOGDIR="/repo/logs"
EPHEMERAL="/tmp/libritts_r"
REPO="/repo/SiFiGAN"
EGSDIR="$(cd "$(dirname "$0")" && pwd)"
PREFIX="libritts_r_clean+vocalset11"

mkdir -p "$LOGDIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "=========================================="
log "データ準備開始"
log "=========================================="
log "スクリプト: $0"
log "作業ディレクトリ: $EGSDIR"
log "Git commit: $(cd "$REPO" && git rev-parse HEAD)"
log "Git branch: $(cd "$REPO" && git branch --show-current)"
log "hostname: $(hostname)"
log "uname: $(uname -a)"
log "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo 'N/A')"
log "disk (persistent): $(df -h /repo | tail -1)"
log "disk (ephemeral):  $(df -h /tmp | tail -1)"

# ============================================
# 1. LibriTTS-R ダウンロード
# ============================================
LIBRITTS_FILES=(
    "train_clean_100.tar.gz"
    "train_clean_360.tar.gz"
    "dev_clean.tar.gz"
    "test_clean.tar.gz"
)
BASE_URL="https://openslr.trmal.net/resources/141"

mkdir -p "$EPHEMERAL"

for f in "${LIBRITTS_FILES[@]}"; do
    filepath="$EPHEMERAL/$f"
    if [ -f "$filepath" ]; then
        log "SKIP: $f は既にダウンロード済み"
    else
        log "DOWNLOAD: $f 開始 ($BASE_URL/$f)"
        curl -L -o "$filepath" "$BASE_URL/$f" --progress-bar 2>&1
        log "DOWNLOAD: $f 完了 ($(ls -lh "$filepath" | awk '{print $5}'))"
    fi
    md5=$(md5sum "$filepath" | awk '{print $1}')
    log "MD5: $f = $md5"
done

# ============================================
# 2. 展開・再配置・tar.gz削除
# ============================================
# LibriTTS-Rの実際の構造:
#   LibriTTS_R/{subset}/{speaker_id}/{chapter_id}/{speaker}_{chapter}_{seg}.wav
# SiFiGANのSCPが期待する構造 (path_replaceで "wav" → "hdf5" に置換するため):
#   LibriTTS_R/{subset}/{speaker_id}/wav/{speaker}_{chapter}_{seg}.wav
# → 話者ディレクトリ内に wav/ を作り、全WAVをフラットにシンボリックリンクする

for f in "${LIBRITTS_FILES[@]}"; do
    filepath="$EPHEMERAL/$f"
    subset=$(echo "$f" | sed 's/.tar.gz//;s/_/-/g')

    if [ -d "$EPHEMERAL/LibriTTS_R/$subset" ]; then
        log "SKIP: LibriTTS_R/$subset は既に展開済み"
    else
        log "EXTRACT: $f 開始"
        tar xzf "$filepath" -C "$EPHEMERAL"
        log "EXTRACT: $f 完了"
    fi

    # tar.gz削除
    if [ -f "$filepath" ]; then
        log "DELETE: $f 削除 (ディスク節約)"
        rm -f "$filepath"
    fi

    # wav/ ディレクトリへの再配置
    subset_dir="$EPHEMERAL/LibriTTS_R/$subset"
    for speaker_dir in "$subset_dir"/*/; do
        speaker=$(basename "$speaker_dir")
        wav_dir="$speaker_dir/wav"
        if [ -d "$wav_dir" ] && [ "$(ls -A "$wav_dir" 2>/dev/null)" ]; then
            continue  # 既に再配置済み
        fi
        mkdir -p "$wav_dir"
        # 各チャプターディレクトリからWAVをシンボリックリンク
        find "$speaker_dir" -maxdepth 2 -name '*.wav' -not -path '*/wav/*' | while read -r wavfile; do
            ln -sf "$wavfile" "$wav_dir/$(basename "$wavfile")"
        done
    done
    log "RESTRUCTURE: $subset 完了"
done

log "LibriTTS-R 展開後サイズ: $(du -sh "$EPHEMERAL/LibriTTS_R/" | awk '{print $1}')"
log "LibriTTS-R WAVファイル数 (wav/): $(find "$EPHEMERAL/LibriTTS_R" -path '*/wav/*.wav' | wc -l)"

# ============================================
# 3. VocalSet WAV 再配置
# ============================================
# VocalSetの構造:
#   VocalSet11/FULL/{singer}/{exercise}/{technique}/{file}.wav
# SiFiGAN用に wav/ ディレクトリを作成:
#   VocalSet11/FULL/{singer}/wav/{file}.wav (シンボリックリンク)

log "VocalSet WAV 再配置開始 (straight + vibrato のみ)"
VOCALSET_ALL_SINGERS="female1 female2 female3 female4 female5 female6 female7 female8 female9 male1 male2 male3 male4 male5 male6 male7 male8 male9 male10 male11"
for singer in $VOCALSET_ALL_SINGERS; do
    wav_dir="/repo/VocalSet11/FULL/$singer/wav"
    if [ -d "$wav_dir" ] && [ "$(ls -A "$wav_dir" 2>/dev/null)" ]; then
        continue  # 既に再配置済み
    fi
    mkdir -p "$wav_dir"
    find "/repo/VocalSet11/FULL/$singer" \( -path '*/straight/*' -o -path '*/vibrato/*' \) -name '*.wav' | while read -r wavfile; do
        ln -sf "$wavfile" "$wav_dir/$(basename "$wavfile")"
    done
done
log "VocalSet WAV 再配置完了"
log "VocalSet WAVファイル数 (wav/): $(find /repo/VocalSet11/FULL -path '*/wav/*.wav' | wc -l)"

# ============================================
# 4. シンボリックリンク作成 (egsディレクトリから参照)
# ============================================
cd "$EGSDIR"

if [ ! -e "LibriTTS_R" ]; then
    ln -s "$EPHEMERAL/LibriTTS_R" LibriTTS_R
    log "SYMLINK: $EGSDIR/LibriTTS_R -> $EPHEMERAL/LibriTTS_R"
fi

if [ ! -e "VocalSet11" ]; then
    ln -s /repo/VocalSet11 VocalSet11
    log "SYMLINK: $EGSDIR/VocalSet11 -> /repo/VocalSet11"
fi

# ============================================
# 5. SCPファイル生成
# ============================================
log "SCPファイル生成開始"
mkdir -p data/scp

VOCALSET_TRAIN_SINGERS="female1 female3 female4 female5 female6 female7 female9 male1 male2 male4 male6 male7 male8 male9 male11"
VOCALSET_EVAL_SINGERS="female2 female8 male3 male5 male10"

# --- train_no_dev.scp ---
{
    for subset in train-clean-100 train-clean-360; do
        find "LibriTTS_R/$subset" -path '*/wav/*.wav' -type l | sort
    done
    for singer in $VOCALSET_TRAIN_SINGERS; do
        find "VocalSet11/FULL/$singer/wav" -name '*.wav' -type l | sort
    done
} > "data/scp/${PREFIX}_train_no_dev.scp"

# --- dev.scp ---
find "LibriTTS_R/dev-clean" -path '*/wav/*.wav' -type l | sort \
    > "data/scp/${PREFIX}_dev.scp"

# --- eval.scp ---
{
    find "LibriTTS_R/test-clean" -path '*/wav/*.wav' -type l | sort
    for singer in $VOCALSET_EVAL_SINGERS; do
        find "VocalSet11/FULL/$singer/wav" -name '*.wav' -type l | sort
    done
} > "data/scp/${PREFIX}_eval.scp"

log "SCP train_no_dev: $(wc -l < "data/scp/${PREFIX}_train_no_dev.scp") ファイル"
log "SCP dev:          $(wc -l < "data/scp/${PREFIX}_dev.scp") ファイル"
log "SCP eval:         $(wc -l < "data/scp/${PREFIX}_eval.scp") ファイル"

# ============================================
# 6. 特徴量抽出
# ============================================
# extract_features は .scp と同名の .list を自動生成する (aux_list_create)
# HDF5出力先は in_dir="wav" → out_dir="hdf5" の文字列置換で決まる
# LibriTTS: LibriTTS_R/{subset}/{speaker}/wav/{file}.wav → .../hdf5/{file}.h5
# VocalSet: VocalSet11/FULL/{singer}/wav/{file}.wav → .../hdf5/{file}.h5
#
# VocalSetのHDF5は /repo/ 配下なので永続、LibriTTSのHDF5はエフェメラル上に生成されるが
# .listファイルさえあれば学習時に参照可能

for split in train_no_dev dev eval; do
    scp="data/scp/${PREFIX}_${split}.scp"
    log "特徴量抽出開始: $split ($(wc -l < "$scp") ファイル)"
    uv run --project "$REPO" sifigan-extract-features \
        audio="$scp" \
        minf0=60 maxf0=1000 \
        sample_rate=24000
    log "特徴量抽出完了: $split"
done

# ============================================
# 7. 統計量計算
# ============================================
log "統計量計算開始"
mkdir -p data/stats
uv run --project "$REPO" sifigan-compute-statistics \
    feats="data/scp/${PREFIX}_train_no_dev.list" \
    stats="data/stats/${PREFIX}_train_no_dev.joblib"
log "統計量計算完了: data/stats/${PREFIX}_train_no_dev.joblib"

# ============================================
# 完了
# ============================================
log "=========================================="
log "データ準備完了"
log "=========================================="
log "disk (persistent): $(df -h /repo | tail -1)"
log "disk (ephemeral):  $(df -h /tmp | tail -1)"

# HDF5統計
LIBRITTS_H5=$(find LibriTTS_R -name '*.h5' 2>/dev/null | wc -l)
VOCALSET_H5=$(find VocalSet11 -name '*.h5' 2>/dev/null | wc -l)
log "HDF5ファイル数: LibriTTS=$LIBRITTS_H5, VocalSet=$VOCALSET_H5"

if [ $LIBRITTS_H5 -gt 0 ]; then
    log "LibriTTS HDF5サイズ: $(du -sh LibriTTS_R/*/*/hdf5 2>/dev/null | tail -1)"
fi
if [ $VOCALSET_H5 -gt 0 ]; then
    log "VocalSet HDF5サイズ: $(du -sh VocalSet11/FULL/*/hdf5 2>/dev/null | tail -1)"
fi

log "SCPファイル:"
wc -l data/scp/${PREFIX}_*.scp data/scp/${PREFIX}_*.list

log "統計ファイル: $(ls -lh data/stats/${PREFIX}_train_no_dev.joblib)"
