# Typhoon-Analyze Web アプリ 設計書

- 作成日: 2026-08-23
- 対象: アプリケーション側（Streamlit）。スクレイピング・前処理はデータ担当（別メンバー）
- 関連: `CLAUDE.md`（目的・役割分担・決定事項）

## 1. 目的とスコープ

2025 年に九州・沖縄へ接近した台風（第 8 号・第 12 号・第 15 号など）について、九州・沖縄 8 地点
（福岡・佐賀・長崎・熊本・大分・宮崎・鹿児島・那覇）の気象（気圧・風速・降水量・気温）が
台風接近の前後でどう変化したかを、台風の接近時刻と重ねて可視化する Web アプリ。

### スコープ内
- 台風の選択、地点の選択、表示期間の調整
- 地点別サマリ（最低気圧・最大風速・総降水量など）とランキング
- 要素別の時系列グラフ（台風の上陸/接近時刻を縦線で重ねる）
- 地図（地点マーカー＋台風経路、時刻スライダー）
- 集計・分析ロジック（アプリ側の責務）
- 気象データのキャッシュ管理とオンデマンド取得の呼び出し

### スコープ外
- 気象庁サイトのスクレイピング・生データの整形（データ担当）
- 台風中心からの距離と観測値の定量分析（将来の拡張候補）
- 過去台風との比較、機械学習による予測

## 2. 前提・決定事項

| 項目 | 決定 |
|---|---|
| フレームワーク | Streamlit。可視化は Plotly に一本化（地図は OpenStreetMap タイル、トークン不要） |
| 構造 | レイヤー分割パッケージ `typhoon_app/` ＋ 1 ページ（サイドバー＋3 タブ） |
| 気象項目 | 気温・降水量・風速・風向・現地気圧・天気 の 6 項目。追加項目は `config.py` の要素定義に足せば増やせる |
| データ取得 | ハイブリッド: `data/processed/` のキャッシュ CSV を読む。無ければデータ側の `fetch_weather` をオンデマンドで呼び、結果を保存 |
| 取得窓 | 台風の接近基準時刻の前後 7 日を固定窓で 1 回取得。UI の「前後 N 日」(1〜7) はその絞り込み |
| 台風経路 | `track.csv`（全経路）があれば線、無ければ `landfall.csv`（上陸/接近点）で点表示 |
| 集計の責務 | アプリ側 |
| 環境管理 | uv（`pyproject.toml` + `uv.lock`）。Community Cloud 向けに `requirements.txt` を `uv export` で生成 |
| デプロイ | Streamlit Community Cloud を想定。データはリポジトリ同梱 |
| UI 言語 | 日本語。利用者は未定のため気象の非専門家を想定し、用語注釈を付ける |

## 3. 画面構成

1 ページ＋サイドバー＋3 タブ。操作は「台風を選ぶ → 地点を選ぶ → タブを見る」の 3 ステップ。

```
┌─ サイドバー ───────────┬─ メイン ───────────────────────────────────────┐
│ 台風を選択 [▼2025年 第12号] │ 台風 第12号（2025）  上陸/最接近: 8/21 17:00 鹿児島付近 │
│   （番号・接近日を併記）   │ 中心気圧 994hPa / 最大風速 45kt   ← 台風データから     │
│                            ├──────────────────────────────────────────────┤
│ 地点を選択 [☑福岡 ☑鹿児島…] │ [概要] [時系列] [地図]                                │
│   （8地点 multiselect）    ├──────────────────────────────────────────────┤
│                            │ ▼ 概要タブ                                           │
│ 表示期間                   │  地点ごとのサマリ表：最低気圧 / 最大風速 / 総降水量 /  │
│   接近日の前後 [==3==] 日  │  最接近(最低気圧)時刻 / 欠測率                         │
│                            │  ランキング棒グラフ（最低気圧・最大風速・総降水量）    │
│ 気象要素                   │                                                      │
│   [☑気圧 ☑風速 ☑降水 ☐気温]│ ▼ 時系列タブ                                         │
│                            │  要素ごとに1枚のグラフ（地点で色分け、降水は棒）       │
│ ──────────────             │  台風の上陸/最接近時刻に縦線                           │
│ データ状態                 │                                                      │
│  ● キャッシュ済み          │ ▼ 地図タブ                                           │
│  ○ 取得中… / ✕ 取得失敗   │  8地点のマーカー（色＝選択要素の値）＋台風経路（線/点） │
│                            │  時刻スライダーで地点の値と台風位置が同期して動く      │
│ ℹ 用語の説明（expander）   │                                                      │
└────────────────────────────┴──────────────────────────────────────────────┘
```

### サイドバー
- **台風を選択**: `landfall.csv` から自動生成。表示は「2025年 第12号（8/21 接近）」のように番号と接近日を併記。既定は 2025 年の最新。
- **地点を選択**: 8 地点の multiselect。既定は全地点。
- **表示期間**: 接近基準時刻の前後 N 日（1〜7、既定 3）。スライダー操作で再取得は起きない。
- **気象要素**: 気圧・風速・降水量・気温の multiselect。既定は気圧・風速・降水量。
- **データ状態**: 地点ごとに「キャッシュ済み / 取得中 / 取得失敗 / 未取得」を表示。
- **用語の説明**: hPa、最接近時刻の定義、欠測率などの短い注釈を expander に置く。

### メイン
- **ヘッダ**: 台風番号・年、上陸/接近時刻（複数あれば列挙）、中心気圧、最大風速（`landfall.csv` から）。「鹿児島付近」のような地名は `landfall.csv` に無いため、緯度経度から最寄りの観測地点をアプリ側で算出して表示する（§6）。
- **概要タブ**: 地点別サマリ表（§6 の指標）とランキング棒グラフ。
- **時系列タブ**: 選択要素ごとに 1 枚のグラフ。地点で色分け、降水量は棒グラフ、他は折れ線。接近基準時刻に縦線。欠測は線を切る。
- **地図タブ**: 地点マーカー（色＝選択要素の値）、台風経路（線または点）、時刻スライダーで地点の値と台風位置を同期表示。
- 「地点比較」タブは作らない。概要タブのサマリ表とランキングで代替する。

## 4. データ契約（データ担当との取り決め）

アプリが外部に依存するのは **関数 1 つ＋CSV 3 種**。

### 4-1. 気象データ取得関数（オンデマンド用）

```python
class WeatherFetchError(Exception): ...

def fetch_weather(station: str, start: datetime.date, end: datetime.date) -> pd.DataFrame:
    """指定地点・期間（両端含む、日単位）の時別値を取得し、§4-2 の形の DataFrame を返す。
    失敗時は WeatherFetchError を送出する。"""
```

- 日付の決定はアプリ側が行う（台風データから接近基準時刻を引き、前後 7 日を計算）。データ側は「地点＋期間」だけ扱えばよい。
- 置き場所はデータ側の任意（例: `preprocess/weather_source.py`）。アプリは `typhoon_app/data/source.py` からのみ import する。
- 気象庁サイトへの連続アクセスの間隔制御は関数の内部（データ側）の責務。

### 4-2. 気象データのスキーマ（関数の戻り値＝キャッシュ CSV、tidy/縦持ち）

| カラム | 型 | 内容・ルール |
|---|---|---|
| `station` | str | 地点名（福岡・佐賀・長崎・熊本・大分・宮崎・鹿児島・那覇） |
| `datetime` | datetime（JST、tz なし） | 観測時刻。**「24時」は翌日 00:00 に正規化** |
| `temperature` | float | 気温 ℃ |
| `precipitation` | float | 降水量 mm。**現象なし `--` → 0.0、欠測 → NaN** |
| `wind_speed` | float | 風速 m/s |
| `wind_direction` | str | 16 方位（例: 東南東）。静穏は「静穏」。欠測 → NaN |
| `pressure` | float | 現地気圧 hPa |
| `weather_code` | Int（nullable） | 気象庁の天気コード。コード→名称の対応表はアプリ側（`config.py`）で保持 |

- CSV は UTF-8（BOM 可）、日時は ISO 8601（`2025-08-21 17:00:00`）。
- 欠測は空欄。`×` `///` 等の記号は残さない。
- 1 地点 1 時刻につき 1 行。重複行は無い。

### 4-3. キャッシュ CSV の配置

```
data/processed/
  weather/{typhoon_id}_{station}.csv   例: 202512_鹿児島.csv（接近基準時刻 ±7 日、§4-2 の形）
  typhoon/landfall.csv                 上陸/接近スナップショット（必須）
  typhoon/track.csv                    全経路（任意。あれば地図に線）
  station.csv                          地点マスタ（任意。無ければアプリ内蔵の 8 地点座標）
```

- 気象キャッシュは台風×地点で 1 ファイル。発表用に対象 3 台風 × 8 地点 = 24 ファイルを事前生成してリポジトリに同梱する（`scripts/build_cache.py`）。
- 既存の `data/weather/`・`data/typhoon/`（生データ）はデータ側の作業領域として残し、アプリは `data/processed/` のみ読む。

### 4-4. 台風データのスキーマ（`landfall.csv` / `track.csv` 共通）

| カラム | 型 | 内容 |
|---|---|---|
| `typhoon_id` | str | 例 `202512`（年 4 桁＋号数 2 桁） |
| `datetime` | datetime（JST） | `2025年08月21日17時00分(JST)` → `2025-08-21 17:00:00` |
| `lat`, `lon` | float | 緯度・経度（度） |
| `pressure` | float | 中心気圧 hPa |
| `max_wind_kt` | float | 最大風速 kt |
| `storm_diameter_nm` | float（nullable） | 暴風域直径 nm。`-` → NaN |
| `gale_diameter_nm` | float（nullable） | 強風域直径 nm。`-` → NaN |

- `landfall.csv` は現行 `data/typhoon/typhoon_track.csv`（実体 xlsx、1991〜2025 年・258 行）をこの形に変換したもの。
- `track.csv` は 6 時間毎程度の全経路（気象庁ベストトラック等）。無くてもアプリは動く。

### 4-5. 地点マスタ `station.csv`

`station, lat, lon, prec_no, block_no` の 5 列。アプリは 8 地点の既定座標を `config.py` に内蔵し、このファイルがあれば上書きする。

## 5. モジュール構成とデータフロー

```
app.py                      # 入口。ページ設定→サイドバー→データ取得→タブ描画を呼ぶだけ（ロジック無し）
typhoon_app/
  config.py                 # 定数: 地点 8 つ＋既定座標、要素定義（列名/表示名/単位/色）、天気コード表、MAX_WINDOW_DAYS=7、パス
  data/
    schema.py               # カラム定義と検証 validate_weather(df) / validate_typhoon(df)
    typhoon.py              # landfall.csv / track.csv 読込、台風一覧、接近基準時刻と取得窓の算出
    weather.py              # get_weather(typhoon_id, stations): キャッシュ読込 → 無ければ source → 保存
    source.py               # データ側 fetch_weather のアダプタ（import 失敗時はキャッシュ専用モード）
    station.py              # station.csv 読込（無ければ config の既定座標）
  analysis/
    summary.py              # 地点別サマリ（最低気圧・最大風速・総降水量・各時刻・欠測率）
    timeseries.py           # 期間での絞り込み、要素ごとの整形（long→wide）
  charts/
    timeseries.py           # 要素別ライン/棒グラフ → plotly Figure
    map.py                  # 地点マーカー＋台風経路（線/点）＋時刻スライダー → plotly Figure
    ranking.py              # ランキング棒グラフ → plotly Figure
  ui/
    state.py                # Selection dataclass（typhoon_id, stations, window_days, variables）、データ状態 enum
    sidebar.py              # サイドバー描画 → Selection を返す
    header.py / tab_overview.py / tab_timeseries.py / tab_map.py / glossary.py
scripts/
  build_cache.py            # 対象台風×8 地点のキャッシュ CSV を一括生成（発表前に実行）
tests/
  fixtures/                 # 数十行の小さなサンプル CSV
  test_schema.py / test_analysis_summary.py / test_data_weather.py / test_charts_smoke.py
```

### 責務の境界
- `data/`: ファイルと外部関数に触るのはここだけ。戻り値は検証済み DataFrame。
- `analysis/`・`charts/`: DataFrame を受けて DataFrame / Figure を返す純関数。Streamlit を import しない。
- `ui/`・`app.py`: Streamlit の呼び出しはここだけ。

### データフロー（1 回の描画）

```
sidebar → Selection
  → data.typhoon.get_event(typhoon_id)            # 接近基準時刻・取得窓（±7 日）・経路（線/点）
  → data.weather.get_weather(typhoon_id, stations)  # 地点ごと: cache hit → 読む / miss → fetch → 保存
  → analysis.timeseries.clip(df, ±window_days)
  → analysis.summary.summarize(df)                # 概要タブ用
  → charts.*(…) → ui.tab_*.render(...)
```

- 読込系（台風・地点マスタ・台風×地点の気象）は `st.cache_data` でメモリキャッシュ。永続化はファイルキャッシュが担う。
- `get_weather` の戻り値は `{station: DataFrame | エラー情報}` とし、地点単位の成否を UI に渡す。

## 6. 集計・分析の定義

| 指標 | 定義 |
|---|---|
| 接近基準時刻（台風単位） | `landfall.csv` の該当台風の時刻。複数あれば全てを時系列グラフに縦線で表示。取得窓 = [最初の時刻 −7 日, 最後の時刻 +7 日]。表示窓 = 最初の時刻 −N 日 〜 最後の時刻 +N 日 |
| 最低気圧・その時刻 | 表示窓内の `pressure` の最小値と発生時刻。地点の「最接近時刻」の代理指標 |
| 最大風速・その時刻・風向 | `wind_speed` の最大値、発生時刻、そのときの `wind_direction` |
| 総降水量 | `precipitation` の合計（NaN 除外） |
| 最大 1 時間降水量・時刻 | `precipitation` の最大値と時刻 |
| 最高/最低気温 | 気温が選択されているときのみ |
| 欠測率 | 表示窓内の欠測セル数 ÷ 全セル数（%）。サマリ表に併記 |
| ランキング | 上記指標で地点を並べた棒グラフ（最低気圧は昇順、他は降順） |
| 地図の色 | スライダーで選んだ時刻の、選択要素の値。該当時刻が欠測なら灰色 |
| 最寄り観測地点（表示用） | 上陸/接近点の緯度経度から 8 地点のうち最も近い地点名（大円距離）。ヘッダの「◯◯付近」に使う |

欠測の扱い: 集計は NaN を無視。時系列グラフは欠測部分で線を切る（補間しない）。降水の 0 は 0 として描く。

## 7. エラーハンドリングと状態表示

| 状況 | 挙動 |
|---|---|
| キャッシュ CSV あり | 即表示。サイドバーに「● キャッシュ済み」 |
| キャッシュなし・`fetch_weather` 利用可 | `st.spinner("気象庁から取得中…")` で地点ごとに取得→保存→表示。地点単位で進捗表示 |
| キャッシュなし・`fetch_weather` が import 不可（未実装） | 「この台風のデータは未取得です（キャッシュ専用モード）」と `st.warning`。取得済みの地点だけ表示 |
| 取得失敗（`WeatherFetchError` / ネットワーク） | 失敗した地点だけ `st.error` で地点名と理由を表示。他の地点は表示を続ける。再試行ボタンあり |
| スキーマ検証エラー | 期待と異なるカラム/型を列挙して停止（データ担当への報告に使える） |
| `landfall.csv` が無い | 起動時に「台風データがありません」と停止（必須データ） |
| `track.csv` が無い | 地図は点表示にフォールバック（警告なし、凡例に「上陸/接近地点」） |
| `station.csv` が無い | 内蔵の 8 地点座標を使用（警告なし） |
| 表示窓内に全欠測の地点 | サマリ表は「—」、グラフは凡例のみ |

原則: 部分的に失敗しても取れているものは見せる（発表中に画面を空にしない）。

## 8. テスト方針

- 対象: `data/schema.py`、`data/weather.py`（キャッシュ／フォールバック分岐）、`data/typhoon.py`（窓の算出）、`analysis/*`、`charts/*`。`ui/`・`app.py` は対象外。
- `tests/fixtures/` に数十行の小さな CSV（2 地点×2 日、欠測・日付境界・`--`→0 を含む）を置き、集計値を手計算と照合。
- `charts/*` は「Figure が返る・トレース数が地点数と一致」のスモークテスト。
- `data/weather.py` は `fetch_weather` をモックに差し替え、(a) キャッシュヒット時は呼ばれない (b) ミス時に呼ばれて保存される (c) 例外時に他地点が続行される、を確認。
- pytest。実装は TDD で進める。

## 9. 環境・デプロイ・運用

- **uv** で管理: `pyproject.toml` に依存（streamlit, pandas, plotly, pyarrow）、dev グループに pytest。`uv.lock` をコミット。`.python-version` で 3.12 を固定。
  - ローカル: `uv sync` → `uv run streamlit run app.py`、テストは `uv run pytest`。
  - bs4 / openpyxl 等のデータ側依存はデータ担当が `uv add` する。
- **Streamlit Community Cloud**: GitHub 連携、エントリは `app.py`。Cloud 側の uv 対応に依存しないよう `uv export --format requirements-txt --no-dev > requirements.txt` で UTF-8 の `requirements.txt` を生成してコミット（現状の UTF-16 版を置き換える）。
- データはリポジトリ同梱（`data/processed/`）。秘密情報・外部トークンは不要。
- Cloud 上のオンデマンド取得は「動くが遅い」前提。発表前に `scripts/build_cache.py` で 24 ファイルを生成してコミットする。
- `.gitignore` を追加（`.venv/`, `__pycache__/`, `.pytest_cache/`, `.streamlit/secrets.toml` 等）。
- README に起動手順・データ配置・データ契約へのリンクを記載。

## 10. データ担当への依頼事項（まとめ）

1. `fetch_weather(station, start, end)` を §4-1/§4-2 の仕様で実装（モジュール名・場所を教えてもらう）。
2. 現行 `data/typhoon/typhoon_track.csv`（xlsx）を §4-4 の形の `data/processed/typhoon/landfall.csv` に変換。
3. 可能なら全経路 `data/processed/typhoon/track.csv`（6 時間毎程度）を用意。
4. 可能なら `data/processed/station.csv`（緯度経度）を用意。
5. データ側依存（beautifulsoup4, openpyxl 等）を `pyproject.toml` に追加。

## 11. 未決事項・拡張候補

- 利用者・利用シーン、評価観点、発表日は未定（CLAUDE.md 参照）。分かり次第、最小構成の優先順位に反映。
- 拡張候補（スコープ外）: 地点比較タブ、台風中心からの距離と観測値の関係（`track.csv` と地点座標があれば可能）、過去台風との比較、追加気象項目（海面気圧・湿度・日照など）。
