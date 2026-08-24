# Typhoon-Analyze Web アプリ 設計書

- 作成日: 2026-08-23
- 対象: アプリケーション側（Streamlit）。スクレイピング・前処理はデータ担当（別メンバー）

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
| 気象項目 | 気温・降水量・風速・現地気圧 の 4 項目（気象データ契約は station, datetime, temperature, precipitation, wind_speed, pressure の 6 列）。追加項目は `config.py` の要素定義に足せば増やせる |
| データ取得 | ハイブリッド: `data/processed/` のキャッシュ CSV を読む。無ければデータ側の `fetch_weather` をオンデマンドで呼び、結果を保存 |
| 取得窓 | 台風データの期間（最初〜最後の時刻）の前後 1 日を固定窓で取得・表示。UI の期間スライダーは廃止 |
| 台風経路 | `track.csv`（必須の 1 本。現行データは台風あたり 1〜6 点のスナップショット。時別データが手に入れば同じ 6 列で差し替え可）を線と時刻ごとの位置マーカーで表示 |
| 集計の責務 | アプリ側 |
| 環境管理 | uv（`pyproject.toml` + `uv.lock`）。Community Cloud 向けに `requirements.txt` を `uv export` で生成 |
| デプロイ | Streamlit Community Cloud を想定。データはリポジトリ同梱 |
| UI 言語 | 日本語。利用者は未定のため気象の非専門家を想定し、用語注釈を付ける |
| 地点拡張 | 2026-08-24: 全国の気象官署（約150地点）に対応。既定の選択・同梱キャッシュは従来の九州・沖縄8地点のまま。アメダスは対象外 |

## 3. 画面構成

1 ページ＋サイドバー＋3 タブ。操作は「台風を選ぶ → 地点を選ぶ → タブを見る」の 3 ステップ。

```
┌─ サイドバー ───────────┬─ メイン ───────────────────────────────────────┐
│ 台風を選択 [▼2025年 第12号] │ 台風 第12号（2025）  対象期間 8/20 09:00〜8/23 03:00   │
│   （番号・期間を併記）     │ 中心気圧 994hPa / 最大風速 45kt   ← 台風データから     │
│                            ├──────────────────────────────────────────────┤
│ 地点を選択 [☑福岡 ☑鹿児島…] │ [概要] [時系列] [地図]                                │
│   （8地点 multiselect）    ├──────────────────────────────────────────────┤
│                            │ ▼ 概要タブ                                           │
│ 気象要素                   │  地点ごとのサマリ表：最低気圧 / 最大風速 / 総降水量 /  │
│   [☑気圧 ☑風速 ☑降水 ☐気温]│  最接近(最低気圧)時刻 / 欠測率                         │
│                            │  ランキング棒グラフ（最低気圧・最大風速・総降水量）    │
│ ──────────────             │                                                      │
│ データ状態                 │ ▼ 時系列タブ                                         │
│  ● キャッシュ済み          │  要素ごとに1枚のグラフ（地点で色分け、降水は棒）       │
│  ○ 取得中… / ✕ 取得失敗   │  台風接近期間を薄い帯で表示                            │
│                            │                                                      │
│ ℹ 用語の説明（expander）   │ ▼ 地図タブ                                           │
│                            │  8地点のマーカー（色＝選択要素の値）＋台風経路（線）   │
│                            │  時刻スライダーで地点の値と台風位置が同期して動く      │
└────────────────────────────┴──────────────────────────────────────────────┘
```

### サイドバー
- **台風を選択**: `track.csv` から自動生成。表示は「2025年 第12号（8/21〜8/22）」のように番号と期間を併記。既定は 2025 年の最新。
- **地点を選択**: 8 地点の multiselect。既定は全地点。
- **気象要素**: 気圧・風速・降水量・気温の multiselect。既定は気圧・風速・降水量。
- **データ状態**: 地点ごとに「キャッシュ済み / 取得中 / 取得失敗 / 未取得」を表示。
- **用語の説明**: hPa、台風接近期間の定義、欠測率などの短い注釈を expander に置く。

### メイン
- **ヘッダ**: 台風番号・年、対象期間（`track.csv` の最初〜最後の時刻）、中心気圧、最大風速。「◯◯付近」のような地名表示は廃止。
- **概要タブ**: 地点別サマリ表（§6 の指標）とランキング棒グラフ。
- **時系列タブ**: 選択要素ごとに 1 枚のグラフ。地点で色分け、降水量は棒グラフ、他は折れ線。台風接近期間を薄い帯で表示。欠測は線を切る。
- **地図タブ**: 地点マーカー（色＝選択要素の値）、台風経路（線＋位置マーカー）、時刻スライダーで地点の値と台風位置を同期表示。選択地点に自動フィット（center・zoom を選択地点の分布から算出）。
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

- 日付の決定はアプリ側が行う（台風データの期間から前後 1 日を計算）。データ側は「地点＋期間」だけ扱えばよい。
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
| `pressure` | float | 現地気圧 hPa |

- CSV は UTF-8（BOM 可）、日時は ISO 8601（`2025-08-21 17:00:00`）。
- 欠測は空欄。`×` `///` 等の記号は残さない。
- 1 地点 1 時刻につき 1 行。重複行は無い。

### 4-3. キャッシュ CSV の配置

```
data/processed/
  weather/{typhoon_id}_{station}.csv   例: 202512_鹿児島.csv（台風データの期間 ±1 日、§4-2 の形）
  typhoon/track.csv                    台風の経路（必須。点の密度は問わない）
  station.csv                          地点マスタ（任意。無ければアプリ内蔵の 8 地点座標）
```

- 気象キャッシュは台風×地点で 1 ファイル。発表用に対象 3 台風 × 8 地点 = 24 ファイルを事前生成してリポジトリに同梱する（`scripts/build_cache.py`）。
- 既存の `data/weather/`・`data/typhoon/`（生データ）はデータ側の作業領域として残し、アプリは `data/processed/` のみ読む。

### 4-4. 台風データのスキーマ（`track.csv`）

| カラム | 型 | 内容 |
|---|---|---|
| `typhoon_id` | str | 例 `202512`（年 4 桁＋号数 2 桁） |
| `datetime` | datetime（JST） | `2025年08月21日17時00分(JST)` → `2025-08-21 17:00:00` |
| `lat`, `lon` | float | 緯度・経度（度） |
| `pressure` | float | 中心気圧 hPa |
| `max_wind_kt` | float | 最大風速 kt |

- `track.csv` は現行 `data/typhoon/typhoon_track.csv`（実体 xlsx、1991〜2025 年・258 行）を `scripts/dev_sample_data.py` でこの形に変換した経路データ 1 本（必須・正式採用 2026-08-24）。台風あたり 1〜6 点のスナップショットで点の密度は問わない（時別データが手に入れば同じ 6 列で差し替えるだけでよい）。最接近時刻の特定は行わない。

### 4-5. 地点マスタ `station.csv`

`station, lat, lon, prec_no, block_no` の 5 列。全国の気象官署一覧（約150地点）を `scripts/build_station_master.py` が気象庁の観測所選択ページから生成し、`data/processed/station.csv` として同梱・スクリプト生成する。アプリは 8 地点（九州・沖縄）の既定座標を `config.py` に内蔵し、このファイルがあれば上書き・追加する。

## 5. モジュール構成とデータフロー

```
app.py                      # 入口。ページ設定→サイドバー→データ取得→タブ描画を呼ぶだけ（ロジック無し）
typhoon_app/
  config.py                 # 定数: 地点 8 つ＋既定座標、要素定義（列名/表示名/単位/色）、WINDOW_DAYS=1、パス
  data/
    schema.py               # カラム定義と検証 validate_weather(df) / validate_typhoon(df)
    typhoon.py              # track.csv 読込、台風一覧、台風期間と取得窓の算出
    weather.py              # get_weather(typhoon_id, stations): キャッシュ読込 → 無ければ source → 保存
    source.py               # データ側 fetch_weather のアダプタ（import 失敗時はキャッシュ専用モード）
    station.py              # station.csv 読込（無ければ config の既定座標）
  analysis/
    summary.py              # 地点別サマリ（最低気圧・最大風速・総降水量・各時刻・欠測率）
    timeseries.py           # 期間での絞り込み、要素ごとの整形（long→wide）
  charts/
    timeseries.py           # 要素別ライン/棒グラフ → plotly Figure
    map.py                  # 地点マーカー＋台風経路（線＋位置マーカー）＋時刻スライダー → plotly Figure
    ranking.py              # ランキング棒グラフ → plotly Figure
  ui/
    state.py                # Selection dataclass（typhoon_id, stations, variables）、データ状態 enum
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
  → data.typhoon.get_event(typhoon_id)            # 台風期間・取得窓（±1 日固定）・経路（線＋位置マーカー）
  → data.weather.get_weather(typhoon_id, stations)  # 地点ごと: cache hit → 読む / miss → fetch → 保存
  → analysis.timeseries.clip(df, *event.display_window())  # 表示窓は ±1 日固定
  → analysis.summary.summarize(df)                # 概要タブ用
  → charts.*(…) → ui.tab_*.render(...)
```

- 読込系（台風・地点マスタ・台風×地点の気象）は `st.cache_data` でメモリキャッシュ。永続化はファイルキャッシュが担う。
- `get_weather` の戻り値は `{station: DataFrame | エラー情報}` とし、地点単位の成否を UI に渡す。

## 6. 集計・分析の定義

| 指標 | 定義 |
|---|---|
| 台風期間（台風単位） | `track` の該当台風の最初〜最後の時刻。時系列グラフでは期間全体を薄い帯で表示。取得窓 = [最初の時刻 −1 日, 最後の時刻 +1 日]。表示窓も同じ（固定） |
| 最低気圧・その時刻 | 表示窓内の `pressure` の最小値と発生時刻。地点の「最接近時刻」の代理指標 |
| 最大風速・その時刻 | `wind_speed` の最大値と発生時刻 |
| 総降水量 | `precipitation` の合計（NaN 除外） |
| 最大 1 時間降水量・時刻 | `precipitation` の最大値と時刻 |
| 最高/最低気温 | 気温が選択されているときのみ |
| 欠測率 | 表示窓内の欠測セル数 ÷ 全セル数（%）。サマリ表に併記 |
| ランキング | 上記指標で地点を並べた棒グラフ（最低気圧は昇順、他は降順） |
| 地図の色 | スライダーで選んだ時刻の、選択要素の値。該当時刻が欠測なら灰色 |

欠測の扱い: 集計は NaN を無視。時系列グラフは欠測部分で線を切る（補間しない）。降水の 0 は 0 として描く。

## 7. エラーハンドリングと状態表示

| 状況 | 挙動 |
|---|---|
| キャッシュ CSV あり | 即表示。サイドバーに「● キャッシュ済み」 |
| キャッシュなし・`fetch_weather` 利用可 | `st.spinner("気象庁から取得中…")` で地点ごとに取得→保存→表示。地点単位で進捗表示 |
| キャッシュなし・`fetch_weather` が import 不可（未実装） | 「この台風のデータは未取得です（キャッシュ専用モード）」と `st.warning`。取得済みの地点だけ表示 |
| 取得失敗（`WeatherFetchError` / ネットワーク） | 失敗した地点だけ `st.error` で地点名と理由を表示。他の地点は表示を続ける。再試行ボタンあり |
| スキーマ検証エラー | 期待と異なるカラム/型を列挙して停止（データ担当への報告に使える） |
| `track.csv` が無い | 起動時に「台風データがありません」と停止（必須データ） |
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

1. `fetch_weather(station, start, end)` を §4-1/§4-2 の仕様（6 列）で実装（モジュール名・場所を教えてもらう）。→ 実装済み（2026-08-24, `preprocess/weather_source.py`。既存 jma_scraper を関数化）。
2. 台風データは現行 `data/typhoon/typhoon_track.csv` の変換（`scripts/dev_sample_data.py`）で正式に賄う（対応済み）。より細かい時別データが手に入れば、同じ 6 列で `track.csv` を差し替えるだけでよい。
3. 可能なら `data/processed/station.csv`（緯度経度）を用意。
4. データ側依存（beautifulsoup4, openpyxl 等）を `pyproject.toml` に追加。→ 対応済み（requests, beautifulsoup4）。

## 11. 未決事項・拡張候補

- 利用者・利用シーン、評価観点、発表日は未定。分かり次第、最小構成の優先順位に反映。
- 拡張候補（スコープ外）: 地点比較タブ、台風中心からの距離と観測値の関係（`track.csv` と地点座標があれば可能）、過去台風との比較、追加気象項目（海面気圧・湿度・日照など）。

## 更新履歴

- 2026-08-24: データ契約 v2（チーム合意）
