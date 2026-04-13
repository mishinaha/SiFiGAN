# データ準備作業記録

LibriTTS-R + VocalSet11 のフルスクラッチ学習用データ準備の記録。

## 実行環境

- マシン: `ssh pakari` (packet.ai RTX PRO 6000 Blackwell, 96コア, 1.5TB RAM)
- Git commit (実行時): `a354202` (np.float64修正後)
- ログ: `/repo/logs/prepare.log`

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

## LibriTTS-R ダウンロード結果

| ファイル | サイズ | MD5 |
|---|---|---|
| train_clean_100.tar.gz | 7.6 GB | `6df668d8f5f33e70876bfa33862ad02b` |
| train_clean_360.tar.gz | 27 GB | `382eb3e64394b3da6a559f864339b22c` |
| dev_clean.tar.gz | 1.3 GB | `2c1f5312914890634cc2d15783032ff3` |
| test_clean.tar.gz | 1.3 GB | `4d373d453eb96c0691e598061bbafab7` |

ダウンロード元: `https://openslr.trmal.net/resources/141/`

## ディレクトリ再配置

SiFiGANの`extract_features.py`は`path_replace()`で`in_dir="wav"`→`out_dir="hdf5"`の文字列置換を行うため、WAVファイルが`{speaker}/wav/{file}.wav`というパスに配置されている必要がある。

### LibriTTS-R

元の構造: `LibriTTS_R/{subset}/{speaker}/{chapter}/{file}.wav`
再配置後: `LibriTTS_R/{subset}/{speaker}/wav/{file}.wav` (シンボリックリンク)

Python一括処理で33,232 (train-clean-100) + 116,462 (train-clean-360) + 5,736 (dev-clean) + 4,837 (test-clean) = 160,267個のシンボリックリンクを作成。再配置は各サブセットで約5-11秒。

### VocalSet

元の構造: `VocalSet11/FULL/{singer}/{exercise}/{technique}/{file}.wav`
再配置後: `VocalSet11/FULL/{singer}/wav/{file}.wav` (シンボリックリンク、straight + vibratoのみ)

616個のシンボリックリンクを作成。

## SCPファイル

| 分割 | ファイル数 | 内容 |
|---|---|---|
| train_no_dev | 150,158 | LibriTTS-R train-clean-100/360 + VocalSet train歌手 |
| dev | 5,736 | LibriTTS-R dev-clean |
| eval | 4,989 | LibriTTS-R test-clean + VocalSet eval歌手 |

## 特徴量抽出

パラメータ: `minf0=60 maxf0=1000 sample_rate=24000`

### 所要時間

| 分割 | 開始 | 完了 | 所要時間 |
|---|---|---|---|
| train_no_dev (150,158) | 00:06 UTC | 10:21 UTC | 約10時間15分 |
| dev (5,736) | 10:21 UTC | 10:47 UTC | 約26分 |
| eval (4,989) | 10:48 UTC | 11:12 UTC | 約25分 |
| 統計量計算 | 11:12 UTC | 11:27 UTC | 約15分 |

処理速度: 約256 HDF5/分（10プロセス並列）。総所要時間: 約11時間20分。

### HDF5生成数

| ソース | 生成数 | 期待数 | 備考 |
|---|---|---|---|
| LibriTTS-R | 160,267 | 160,267 | 全量生成 |
| VocalSet | 616 | 616 | 全ファイルで警告発生（後述） |

### 統計ファイル

`data/stats/libritts_r_clean+vocalset11_train_no_dev.joblib` (2.5KB) を生成。

## 発見された問題

### 1. np.float 削除 (修正済み)

`extract_features.py:272` で `np.float` を使用していたが、numpy 2.0以降で削除されたためAttributeError。`np.float64` に修正済み (commit `a354202`)。

### 2. VocalSetのサンプルレート不一致 (未解決)

VocalSetのWAVファイルは44,100 Hzだが、特徴量抽出は24,000 Hzを期待。616件全てで「Resample before feature extraction」警告が発生。HDF5は616件生成されているが、サンプルレート不一致のまま処理された特徴量の品質は不明。

**対策案:**
- VocalSetのWAVを事前に24kHzにリサンプリングする（librosaやsoxで変換）
- 変換後に特徴量を再抽出

### 3. シンボリックリンク作成の速度 (修正済み)

初回実行ではbashのfind+while+lnループが極端に遅かった（10万ファイルで20分以上）。Pythonのos.symlinkに書き換えて5秒に短縮 (commit `5253cfb`)。

## ストレージ配置

| 場所 | 内容 | 備考 |
|---|---|---|
| エフェメラル `/tmp/libritts_r/` | LibriTTS-R WAV + HDF5 | 再起動で消失 |
| 永続 `/repo/VocalSet11/` | VocalSet WAV + HDF5 | 永続 |
| 永続 `/repo/SiFiGAN/egs/.../data/scp/` | SCPファイル | Git管理 |
| 永続 `/repo/SiFiGAN/egs/.../data/stats/` | 統計ファイル | 学習に必要 |

**注意**: LibriTTS-RのHDF5はエフェメラルストレージに生成される。コンテナ再起動時は特徴量抽出の再実行が必要。ただし.listファイル（自動生成）はegs内に保存されるためGit管理可能。

### 完了後のディスク使用量

| 場所 | 使用量 | 容量 |
|---|---|---|
| 永続 (/repo) | 18 GB | 98 GB (20%) |
| エフェメラル (/tmp) | 434 GB | 3.5 TB (13%) |
