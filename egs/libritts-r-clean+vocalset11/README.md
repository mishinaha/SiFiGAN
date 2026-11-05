# libritts-r-clean+vocalset11

LibriTTS-R（train-clean-100 と train-clean-360）と VocalSet 1.1（straight と vibrato）で SiFiGAN をフルスクラッチ学習したときのレシピである。
データの設定は `sifigan/bin/config/data/libritts-r-clean+vocalset11.yaml` にある。

ここのスクリプトは、開発者が実際に使った環境の記録である。
パスや B2 のバケット名は、その環境に合わせて直接書いてある。
別の環境で使うときは、下の「変更が必要な箇所」を書き換える必要がある。

作業の経緯は `doc/Prepare.md` と `doc/260417-1-train.md` に記録してある。

## 想定している環境

- pakari：packet.ai のコンテナ。
  リポジトリは `/repo/SiFiGAN`、VocalSet は `/repo/VocalSet11`、ログは `/repo/logs` に置いた。
  LibriTTS-R の WAV はエフェメラルの `/tmp/libritts_r` に置いた。
  `run_prepare.sh` と `run_train.sh` はこの環境向けである。
- ruthor：RunPod の Pod。
  リポジトリは `/root/SiFiGAN` に置いた。
  学習の出力とログは永続の `/workspace` に置いた。
  WAV と HDF5 はエフェメラルの `/root/data` に置いた。
  `run_train_ruthor.sh` と `checkpoint_uploader.sh` はこの環境向けである。
- B2：Backblaze B2 のバケット `pakari` を S3 互換 API で使った。
  認証情報はリポジトリ直下の `.env`（コミットしない）に `B2_APPLICATION_KEY_ID` と `B2_APPLICATION_KEY` として書く。

## 使う順序

1. `run_prepare.sh`（pakari）
   LibriTTS-R のダウンロードと展開、`wav/` へのシンボリックリンクによる再配置、SCP ファイルの生成、特徴量の抽出、統計量の計算を行う。
   egs ディレクトリに `LibriTTS_R` と `VocalSet11` のシンボリックリンクを作る。
   生成物は `data/scp/` と `data/stats/` に置かれる。
2. 学習
   - `run_train.sh`（pakari）：最初から学習する。
   - `run_train_ruthor.sh`（ruthor）：`checkpoint-300000steps.pkl` から再開する。
3. `checkpoint_uploader.sh`（ruthor）
   学習と並行して tmux で動かす。
   新しいチェックポイントを検知して B2 にアップロードし、tfevents と `train.log` も同期する。

`run_prepare.sh` は VocalSet を 24 kHz にリサンプリングしない。
VocalSet は 44.1 kHz なので、`run_prepare.sh` の後に別途 soxr で 24 kHz にリサンプリングした（`doc/260417-1-train.md` の 3.1 節）。
ruthor で使ったリサンプリングの処理は `reference/script/260417/resample_and_symlink.py` にある。

ruthor ではデータの準備に `run_prepare.sh` を使っていない。
B2 から HDF5 と統計量を、OpenSLR と Zenodo から WAV を復元した（`doc/260417-1-train.md` の 3.2 節）。
`run_train_ruthor.sh` は、egs ディレクトリに `LibriTTS_R` と `VocalSet11` のシンボリックリンクがあり、`data/scp/` と `data/stats/` がそろっていることを前提とする。
これらを作るスクリプトはこのディレクトリにない。

## 変更が必要な箇所

### `run_prepare.sh`

- `PATH` に足している `/repo/.local/bin`（uv の場所）
- `LOGDIR`（`/repo/logs`）
- `EPHEMERAL`（`/tmp/libritts_r`、LibriTTS-R の置き場所）
- `REPO`（`/repo/SiFiGAN`）
- 埋め込みの Python 中の `base = '/repo/VocalSet11/FULL'`
- `VocalSet11` のシンボリックリンクの張り先 `/repo/VocalSet11`
- `df -h /repo` のマウントポイント
- `BASE_URL`（OpenSLR のミラー）

### `run_train.sh`

- `PATH` に足している `/repo/.local/bin` と `/home/ubuntu/.local/bin`
- `REPO`（`/repo/SiFiGAN`）
- `LOGDIR`（`/repo/logs`、定義されているが使われていない）
- `EXPDIR`（既定は egs ディレクトリの `exp/sifigan_1000k`）
- `df -h /repo` のマウントポイント

### `run_train_ruthor.sh`

- `PATH` に足している `/root/.local/bin`
- `REPO`（`/root/SiFiGAN`）
- `EXPDIR`（`/workspace/exp/sifigan_1000k`）
- `LOGDIR`（`/workspace/logs`）
- `RESUME_STEPS`（`300000`）
- 検査に使う期待ファイル数（LibriTTS-R が 160000 以上、VocalSet が 616）
- `df -h /workspace` のマウントポイント

### `checkpoint_uploader.sh`

- `.env` の `B2_APPLICATION_KEY_ID` と `B2_APPLICATION_KEY`
- `ENDPOINT`（`https://s3.us-west-004.backblazeb2.com`）
- `PATH` に足している `/root/.local/bin`
- `WATCH_DIR`、`EXPDIR`、`LOG`、`/workspace/logs/train.log`（`/workspace` 配下）
- `B2_CKPT`、`B2_EXP`、`B2_LOG` と `s3://pakari/logs/checkpoint_upload.log`（バケット `pakari`）

`aws`（awscli）と `inotifywait`（inotify-tools）が必要である。
