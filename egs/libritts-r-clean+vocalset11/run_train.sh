#!/bin/bash
# SiFiGAN フルスクラッチ学習スクリプト
#
# 実行方法 (pakari上、tmuxセッション内で):
#   cd /repo/SiFiGAN/egs/libritts-r-clean+vocalset11 && \
#   bash run_train.sh 2>&1 | tee -a /repo/logs/train.log
#
# 前提:
#   - LibriTTS-R HDF5 が /tmp/libritts_r/LibriTTS_R/ に展開済み
#   - VocalSet HDF5 が /repo/VocalSet11/FULL/*/hdf5/ に存在
#   - egs ディレクトリに LibriTTS_R, VocalSet11 のシンボリックリンクが存在
#   - 統計ファイル data/stats/...train_no_dev.joblib が存在
#   - uv が /repo/.local/bin/uv にインストール済み

set -euo pipefail

export PATH="/repo/.local/bin:/home/ubuntu/.local/bin:$PATH"

REPO="/repo/SiFiGAN"
EGSDIR="$(cd "$(dirname "$0")" && pwd)"
LOGDIR="/repo/logs"
EXPDIR="$EGSDIR/exp/sifigan_1000k"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "=========================================="
log "SiFiGAN フルスクラッチ学習開始"
log "=========================================="
log "スクリプト: $0"
log "作業ディレクトリ: $EGSDIR"
log "出力ディレクトリ: $EXPDIR"
log "Git commit: $(cd "$REPO" && git rev-parse HEAD)"
log "Git branch: $(cd "$REPO" && git branch --show-current)"
log "hostname: $(hostname)"
log "GPU: $(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null || echo 'N/A')"
log "CUDA: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null || echo 'N/A')"
log "Python: $(uv run --project "$REPO" python --version)"
log "PyTorch: $(uv run --project "$REPO" python -c 'import torch; print(torch.__version__, "CUDA:", torch.cuda.is_available())')"
log "disk (persistent): $(df -h /repo | tail -1)"
log "disk (ephemeral):  $(df -h /tmp | tail -1)"

# データ存在チェック
log "=== データ存在チェック ==="
LIBRITTS_H5=$(find "$EGSDIR/LibriTTS_R" -name '*.h5' 2>/dev/null | wc -l)
VOCALSET_H5=$(find "$EGSDIR/VocalSet11" -name '*.h5' 2>/dev/null | wc -l)
STATS="$EGSDIR/data/stats/libritts_r_clean+vocalset11_train_no_dev.joblib"
log "LibriTTS-R HDF5: $LIBRITTS_H5 ファイル"
log "VocalSet HDF5: $VOCALSET_H5 ファイル"
log "統計ファイル: $(ls -lh "$STATS" 2>/dev/null || echo 'NOT FOUND')"

if [ "$LIBRITTS_H5" -eq 0 ]; then
    log "ERROR: LibriTTS-R HDF5 が見つかりません。B2から復元してください。"
    exit 1
fi
if [ "$VOCALSET_H5" -eq 0 ]; then
    log "ERROR: VocalSet HDF5 が見つかりません。"
    exit 1
fi
if [ ! -f "$STATS" ]; then
    log "ERROR: 統計ファイルが見つかりません。"
    exit 1
fi

# 学習パラメータ表示
log "=== 学習パラメータ ==="
log "generator: sifigan"
log "discriminator: univnet"
log "train config: sifigan_1000k (1,000,000 steps)"
log "data config: libritts-r-clean+vocalset11"
log "batch_size: 16"
log "sample_rate: 24000"
log "hop_size: 120"
log "save_interval: 100,000 steps"
log "eval_interval: 2,000 steps"
log "log_interval: 2,000 steps"

# 学習実行
log "=== 学習コマンド実行 ==="
cd "$EGSDIR"

uv run --project "$REPO" sifigan-train \
    generator=sifigan \
    discriminator=univnet \
    train=sifigan_1000k \
    data=libritts-r-clean+vocalset11 \
    out_dir="$EXPDIR"

log "=========================================="
log "SiFiGAN 学習完了"
log "=========================================="
log "出力ディレクトリ: $EXPDIR"
log "チェックポイント: $(ls "$EXPDIR/checkpoints/" 2>/dev/null | wc -l) 個"
log "disk (persistent): $(df -h /repo | tail -1)"
log "disk (ephemeral):  $(df -h /tmp | tail -1)"
