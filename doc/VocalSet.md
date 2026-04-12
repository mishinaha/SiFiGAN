# VocalSet

歌唱音声データセット。20名の歌手（女性9名・男性11名）による17種類の歌唱技法を収録。

- 入手元: https://zenodo.org/records/1203819 (VocalSet 1.1)
- 展開先 (pakari): `/repo/VocalSet11/FULL/`
- ライセンス: CC BY 4.0 (Zenodoページに記載)

### バージョンについて

VocalSet 1.2 (https://zenodo.org/records/1442513) も存在するが、音声ファイルは1.1と完全に同一（md5sumで確認済み）。1.2はdata_by_singer / data_by_technique / data_by_vowelの3つのビューとして同じファイルを3重コピーしているだけで、新規音声はゼロ。1.1の `FULL/` ディレクトリ (2.7GB) のみで十分。

## 基本統計

| 項目 | 値 |
|---|---|
| WAV総数 | 3,613 |
| 総再生時間 | 31,656秒 (約8.8時間) |
| サンプルレート | 44,100 Hz |
| ビット深度 | 16-bit |
| チャンネル | モノラル |
| 1ファイルの長さ | 最小1.57秒 / 最大81.21秒 / 平均8.76秒 / 中央値8.14秒 |

## ディレクトリ構造

```
VocalSet11/
├── readme-anon.txt               # 歌手の声種一覧
├── train_singers_technique.txt   # 学習用歌手リスト (15名)
├── test_singers_technique.txt    # テスト用歌手リスト (5名)
├── DataSetVocalises.pdf          # 歌手が歌った楽譜
└── FULL/                         # 2.7 GB
    ├── female1/ ... female9/
    └── male1/ ... male11/
        ├── arpeggios/
        │   ├── belt/
        │   ├── breathy/
        │   ├── fast_forte/ slow_forte/ fast_piano/ slow_piano/
        │   ├── lip_trill/ straight/ vibrato/ vocal_fry/
        │   └── ...
        ├── scales/            # arpeggiosと同じ技法サブディレクトリ
        ├── long_tones/
        │   ├── forte/ pp/ straight/ trill/ trillo/
        │   ├── inhaled/ messa/
        │   └── ...
        └── excerpts/
            ├── spoken/ straight/ vibrato/
            └── ...
```

## 歌手一覧

### 女性 (9名)

| ID | 声種 | 分割 |
|---|---|---|
| f1 | ソプラノ | train |
| f2 | ソプラノ | **test** |
| f3 | ソプラノ | train |
| f4 | ソプラノ | train |
| f5 | メゾソプラノ | train |
| f6 | ソプラノ | train |
| f7 | ソプラノ | train |
| f8 | メゾソプラノ | **test** |
| f9 | ソプラノ | train |

### 男性 (11名)

| ID | 声種 | 分割 |
|---|---|---|
| m1 | バリトン | train |
| m2 | テノール | train |
| m3 | テノール | **test** |
| m4 | バス(?) | train |
| m5 | バリトン | **test** |
| m6 | バリトン | train |
| m7 | テノール(?) | train |
| m8 | バス | train |
| m9 | カウンターテノール | train |
| m10 | バスバリトン | **test** |
| m11 | テノール | train |

学習/テスト分割: 15名 (train) / 5名 (test)。歌手単位の分割なので話者リークなし。

## 歌唱技法 (17種)

### arpeggios・scales共通 (10技法)

| 技法 | 説明 | ファイル数 |
|---|---|---|
| belt | 高強度のチェストボイス | 205 |
| breathy | 息混じりの声 | 200 |
| fast_forte | 速いテンポ・フォルテ | 394 |
| fast_piano | 速いテンポ・ピアノ | 386 |
| slow_forte | 遅いテンポ・フォルテ | 395 |
| slow_piano | 遅いテンポ・ピアノ | 397 |
| lip_trill | リップトリル（唇を震わせながら発声） | 202 |
| straight | ビブラートなしの平坦な発声 | 361 |
| vibrato | ビブラート | 260 |
| vocal_fry | ボーカルフライ（低音域のきしみ声） | 198 |

### long_tones専用 (5技法)

| 技法 | 説明 | ファイル数 |
|---|---|---|
| forte | フォルテの持続音 | 100 |
| pp | ピアニッシモの持続音 | 100 |
| trill | 2音間の急速な交替 | 195 |
| trillo | 単音の急速な反復 | — |
| inhaled | 吸気発声 | 100 |
| messa | メッサ・ディ・ヴォーチェ（クレッシェンド→デクレッシェンド） | 99 |

### excerpts専用 (1技法)

| 技法 | 説明 | ファイル数 |
|---|---|---|
| spoken | 話し声での歌唱 | 20 |

## 発声法 (4種)

| 発声法 | 説明 | ファイル数 |
|---|---|---|
| arpeggios | アルペジオ | 1,396 |
| scales | 音階 | 1,384 |
| long_tones | 持続音 | 694 |
| excerpts | 楽曲の抜粋演奏 (Caro mio ben, Dona nobis pacem, Row Row Row Your Boat) | 139 |

## 母音

5つのイタリア語母音。ほぼ均等に分布:

| 母音 | ファイル数 |
|---|---|
| a | 689 |
| e | 694 |
| i | 692 |
| o | 694 |
| u | 693 |

excerptファイルは母音ラベルを持たない。

## ファイル命名規則

### arpeggios・scales (テンポ+ダイナミクス系)

```
{singer}_{vocalise}_{c|f}_{tempo}_{dynamic}_{vowel}.wav
```

- `c` = ascending (do→), `f` = descending (→do)
- 例: `m2_scales_c_slow_forte_a.wav` = male2, 音階, 上行, 遅い, フォルテ, 母音a

### arpeggios・scales (技法系: belt, breathy, lip_trill, straight, vibrato, vocal_fry)

```
{singer}_{vocalise}_{technique}_{vowel}.wav
```

- 例: `f3_arpeggios_vocal_fry_a.wav` = female3, アルペジオ, ボーカルフライ, 母音a

### long_tones

```
{singer}_long_{technique}_{vowel}.wav
```

- 例: `m2_long_trillo_e.wav` = male2, 持続音, トリッロ, 母音e

### excerpts

```
{singer}_{song}_{technique}.wav
```

- 例: `f1_caro_vibrato.wav` = female1, Caro mio ben, ビブラート

歌手IDの略記: f1-f9 = female1-female9, m1-m11 = male1-male11。

## 歌手あたりのファイル数

| 歌手 | ファイル数 | 歌手 | ファイル数 |
|---|---|---|---|
| female1 | 182 | male1 | 179 |
| female2 | 189 | male2 | 181 |
| female3 | 183 | male3 | 179 |
| female4 | 156 | male4 | 182 |
| female5 | 182 | male5 | 182 |
| female6 | 187 | male6 | 178 |
| female7 | 183 | male7 | 182 |
| female8 | 182 | male8 | 182 |
| female9 | 178 | male9 | 182 |
| | | male10 | 182 |
| | | male11 | 182 |

female4が最少 (156)、female2が最多 (189)。

## データ品質の注意点

- **歌手ID欠落**: 32ファイルが歌手IDプレフィックスを持たない（例: `arpeggios_straight_a.wav`）
- **ファイル名のtypo**: `arepggios`（arpeggiosの誤記）、`sow_forte`（slow_forteの誤記）
- **重複マーカー**: `scales_f_slow_piano_u(1).wav` のような `(1)` 付きファイルが存在
- **`__MACOSX/`**: macOSメタデータ、無視すること

## SiFiGAN学習に向けた考慮事項

- **リサンプリング必要**: SiFiGANのデフォルト設定は24kHzだが、VocalSetは44.1kHz
- **ピッチ多様性**: バスからソプラノ、カウンターテノールまで広いF0範囲をカバー。SiFiGANのF0依存モデルに適している
- **技法の選択**: クリーンなボコーダ学習にはstraight・vibratoが最も自然。inhaled・lip_trill・vocal_fryは非定常的で学習が難しい可能性がある
- **音素の限界**: 5つのイタリア語母音のみ。子音・二重母音・閉母音なし
- **データ量**: 歌手あたり約25-27分。単一話者モデルには少ないが、多話者モデルの一部としては十分
