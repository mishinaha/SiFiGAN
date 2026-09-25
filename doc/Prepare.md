# データ準備作業記録

LibriTTS-R と VocalSet11 を使ったフルスクラッチ学習に向けて、データを準備したときの記録である。

## 実行環境

- マシン：`ssh pakari`（packet.ai、RTX PRO 6000 Blackwell、96 コア、1.5TB RAM）
- 実行時の Git commit：`a354202`（np.float64 修正後）
- ログ：`/repo/logs/prepare.log`

## 実行したコマンド

```bash
# 1回目 (シンボリックリンク作成が遅く中断)
cd /repo/SiFiGAN/egs/libritts-r-clean+vocalset11
bash run_prepare.sh 2>&1 | tee -a /repo/logs/prepare.log

# 2回目 (Python一括処理に修正後、再実行)
# DL済みファイルはスキップ、展開済みディレクトリもスキップ
bash run_prepare.sh >> /repo/logs/prepare.log 2>&1

# 3回目 (np.float修正後、特徴量抽出のみ再実行)
# train_no_dev, dev, eval の順に特徴量抽出 + 統計量計算
```

## LibriTTS-R のダウンロード結果

| ファイル | サイズ | MD5 |
|---|---|---|
| train_clean_100.tar.gz | 7.6 GB | `6df668d8f5f33e70876bfa33862ad02b` |
| train_clean_360.tar.gz | 27 GB | `382eb3e64394b3da6a559f864339b22c` |
| dev_clean.tar.gz | 1.3 GB | `2c1f5312914890634cc2d15783032ff3` |
| test_clean.tar.gz | 1.3 GB | `4d373d453eb96c0691e598061bbafab7` |

ダウンロード元は `https://openslr.trmal.net/resources/141/` である。

## ディレクトリの再配置

SiFiGAN の `extract_features.py` は、`path_replace()` で `in_dir="wav"` を `out_dir="hdf5"` に文字列置換して出力先を決める。
そのため、WAV ファイルを `{speaker}/wav/{file}.wav` というパスに置いておく必要がある。

### LibriTTS-R

- 元の構造：`LibriTTS_R/{subset}/{speaker}/{chapter}/{file}.wav`
- 再配置後：`LibriTTS_R/{subset}/{speaker}/wav/{file}.wav`（シンボリックリンク）

Python の一括処理で、33,232（train-clean-100）+ 116,462（train-clean-360）+ 5,736（dev-clean）+ 4,837（test-clean）= 160,267 個のシンボリックリンクを作成した。
再配置にかかった時間は各サブセットで約 5〜11 秒である。

### VocalSet

- 元の構造：`VocalSet11/FULL/{singer}/{exercise}/{technique}/{file}.wav`
- 再配置後：`VocalSet11/FULL/{singer}/wav/{file}.wav`（シンボリックリンク、straight と vibrato のみ）

616 個のシンボリックリンクを作成した。

## SCP ファイル

| 分割 | ファイル数 | 内容 |
|---|---|---|
| train_no_dev | 150,158 | LibriTTS-R train-clean-100/360 + VocalSet train歌手 |
| dev | 5,736 | LibriTTS-R dev-clean |
| eval | 4,989 | LibriTTS-R test-clean + VocalSet eval歌手 |

## 特徴量抽出

パラメータは `minf0=60 maxf0=1000 sample_rate=24000` である。

### 所要時間

| 分割 | 開始 | 完了 | 所要時間 |
|---|---|---|---|
| train_no_dev (150,158) | 00:06 UTC | 10:21 UTC | 約10時間15分 |
| dev (5,736) | 10:21 UTC | 10:47 UTC | 約26分 |
| eval (4,989) | 10:48 UTC | 11:12 UTC | 約25分 |
| 統計量計算 | 11:12 UTC | 11:27 UTC | 約15分 |

10 プロセス並列で、処理速度は約 256 HDF5/分だった。
総所要時間は約 11 時間 20 分である。

### HDF5 の生成数

| ソース | 生成数 | 期待数 | 備考 |
|---|---|---|---|
| LibriTTS-R | 160,267 | 160,267 | 全量生成 |
| VocalSet | 616 | 616 | 全ファイルで警告発生（後述） |

### 統計ファイル

`data/stats/libritts_r_clean+vocalset11_train_no_dev.joblib`（2.5KB）を生成した。

## 見つかった問題

### 1. np.float の削除（修正済み）

`extract_features.py:272` は `np.float` を使っていた。
numpy 2.0 以降では `np.float` が削除されているため、ここで AttributeError が発生した。
`np.float64` に修正した（commit `a354202`）。

### 2. VocalSet のサンプルレート不一致（解決済み）

VocalSet の WAV ファイルは 44,100 Hz だが、特徴量抽出は 24,000 Hz の入力を前提としている。
そのため初回の抽出では、616 件すべてで「Resample before feature extraction」警告が出た。

**解決**：soxr ライブラリで 616 ファイルすべてを 44,100 Hz から 24,000 Hz にリサンプリングした。
手順は次のとおりである。

1. 各歌手ディレクトリに `wav_24k/` を作り、リサンプリング後のファイルを置く。
2. `wav/` のシンボリックリンクを 24kHz のファイルに差し替える。
3. HDF5 を削除して特徴量を再抽出する。

再抽出では Resample 警告は出なかった。

### 3. シンボリックリンク作成の速度（修正済み）

初回の実行では、bash の find+while+ln ループが極端に遅かった（10 万ファイルで 20 分以上）。
Python の os.symlink を使う処理に書き換え、5 秒に短縮した（commit `5253cfb`）。

## ストレージ配置

### NFS の小ファイル問題

LibriTTS-R の HDF5 は 160,267 個の小さなファイルからなり、実データは合計 59.3GB である。
これを NFS の永続ストレージに直接置くと、ブロック単位の割り当てのために 66GB 以上を消費し、容量 98GB のストレージを圧迫する。

### B2 Storage (Backblaze)

そこで、HDF5 を tar.gz にまとめて B2 Storage に保存する方式を採った。

| ファイル | B2パス | サイズ | 備考 |
|---|---|---|---|
| LibriTTS-R HDF5 | `s3://pakari/libritts_r_hdf5.tar.gz` | 59.3 GiB | 160,267個のh5ファイル |
| VocalSet HDF5 | `s3://pakari/vocalset11_hdf5.tar.gz` | 508 MiB | 616個のh5ファイル（24kHzリサンプリング済み） |

B2 の接続情報は次のとおりである。

- Endpoint：`s3.us-west-004.backblazeb2.com`
- Bucket：`pakari`
- 認証情報：リポジトリ直下の `.env`（コミットしない）に、キー ID を `B2_APPLICATION_KEY_ID`、シークレットを `B2_APPLICATION_KEY` として書く。
- アクセスには aws CLI を使う（`uv tool install awscli` で導入する）。

### コンテナ再起動時の復元手順

```bash
# 1. /repo シンボリックリンク再作成（再起動で消える）
sudo ln -sf /data/share159 /repo

# 2. aws CLI導入（エフェメラルなので再起動で消える）
export PATH="/repo/.local/bin:/home/ubuntu/.local/bin:$PATH"
uv tool install awscli

# 3. B2からHDF5をダウンロード・展開（認証情報は .env から読む）
. /repo/SiFiGAN/.env
export AWS_ACCESS_KEY_ID="$B2_APPLICATION_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$B2_APPLICATION_KEY"
mkdir -p /tmp/libritts_r
aws s3 cp s3://pakari/libritts_r_hdf5.tar.gz /tmp/libritts_r_hdf5.tar.gz \
    --endpoint-url https://s3.us-west-004.backblazeb2.com
tar xzf /tmp/libritts_r_hdf5.tar.gz -C /tmp/libritts_r
rm /tmp/libritts_r_hdf5.tar.gz

# 4. egsからシンボリックリンク作成
cd /repo/SiFiGAN/egs/libritts-r-clean+vocalset11
ln -s /tmp/libritts_r/LibriTTS_R LibriTTS_R
ln -s /repo/VocalSet11 VocalSet11
```

### 永続ストレージの内容

| 場所 | 内容 | 備考 |
|---|---|---|
| 永続 `/repo/SiFiGAN/` | リポジトリ + .venv | uv sync済み |
| 永続 `/repo/VocalSet11/` | VocalSet WAV + HDF5 | リサンプリング未実施 |
| 永続 `/repo/SiFiGAN/egs/.../data/stats/` | 統計ファイル (.joblib) | 学習に必要 |
| 永続 `/repo/logs/` | 作業ログ | 再現性記録 |
| B2 `s3://pakari/` | LibriTTS-R HDF5 tar.gz | 59.3 GiB |
| エフェメラル `/tmp/libritts_r/` | LibriTTS-R HDF5 (展開後) | 再起動で消失、B2から復元 |
