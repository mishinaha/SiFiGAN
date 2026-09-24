# VocalSet

VocalSet は歌唱音声のデータセットで、20 名の歌手（女性 9 名、男性 11 名）が 17 種類の歌唱技法で歌った音声を収録している。

- 入手元：https://zenodo.org/records/1203819 （VocalSet 1.1）
- 展開先（pakari）：`/repo/VocalSet11/FULL/`
- ライセンス：CC BY 4.0（Zenodo のページに記載）

### バージョンについて

VocalSet 1.2（https://zenodo.org/records/1442513 ）もあるが、音声ファイルは 1.1 とまったく同じである（md5sum で確認した）。
1.2 は同じファイルを data_by_singer、data_by_technique、data_by_vowel の 3 つのビューとして 3 重にコピーしているだけで、新しい音声は 1 つもない。
したがって、1.1 の `FULL/` ディレクトリ（2.7GB）だけで足りる。

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

学習用とテスト用の分割は 15 名（train）と 5 名（test）である。
歌手単位で分割しているので、同じ話者が学習とテストの両方に入ること（話者リーク）はない。

## 歌唱技法 (17種)

### arpeggios と scales に共通 (10技法)

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

### long_tones 専用 (5技法)

| 技法 | 説明 | ファイル数 |
|---|---|---|
| forte | フォルテの持続音 | 100 |
| pp | ピアニッシモの持続音 | 100 |
| trill | 2音間の急速な交替 | 195 |
| trillo | 単音の急速な反復 | — |
| inhaled | 吸気発声 | 100 |
| messa | メッサ・ディ・ヴォーチェ（クレッシェンド→デクレッシェンド） | 99 |

### excerpts 専用 (1技法)

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

母音はイタリア語の 5 母音で、ファイル数はほぼ均等である。

| 母音 | ファイル数 |
|---|---|
| a | 689 |
| e | 694 |
| i | 692 |
| o | 694 |
| u | 693 |

excerpts のファイルには母音ラベルがない。

## ファイル命名規則

### arpeggios と scales（テンポとダイナミクスの組み合わせ）

```
{singer}_{vocalise}_{c|f}_{tempo}_{dynamic}_{vowel}.wav
```

- `c` は ascending（do→）、`f` は descending（→do）を表す。
- 例：`m2_scales_c_slow_forte_a.wav` は male2、音階、上行、遅い、フォルテ、母音 a を表す。

### arpeggios と scales（技法：belt, breathy, lip_trill, straight, vibrato, vocal_fry）

```
{singer}_{vocalise}_{technique}_{vowel}.wav
```

- 例：`f3_arpeggios_vocal_fry_a.wav` は female3、アルペジオ、ボーカルフライ、母音 a を表す。

### long_tones

```
{singer}_long_{technique}_{vowel}.wav
```

- 例：`m2_long_trillo_e.wav` は male2、持続音、トリッロ、母音 e を表す。

### excerpts

```
{singer}_{song}_{technique}.wav
```

- 例：`f1_caro_vibrato.wav` は female1、Caro mio ben、ビブラートを表す。

歌手 ID は略記で、f1〜f9 が female1〜female9、m1〜m11 が male1〜male11 に対応する。

## 歌手ごとのファイル数

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

最も少ないのは female4（156）、最も多いのは female2（189）である。

## データ品質の注意点

- **歌手 ID の欠落**：32 ファイルが歌手 ID のプレフィックスを持たない（例：`arpeggios_straight_a.wav`）。
- **ファイル名の誤記**：`arepggios`（arpeggios の誤記）、`sow_forte`（slow_forte の誤記）がある。
- **重複マーカー**：`scales_f_slow_piano_u(1).wav` のように `(1)` が付いたファイルがある。
- **`__MACOSX/`**：macOS のメタデータなので無視する。

## SiFiGAN の学習に使うときの考慮事項

- **リサンプリングが必要**：SiFiGAN のデフォルト設定は 24kHz だが、VocalSet は 44.1kHz である。
- **ピッチの多様性**：バスからソプラノ、カウンターテノールまで、広い F0 範囲をカバーしている。F0 に依存する SiFiGAN のモデルの学習に向いている。
- **技法の選び方**：クリーンなボコーダを学習するには、straight と vibrato が最も自然である。inhaled、lip_trill、vocal_fry は非定常的な発声なので、学習が難しくなる可能性がある。
- **音素の限界**：イタリア語の 5 母音しかなく、子音、二重母音、閉母音は含まれない。
- **データ量**：歌手あたり約 25〜27 分である。単一話者モデルには少ないが、多話者モデルの学習データの一部としては十分である。
