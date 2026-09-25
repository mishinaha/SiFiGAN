#!/bin/bash
# チェックポイント自動アップローダ
#
# /workspace/exp/sifigan_1000k/checkpoints/ を inotifywait で監視し、
# 新規チェックポイント(.pkl) が書き込み完了した瞬間にB2へアップロードする。
# 合わせて tfevents と train.log も同期する。
#
# 実行方法:
#   tmux new-session -d -s uploader "bash /root/SiFiGAN/egs/libritts-r-clean+vocalset11/checkpoint_uploader.sh"
#
# B2 の認証情報はリポジトリ直下の .env (コミットしない) から読む。
# .env には B2_APPLICATION_KEY_ID (キー ID) と B2_APPLICATION_KEY (シークレット) を書く。

set -u

export PATH="/root/.local/bin:$PATH"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
. "$REPO_ROOT/.env"
export AWS_ACCESS_KEY_ID="${B2_APPLICATION_KEY_ID:?.env に設定されていない}"
export AWS_SECRET_ACCESS_KEY="${B2_APPLICATION_KEY:?.env に設定されていない}"
ENDPOINT="--endpoint-url https://s3.us-west-004.backblazeb2.com"

WATCH_DIR="/workspace/exp/sifigan_1000k/checkpoints"
EXPDIR="/workspace/exp/sifigan_1000k"
B2_CKPT="s3://pakari/exp/sifigan_1000k/checkpoints"
B2_EXP="s3://pakari/exp/sifigan_1000k/"
B2_LOG="s3://pakari/logs/train.log"
LOG="/workspace/logs/checkpoint_upload.log"

mkdir -p "$WATCH_DIR"
touch "$LOG"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

log "=========================================="
log "checkpoint_uploader 起動"
log "=========================================="
log "監視ディレクトリ: $WATCH_DIR"
log "B2 アップロード先: $B2_CKPT"

# 起動時に一度同期 (取りこぼし対策)
log "起動時初期同期..."
aws s3 sync "$EXPDIR/" "$B2_EXP" \
    --exclude "*" --include "checkpoints/*.pkl" --include "events.out.tfevents.*" --include "config.yaml" \
    $ENDPOINT 2>&1 | tail -3 | while read line; do log "  $line"; done
log "初期同期完了"

# inotifywait で監視
log "監視開始..."
inotifywait -m -e close_write --format '%f' "$WATCH_DIR" | while read fname; do
    case "$fname" in
        checkpoint-*steps.pkl)
            log "検知: $fname"
            # チェックポイント本体
            if aws s3 cp "$WATCH_DIR/$fname" "$B2_CKPT/$fname" $ENDPOINT >/dev/null 2>&1; then
                log "  ✓ checkpoint uploaded: $fname"
            else
                log "  ✗ ERROR uploading checkpoint: $fname"
            fi
            # tfevents 同期
            if aws s3 sync "$EXPDIR/" "$B2_EXP" \
                --exclude "*" --include "events.out.tfevents.*" --include "config.yaml" \
                $ENDPOINT >/dev/null 2>&1; then
                log "  ✓ tfevents synced"
            fi
            # train.log アップロード
            if [ -f /workspace/logs/train.log ] && aws s3 cp /workspace/logs/train.log "$B2_LOG" $ENDPOINT >/dev/null 2>&1; then
                log "  ✓ train.log uploaded"
            fi
            # checkpoint_upload.log 自身もアップロード
            aws s3 cp "$LOG" "s3://pakari/logs/checkpoint_upload.log" $ENDPOINT >/dev/null 2>&1
            ;;
    esac
done
