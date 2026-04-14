#!/bin/bash
# SiFiGAN 学習スクリプト (ruthor / RunPod RTX 5090 用)
#
# pakari消滅後の環境:
#   - エフェメラル (/root, 300GB): リポジトリ、WAV、HDF5、venv
#   - 永続 (/workspace, 100GB): exp/ 出力、logs/、stats/
#
# 実行方法 (tmuxセッション内で):
#   tmux new-session -d -s train "bash /root/SiFiGAN/egs/libritts-r-clean+vocalset11/run_train_ruthor.sh"
#
# チェックポイント300000からの再開を前提。

set -euo pipefail

export PATH="/root/.local/bin:$PATH"

REPO="/root/SiFiGAN"
EGSDIR="$REPO/egs/libritts-r-clean+vocalset11"
EXPDIR="/workspace/exp/sifigan_1000k"
LOGDIR="/workspace/logs"
RESUME_STEPS=300000

mkdir -p "$LOGDIR" "$EXPDIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "=========================================="
log "SiFiGAN 学習 (ruthor) - 再開"
log "=========================================="
log "スクリプト: $0"
log "EGSDIR: $EGSDIR"
log "EXPDIR: $EXPDIR"
log "Git commit: $(cd "$REPO" && git rev-parse HEAD)"
log "Git branch: $(cd "$REPO" && git branch --show-current)"
log "hostname: $(hostname)"
log "GPU: $(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null || echo 'N/A')"
log "Python: $(uv run --project "$REPO" python --version)"
log "PyTorch: $(uv run --project "$REPO" python -c 'import torch; print(torch.__version__, "CUDA:", torch.cuda.is_available())')"
log "disk (ephemeral /): $(df -h / | tail -1)"
log "disk (persistent /workspace): $(df -h /workspace | tail -1)"

# データ存在チェック
log "=== データ存在チェック ==="
LIBRITTS_H5=$(find -L "$EGSDIR/LibriTTS_R" -name '*.h5' 2>/dev/null | wc -l)
VOCALSET_H5=$(find -L "$EGSDIR/VocalSet11" -name '*.h5' 2>/dev/null | wc -l)
LIBRITTS_WAV=$(find -L "$EGSDIR/LibriTTS_R" -path '*/wav/*.wav' 2>/dev/null | wc -l)
VOCALSET_WAV=$(find -L "$EGSDIR/VocalSet11" -path '*/wav/*.wav' 2>/dev/null | wc -l)
STATS="$EGSDIR/data/stats/libritts_r_clean+vocalset11_train_no_dev.joblib"
CHECKPOINT="$EXPDIR/checkpoints/checkpoint-${RESUME_STEPS}steps.pkl"
log "LibriTTS-R HDF5: $LIBRITTS_H5 ファイル (期待 160267)"
log "LibriTTS-R WAV:  $LIBRITTS_WAV ファイル (期待 160267)"
log "VocalSet HDF5:   $VOCALSET_H5 ファイル (期待 616)"
log "VocalSet WAV:    $VOCALSET_WAV ファイル (期待 616)"
log "統計ファイル: $(ls -lh "$STATS" 2>/dev/null || echo 'NOT FOUND')"
log "チェックポイント: $(ls -lh "$CHECKPOINT" 2>/dev/null || echo 'NOT FOUND')"

if [ ! -f "$STATS" ]; then log "ERROR: stats 不在"; exit 1; fi
if [ ! -f "$CHECKPOINT" ]; then log "ERROR: checkpoint 不在"; exit 1; fi
if [ "$LIBRITTS_H5" -lt 160000 ]; then log "ERROR: LibriTTS HDF5 不足"; exit 1; fi
if [ "$VOCALSET_H5" -ne 616 ]; then log "ERROR: VocalSet HDF5 不一致"; exit 1; fi
if [ "$LIBRITTS_WAV" -lt 160000 ]; then log "ERROR: LibriTTS WAV 不足"; exit 1; fi
if [ "$VOCALSET_WAV" -ne 616 ]; then log "ERROR: VocalSet WAV 不一致"; exit 1; fi

# 学習実行
log "=== 学習コマンド実行 (resume=$RESUME_STEPS) ==="
cd "$EGSDIR"

uv run --project "$REPO" sifigan-train \
    generator=sifigan \
    discriminator=univnet \
    train=sifigan_1000k \
    train.resume=$RESUME_STEPS \
    data=libritts-r-clean+vocalset11 \
    out_dir="$EXPDIR"

log "=========================================="
log "学習完了"
log "=========================================="
