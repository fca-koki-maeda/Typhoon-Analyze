# Typhoon-Analyze Web アプリ 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 選んだ台風について九州・沖縄 8 地点の気圧・風速・降水量・気温の時間変化を、台風の接近時刻と重ねて見せる Streamlit アプリを、テスト付きで動く状態にする。

**Architecture:** `typhoon_app/` パッケージを `data`（ファイル I/O とデータ契約）/ `analysis`（集計・純関数）/ `charts`（Plotly Figure 生成・純関数）/ `ui`（Streamlit 描画）に分け、`app.py` は配線だけ行う。気象データは `data/processed/weather/{typhoon_id}_{station}.csv` のキャッシュを読み、無ければデータ担当の `fetch_weather` をオンデマンドで呼んで保存する。

**Tech Stack:** Python 3.12 / uv / Streamlit ≥1.50 / pandas ≥2.2 / Plotly ≥6 / pytest

**Spec:** `docs/superpowers/specs/2026-08-23-typhoon-app-design.md`

## Global Constraints

- Python 3.12、環境管理は **uv**（`pyproject.toml` + `uv.lock`）。コマンドはすべて `uv run ...` で実行する
- `streamlit>=1.50`（`width="stretch"` を使う。`use_container_width` は使わない）、`plotly>=6`（`go.Scattermap` と `layout.map` を使う。`scatter_mapbox` は使わない）、`pandas>=2.2`
- Streamlit を import してよいのは `typhoon_app/ui/` と `app.py` だけ。`data/`・`analysis/`・`charts/` は純 Python
- データ契約（spec §4）のカラム名は厳守: 気象 `station, datetime, temperature, precipitation, wind_speed, wind_direction, pressure, weather_code` / 台風 `typhoon_id, datetime, lat, lon, pressure, max_wind_kt, storm_diameter_nm, gale_diameter_nm` / 地点 `station, lat, lon, prec_no, block_no`
- キャッシュ CSV は `data/processed/weather/{typhoon_id}_{station}.csv`、UTF-8(BOM 可)、日時は `%Y-%m-%d %H:%M:%S`
- 取得窓は接近基準時刻の前後 **7 日固定**（`MAX_WINDOW_DAYS = 7`）、表示窓の既定は **3 日**
- 地図は OpenStreetMap タイル（トークン不要）。外部 API キーは一切使わない
- UI 文言は日本語。欠測は補間しない（集計は NaN 無視、折れ線は切る、降水 0 は 0）
- 部分的に失敗しても取れている地点は表示する（spec §7）
- コミットメッセージは英語 1 行要約 + 必要なら本文。各 Task の最後にコミットする

---

## ファイル構成（最終形）

```
pyproject.toml / uv.lock / .python-version / requirements.txt(uv export で生成) / .gitignore / README.md
app.py                              # 配線のみ
typhoon_app/
  __init__.py
  config.py                         # 定数・地点既定座標・要素定義・天気コード表
  data/__init__.py
  data/schema.py                    # SchemaError, validate_weather, validate_typhoon
  data/station.py                   # load_stations, haversine_km, nearest_station
  data/typhoon.py                   # TyphoonEvent, load_landfall, load_track, list_typhoons, get_event
  data/source.py                    # get_fetcher（データ側 fetch_weather のアダプタ）
  data/weather.py                   # StationResult, cache_path, read/write_cache, get_station_weather, get_weather, combine
  analysis/__init__.py
  analysis/timeseries.py            # clip, time_steps, values_at
  analysis/track.py                 # position_at, typhoon_position
  analysis/summary.py               # summarize
  charts/__init__.py
  charts/common.py                  # empty_figure
  charts/timeseries.py              # variable_chart
  charts/ranking.py                 # ranking_chart
  charts/map.py                     # station_map
  ui/__init__.py
  ui/state.py                       # Selection
  ui/loaders.py                     # st.cache_data 付きローダ
  ui/sidebar.py                     # render_sidebar, render_data_status
  ui/header.py                      # render_header
  ui/glossary.py                    # render_glossary
  ui/tab_overview.py                # render_overview
  ui/tab_timeseries.py              # render_timeseries
  ui/tab_map.py                     # render_map
scripts/build_cache.py              # 対象台風×8地点のキャッシュを事前生成
scripts/dev_sample_data.py          # 【暫定】手元の生データから data/processed/ を作る開発用
tests/conftest.py, tests/fixtures/{weather_small,landfall_small,track_small}.csv
tests/test_schema.py test_station.py test_typhoon.py test_weather.py test_timeseries.py test_summary.py test_charts.py test_app_smoke.py
```

---

### Task 1: 環境セットアップ（uv・パッケージ骨組み・テストフィクスチャ）

**Files:**
- Create: `pyproject.toml`, `.python-version`, `.gitignore`（追記）, `typhoon_app/__init__.py`, `typhoon_app/{data,analysis,charts,ui}/__init__.py`, `tests/__init__.py`, `tests/conftest.py`, `tests/fixtures/weather_small.csv`, `tests/fixtures/landfall_small.csv`, `tests/fixtures/track_small.csv`, `tests/test_smoke_env.py`
- Modify: `requirements.txt`（UTF-16 の現行ファイルを uv export で置き換え）

**Interfaces:**
- Produces: pytest フィクスチャ `fixtures_dir: Path`, `weather_raw: DataFrame`（CSV をそのまま読んだもの）, `weather_df: DataFrame`（検証済み。Task 3 で定義する `validate_weather` を使うため Task 3 完了後に有効）, `landfall_df`, `track_df`（Task 5 の `load_landfall`/`load_track` を使う）

- [ ] **Step 1: uv をインストールする（未導入なら）**

Run: `curl -LsSf https://astral.sh/uv/install.sh | sh && exec $SHELL -l && uv --version`
Expected: `uv 0.x.x` が表示される（pip で入れる場合は `pip install --user uv`）

- [ ] **Step 2: pyproject.toml と .python-version を書く**

`pyproject.toml`:
```toml
[project]
name = "typhoon-analyze"
version = "0.1.0"
description = "台風接近時の九州・沖縄 8 地点の気象変化を可視化する Streamlit アプリ"
requires-python = ">=3.12"
dependencies = [
    "streamlit>=1.50",
    "pandas>=2.2",
    "plotly>=6.0",
    "pyarrow>=15",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "openpyxl>=3.1",   # scripts/dev_sample_data.py（暫定）が xlsx を読むためだけに使う
]

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

`.python-version`:
```
3.12
```

- [ ] **Step 3: .gitignore に Python 向けの無視設定を追記する**

`.gitignore` を以下の内容にする（既存の CLAUDE.md 行は残す）:
```
# ローカル専用（Claude Code 向けコンテキスト）
CLAUDE.md

# Python / uv
.venv/
__pycache__/
*.pyc
.pytest_cache/
.streamlit/secrets.toml
```

- [ ] **Step 4: 依存を解決して仮想環境を作る**

Run: `uv sync`
Expected: `.venv/` と `uv.lock` が作られ、エラーなく終了する

- [ ] **Step 5: パッケージの空ファイルを作る**

Run:
```bash
mkdir -p typhoon_app/data typhoon_app/analysis typhoon_app/charts typhoon_app/ui tests/fixtures scripts
touch typhoon_app/__init__.py typhoon_app/data/__init__.py typhoon_app/analysis/__init__.py typhoon_app/charts/__init__.py typhoon_app/ui/__init__.py tests/__init__.py
```

- [ ] **Step 6: テスト用フィクスチャ CSV を置く**

`tests/fixtures/weather_small.csv`（2 地点 × 6 時刻。福岡は気温欠測 1、鹿児島は降水・風速・風向欠測 1。日付境界 00:00 を含む）:
```csv
station,datetime,temperature,precipitation,wind_speed,wind_direction,pressure,weather_code
福岡,2025-08-21 21:00:00,28.0,0.0,3.0,東,1000.0,2
福岡,2025-08-21 22:00:00,27.5,0.5,4.0,東南東,998.0,10
福岡,2025-08-21 23:00:00,27.0,2.0,6.0,南東,995.0,10
福岡,2025-08-22 00:00:00,26.5,1.0,5.0,南,996.0,10
福岡,2025-08-22 01:00:00,26.0,0.0,3.0,南西,998.5,4
福岡,2025-08-22 02:00:00,,0.0,2.0,西,1000.5,2
鹿児島,2025-08-21 21:00:00,29.0,5.0,12.0,北東,990.0,10
鹿児島,2025-08-21 22:00:00,28.5,10.0,15.0,東,985.0,10
鹿児島,2025-08-21 23:00:00,28.0,20.5,18.0,東南東,980.0,10
鹿児島,2025-08-22 00:00:00,27.5,8.0,20.0,南東,982.0,10
鹿児島,2025-08-22 01:00:00,27.0,1.0,10.0,南,988.0,10
鹿児島,2025-08-22 02:00:00,27.0,,,,992.0,4
```

`tests/fixtures/landfall_small.csv`:
```csv
typhoon_id,datetime,lat,lon,pressure,max_wind_kt,storm_diameter_nm,gale_diameter_nm
202512,2025-08-21 17:00:00,31.6,130.3,994,45,,160
202515,2025-09-05 01:00:00,33.0,132.4,1000,35,,360
202515,2025-09-05 16:00:00,35.0,139.7,992,45,,420
```

`tests/fixtures/track_small.csv`:
```csv
typhoon_id,datetime,lat,lon,pressure,max_wind_kt,storm_diameter_nm,gale_diameter_nm
202512,2025-08-21 09:00:00,30.0,129.5,996,40,,160
202512,2025-08-21 15:00:00,31.2,130.1,994,45,,160
202512,2025-08-21 21:00:00,32.4,130.9,996,40,,160
202512,2025-08-22 03:00:00,33.6,131.7,1000,35,,160
```

- [ ] **Step 7: conftest.py を書く**

`tests/conftest.py`（`weather_df` / `landfall_df` / `track_df` は Task 3・5 の関数に依存する。Task 1 時点では import エラーにならないよう関数内 import にしてある）:
```python
from pathlib import Path

import pandas as pd
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def weather_raw() -> pd.DataFrame:
    """CSV をそのまま読んだ、検証前の気象データ。"""
    return pd.read_csv(FIXTURES / "weather_small.csv", encoding="utf-8-sig")


@pytest.fixture
def weather_df(weather_raw) -> pd.DataFrame:
    """検証済み（型変換済み）の気象データ。"""
    from typhoon_app.data.schema import validate_weather

    return validate_weather(weather_raw)


@pytest.fixture
def landfall_df() -> pd.DataFrame:
    from typhoon_app.data.typhoon import load_landfall

    return load_landfall(FIXTURES / "landfall_small.csv")


@pytest.fixture
def track_df() -> pd.DataFrame:
    from typhoon_app.data.typhoon import load_track

    return load_track(FIXTURES / "track_small.csv")
```

- [ ] **Step 8: 環境が動くことを確かめる最小テストを書く**

`tests/test_smoke_env.py`:
```python
def test_imports():
    import pandas, plotly, streamlit  # noqa: F401

    import typhoon_app  # noqa: F401
```

- [ ] **Step 9: テストを実行する**

Run: `uv run pytest -q`
Expected: `1 passed`

- [ ] **Step 10: requirements.txt を UTF-8 で再生成する（Community Cloud 用）**

Run: `uv export --format requirements-txt --no-dev --no-hashes -o requirements.txt && file requirements.txt && head -3 requirements.txt`
Expected: `requirements.txt: ASCII text` または `UTF-8`、先頭に `# This file was autogenerated by uv` と依存の行

- [ ] **Step 11: コミット**

```bash
git add pyproject.toml uv.lock .python-version .gitignore requirements.txt typhoon_app tests
git commit -m "Set up uv project skeleton, test fixtures, and regenerate requirements.txt"
```

---

### Task 2: config.py（定数・地点・要素定義）

**Files:**
- Create: `typhoon_app/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `PROJECT_ROOT, PROCESSED_DIR, WEATHER_CACHE_DIR, LANDFALL_CSV, TRACK_CSV, STATION_CSV: Path`
  - `MAX_WINDOW_DAYS: int = 7`, `DEFAULT_WINDOW_DAYS: int = 3`
  - `FETCHER_MODULE = "preprocess.weather_source"`, `FETCHER_FUNCTION = "fetch_weather"`
  - `@dataclass(frozen=True) Station(name: str, lat: float, lon: float, prec_no: int, block_no: int)`
  - `DEFAULT_STATIONS: tuple[Station, ...]`（8 地点）, `STATION_NAMES: list[str]`
  - `@dataclass(frozen=True) Variable(key: str, label: str, unit: str, kind: Literal["line","bar"], agg: Literal["min","max","sum"])`
  - `VARIABLES: dict[str, Variable]`（キー: pressure, wind_speed, precipitation, temperature）, `DEFAULT_VARIABLES: tuple[str, ...]`
  - `WEATHER_CODE_NAMES: dict[int, str]`, `MAP_CENTER: tuple[float, float]`, `MAP_ZOOM: int`

- [ ] **Step 1: テストを書く**

`tests/test_config.py`:
```python
from typhoon_app import config


def test_default_stations_are_eight_kyushu_okinawa_points():
    names = [s.name for s in config.DEFAULT_STATIONS]
    assert names == ["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "那覇"]
    assert config.STATION_NAMES == names
    for s in config.DEFAULT_STATIONS:
        assert 24 < s.lat < 35 and 126 < s.lon < 133


def test_variables_and_windows():
    assert set(config.VARIABLES) == {"pressure", "wind_speed", "precipitation", "temperature"}
    assert config.VARIABLES["precipitation"].kind == "bar"
    assert config.VARIABLES["pressure"].agg == "min"
    assert config.MAX_WINDOW_DAYS == 7
    assert 1 <= config.DEFAULT_WINDOW_DAYS <= config.MAX_WINDOW_DAYS
    assert config.WEATHER_CODE_NAMES[2] == "晴"
```

- [ ] **Step 2: 失敗を確認する**

Run: `uv run pytest tests/test_config.py -q`
Expected: FAIL（`ModuleNotFoundError: typhoon_app.config`）

- [ ] **Step 3: config.py を書く**

`typhoon_app/config.py`:
```python
"""アプリ全体の定数。設計書 §2・§4・§6 の値をここに集約する。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
WEATHER_CACHE_DIR = PROCESSED_DIR / "weather"
LANDFALL_CSV = PROCESSED_DIR / "typhoon" / "landfall.csv"
TRACK_CSV = PROCESSED_DIR / "typhoon" / "track.csv"
STATION_CSV = PROCESSED_DIR / "station.csv"

MAX_WINDOW_DAYS = 7       # 取得窓: 接近基準時刻の前後 7 日（固定）
DEFAULT_WINDOW_DAYS = 3   # 表示窓の既定

# データ側が実装する取得関数の場所（設計書 §4-1）
FETCHER_MODULE = "preprocess.weather_source"
FETCHER_FUNCTION = "fetch_weather"


@dataclass(frozen=True)
class Station:
    name: str
    lat: float
    lon: float
    prec_no: int
    block_no: int


# 気象庁の観測所座標（おおよそ）。data/processed/station.csv があればそちらで上書きする
DEFAULT_STATIONS: tuple[Station, ...] = (
    Station("福岡", 33.582, 130.375, 82, 47807),
    Station("佐賀", 33.265, 130.305, 85, 47813),
    Station("長崎", 32.733, 129.867, 84, 47817),
    Station("熊本", 32.813, 130.707, 86, 47819),
    Station("大分", 33.235, 131.618, 83, 47624),
    Station("宮崎", 31.938, 131.413, 87, 47830),
    Station("鹿児島", 31.555, 130.547, 88, 47827),
    Station("那覇", 26.207, 127.687, 91, 47936),
)
STATION_NAMES: list[str] = [s.name for s in DEFAULT_STATIONS]


@dataclass(frozen=True)
class Variable:
    key: str                          # 気象データのカラム名
    label: str                        # 表示名
    unit: str
    kind: Literal["line", "bar"]      # 時系列グラフの種類
    agg: Literal["min", "max", "sum"] # ランキングで使う代表値


VARIABLES: dict[str, Variable] = {
    "pressure": Variable("pressure", "気圧", "hPa", "line", "min"),
    "wind_speed": Variable("wind_speed", "風速", "m/s", "line", "max"),
    "precipitation": Variable("precipitation", "降水量", "mm", "bar", "sum"),
    "temperature": Variable("temperature", "気温", "℃", "line", "max"),
}
DEFAULT_VARIABLES: tuple[str, ...] = ("pressure", "wind_speed", "precipitation")

# 気象庁 時別値の天気コード → 名称（表示用）
WEATHER_CODE_NAMES: dict[int, str] = {
    1: "快晴", 2: "晴", 3: "薄曇", 4: "曇", 5: "煙霧", 6: "砂じん嵐", 7: "地ふぶき",
    8: "霧", 9: "霧雨", 10: "雨", 11: "みぞれ", 12: "雪", 13: "あられ", 14: "ひょう",
    15: "雷", 16: "しゅう雨または止み間のある雨", 17: "着氷性の雨", 18: "着氷性の霧雨",
    19: "しゅう雪または止み間のある雪", 22: "霧雪", 23: "凍雨", 24: "細氷", 28: "もや",
    101: "降水またはしゅう雨性の降水",
}

MAP_CENTER: tuple[float, float] = (31.0, 130.5)
MAP_ZOOM: int = 5
```

- [ ] **Step 4: テストを通す**

Run: `uv run pytest tests/test_config.py -q`
Expected: `2 passed`

- [ ] **Step 5: コミット**

```bash
git add typhoon_app/config.py tests/test_config.py
git commit -m "Add app config: paths, stations, variables, weather codes"
```

---

### Task 3: data/schema.py（データ契約の検証）

**Files:**
- Create: `typhoon_app/data/schema.py`
- Test: `tests/test_schema.py`

**Interfaces:**
- Produces:
  - `class SchemaError(ValueError)`
  - `WEATHER_COLUMNS: dict[str, str]`, `TYPHOON_COLUMNS: dict[str, str]`（カラム名 → "string"|"datetime"|"float"|"int"）
  - `validate_weather(df: pd.DataFrame) -> pd.DataFrame`（型変換済み・station, datetime 昇順）
  - `validate_typhoon(df: pd.DataFrame) -> pd.DataFrame`（型変換済み・typhoon_id, datetime 昇順）
  - どちらも欠けたカラム／解釈できない値があれば `SchemaError`（メッセージにカラム名を含む）

- [ ] **Step 1: テストを書く**

`tests/test_schema.py`:
```python
import pandas as pd
import pytest

from typhoon_app.data.schema import (
    TYPHOON_COLUMNS,
    WEATHER_COLUMNS,
    SchemaError,
    validate_typhoon,
    validate_weather,
)


def test_validate_weather_coerces_types(weather_raw):
    df = validate_weather(weather_raw)
    assert list(WEATHER_COLUMNS) == [c for c in df.columns if c in WEATHER_COLUMNS]
    assert str(df["datetime"].dtype).startswith("datetime64")
    assert df["pressure"].dtype == "float64"
    assert str(df["weather_code"].dtype) == "Int64"
    assert df["precipitation"].isna().sum() == 1          # 鹿児島 02:00 の欠測
    assert df["datetime"].iloc[0] == pd.Timestamp("2025-08-21 21:00:00")


def test_validate_weather_missing_column_names_it(weather_raw):
    with pytest.raises(SchemaError, match="pressure"):
        validate_weather(weather_raw.drop(columns=["pressure"]))


def test_validate_weather_rejects_unparseable_value(weather_raw):
    bad = weather_raw.astype({"precipitation": "string"})
    bad.loc[0, "precipitation"] = "--"   # データ側で 0.0 に変換されているべき値
    with pytest.raises(SchemaError, match="precipitation"):
        validate_weather(bad)


def test_validate_weather_sorts_by_station_and_time(weather_raw):
    shuffled = weather_raw.sample(frac=1, random_state=0)
    df = validate_weather(shuffled)
    assert df["station"].tolist()[:6] == ["福岡"] * 6
    assert df["datetime"].iloc[:6].is_monotonic_increasing


def test_validate_typhoon(fixtures_dir):
    raw = pd.read_csv(fixtures_dir / "landfall_small.csv", dtype={"typhoon_id": str})
    df = validate_typhoon(raw)
    assert list(TYPHOON_COLUMNS) == [c for c in df.columns if c in TYPHOON_COLUMNS]
    assert df["storm_diameter_nm"].isna().all()
    assert df["typhoon_id"].tolist() == ["202512", "202515", "202515"]
    with pytest.raises(SchemaError, match="lat"):
        validate_typhoon(raw.drop(columns=["lat"]))
```

- [ ] **Step 2: 失敗を確認する**

Run: `uv run pytest tests/test_schema.py -q`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: schema.py を書く**

`typhoon_app/data/schema.py`:
```python
"""データ契約（設計書 §4-2 / §4-4）の検証と型変換。"""
from __future__ import annotations

import pandas as pd


class SchemaError(ValueError):
    """データ契約に合わないときに送出する。メッセージにカラム名を含める。"""


WEATHER_COLUMNS: dict[str, str] = {
    "station": "string",
    "datetime": "datetime",
    "temperature": "float",
    "precipitation": "float",
    "wind_speed": "float",
    "wind_direction": "string",
    "pressure": "float",
    "weather_code": "int",
}

TYPHOON_COLUMNS: dict[str, str] = {
    "typhoon_id": "string",
    "datetime": "datetime",
    "lat": "float",
    "lon": "float",
    "pressure": "float",
    "max_wind_kt": "float",
    "storm_diameter_nm": "float",
    "gale_diameter_nm": "float",
}


def _coerce(df: pd.DataFrame, spec: dict[str, str], name: str) -> pd.DataFrame:
    missing = [c for c in spec if c not in df.columns]
    if missing:
        raise SchemaError(f"{name}: 欠けているカラム: {missing}")

    out = df.copy()
    problems: list[str] = []
    for col, kind in spec.items():
        src = out[col]
        if kind == "string":
            out[col] = src.astype("string")
            continue
        if kind == "datetime":
            coerced = pd.to_datetime(src, errors="coerce")
        else:
            coerced = pd.to_numeric(src, errors="coerce")
            if kind == "int":
                try:
                    coerced = coerced.astype("Int64")
                except (TypeError, ValueError):
                    problems.append(f"{col}: 整数でない値があります")
        # 元は値があるのに変換後 NaN になったセル = 解釈できない値
        nonblank = src.notna() & (src.astype("string").str.strip() != "")
        bad = coerced.isna() & nonblank.fillna(False)
        if bad.any():
            problems.append(f"{col}={src[bad].iloc[0]!r}")
        out[col] = coerced

    if problems:
        raise SchemaError(f"{name}: 解釈できない値があります: " + ", ".join(problems))
    return out


def validate_weather(df: pd.DataFrame) -> pd.DataFrame:
    """気象データ（tidy）を検証し、型変換して station, datetime 昇順で返す。"""
    out = _coerce(df, WEATHER_COLUMNS, "weather")
    return out.sort_values(["station", "datetime"]).reset_index(drop=True)


def validate_typhoon(df: pd.DataFrame) -> pd.DataFrame:
    """台風データ（landfall / track 共通）を検証し、typhoon_id, datetime 昇順で返す。"""
    out = _coerce(df, TYPHOON_COLUMNS, "typhoon")
    return out.sort_values(["typhoon_id", "datetime"]).reset_index(drop=True)
```

- [ ] **Step 4: テストを通す**

Run: `uv run pytest tests/test_schema.py -q`
Expected: `5 passed`

- [ ] **Step 5: コミット**

```bash
git add typhoon_app/data/schema.py tests/test_schema.py
git commit -m "Add schema validation for weather and typhoon data contracts"
```

---

### Task 4: data/station.py（地点マスタと距離）

**Files:**
- Create: `typhoon_app/data/station.py`
- Test: `tests/test_station.py`

**Interfaces:**
- Consumes: `config.Station`, `config.DEFAULT_STATIONS`, `config.STATION_CSV`, `schema.SchemaError`
- Produces:
  - `load_stations(path: Path = STATION_CSV) -> dict[str, Station]`（既定 8 地点。CSV があれば同名を上書き／追加）
  - `haversine_km(lat1, lon1, lat2, lon2) -> float`
  - `nearest_station(lat: float, lon: float, stations: dict[str, Station]) -> Station`

- [ ] **Step 1: テストを書く**

`tests/test_station.py`:
```python
from pathlib import Path

import pytest

from typhoon_app.data.schema import SchemaError
from typhoon_app.data.station import haversine_km, load_stations, nearest_station


def test_load_stations_defaults_when_file_missing(tmp_path):
    stations = load_stations(tmp_path / "station.csv")
    assert len(stations) == 8
    assert stations["福岡"].block_no == 47807


def test_load_stations_overrides_from_csv(tmp_path):
    p = tmp_path / "station.csv"
    p.write_text("station,lat,lon,prec_no,block_no\n福岡,33.6,130.4,82,47807\n", encoding="utf-8")
    stations = load_stations(p)
    assert stations["福岡"].lat == 33.6
    assert len(stations) == 8   # 他の地点は既定のまま


def test_load_stations_rejects_bad_columns(tmp_path):
    p = tmp_path / "station.csv"
    p.write_text("name,lat,lon\n福岡,33.6,130.4\n", encoding="utf-8")
    with pytest.raises(SchemaError, match="station"):
        load_stations(p)


def test_haversine_fukuoka_kagoshima():
    d = haversine_km(33.582, 130.375, 31.555, 130.547)
    assert 200 < d < 250


def test_nearest_station():
    stations = load_stations(Path("/nonexistent/station.csv"))
    assert nearest_station(31.6, 130.3, stations).name == "鹿児島"
    assert nearest_station(26.6, 128.0, stations).name == "那覇"
```

- [ ] **Step 2: 失敗を確認する**

Run: `uv run pytest tests/test_station.py -q`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: station.py を書く**

`typhoon_app/data/station.py`:
```python
"""地点マスタ（設計書 §4-5）。CSV が無ければ config の既定座標を使う。"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from typhoon_app.config import DEFAULT_STATIONS, STATION_CSV, Station
from typhoon_app.data.schema import SchemaError

_REQUIRED = ["station", "lat", "lon", "prec_no", "block_no"]


def load_stations(path: Path = STATION_CSV) -> dict[str, Station]:
    """既定 8 地点に、station.csv があればその内容を上書き・追加して返す。"""
    stations: dict[str, Station] = {s.name: s for s in DEFAULT_STATIONS}
    path = Path(path)
    if not path.exists():
        return stations
    df = pd.read_csv(path, encoding="utf-8-sig")
    missing = [c for c in _REQUIRED if c not in df.columns]
    if missing:
        raise SchemaError(f"station.csv: 欠けているカラム: {missing}")
    for row in df.itertuples(index=False):
        name = str(row.station)
        stations[name] = Station(name, float(row.lat), float(row.lon), int(row.prec_no), int(row.block_no))
    return stations


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """2 点間の大円距離（km）。"""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_station(lat: float, lon: float, stations: dict[str, Station]) -> Station:
    """(lat, lon) に最も近い地点を返す。ヘッダの「◯◯付近」表示に使う。"""
    return min(stations.values(), key=lambda s: haversine_km(lat, lon, s.lat, s.lon))
```

- [ ] **Step 4: テストを通す**

Run: `uv run pytest tests/test_station.py -q`
Expected: `5 passed`

- [ ] **Step 5: コミット**

```bash
git add typhoon_app/data/station.py tests/test_station.py
git commit -m "Add station master loader with defaults and nearest-station lookup"
```

---

### Task 5: data/typhoon.py（台風データと TyphoonEvent）

**Files:**
- Create: `typhoon_app/data/typhoon.py`
- Test: `tests/test_typhoon.py`

**Interfaces:**
- Consumes: `config.LANDFALL_CSV, TRACK_CSV, MAX_WINDOW_DAYS`, `schema.validate_typhoon`
- Produces:
  - `@dataclass(frozen=True) TyphoonEvent(typhoon_id: str, landfalls: pd.DataFrame, track: pd.DataFrame | None = None)`
    - `.year: int`, `.number: int`, `.label: str`（例 `"2025年 第12号（8/21 接近）"`）
    - `.reference_times: list[pd.Timestamp]`, `.first_time`, `.last_time: pd.Timestamp`
    - `.center_pressure: float`（landfalls の最小）, `.max_wind_kt: float`（最大）, `.landfall_lat`, `.landfall_lon: float`（最初の行）
    - `.fetch_window(days: int = MAX_WINDOW_DAYS) -> tuple[date, date]`
    - `.display_window(days: int) -> tuple[pd.Timestamp, pd.Timestamp]`
  - `load_landfall(path: Path = LANDFALL_CSV) -> pd.DataFrame`（無ければ `FileNotFoundError`）
  - `load_track(path: Path = TRACK_CSV) -> pd.DataFrame | None`（無ければ `None`）
  - `list_typhoons(landfall: pd.DataFrame, track: pd.DataFrame | None = None) -> list[TyphoonEvent]`（first_time 降順）
  - `get_event(typhoon_id: str, landfall, track=None) -> TyphoonEvent`（無ければ `KeyError`）

- [ ] **Step 1: テストを書く**

`tests/test_typhoon.py`:
```python
from datetime import date

import pandas as pd
import pytest

from typhoon_app.data.typhoon import get_event, list_typhoons, load_landfall, load_track


def test_load_landfall_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_landfall(tmp_path / "landfall.csv")


def test_load_track_missing_file_is_none(tmp_path):
    assert load_track(tmp_path / "track.csv") is None


def test_list_typhoons_sorted_newest_first(landfall_df):
    events = list_typhoons(landfall_df)
    assert [e.typhoon_id for e in events] == ["202515", "202512"]


def test_event_properties_and_windows(landfall_df):
    e = get_event("202515", landfall_df)
    assert (e.year, e.number) == (2025, 15)
    assert e.label == "2025年 第15号（9/5 接近）"
    assert e.reference_times == [pd.Timestamp("2025-09-05 01:00"), pd.Timestamp("2025-09-05 16:00")]
    assert e.fetch_window() == (date(2025, 8, 29), date(2025, 9, 12))
    assert e.display_window(3) == (pd.Timestamp("2025-09-02 01:00"), pd.Timestamp("2025-09-08 16:00"))
    assert e.center_pressure == 992.0
    assert e.max_wind_kt == 45.0
    assert (e.landfall_lat, e.landfall_lon) == (33.0, 132.4)


def test_get_event_unknown_id(landfall_df):
    with pytest.raises(KeyError):
        get_event("199999", landfall_df)


def test_track_is_attached_per_typhoon(landfall_df, track_df):
    with_track = get_event("202512", landfall_df, track_df)
    assert len(with_track.track) == 4
    without = get_event("202515", landfall_df, track_df)
    assert without.track is None
```

- [ ] **Step 2: 失敗を確認する**

Run: `uv run pytest tests/test_typhoon.py -q`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: typhoon.py を書く**

`typhoon_app/data/typhoon.py`:
```python
"""台風データ（設計書 §4-4）の読込と、台風 1 個ぶんの情報をまとめる TyphoonEvent。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from typhoon_app.config import LANDFALL_CSV, MAX_WINDOW_DAYS, TRACK_CSV
from typhoon_app.data.schema import validate_typhoon


@dataclass(frozen=True)
class TyphoonEvent:
    typhoon_id: str
    landfalls: pd.DataFrame               # この台風の上陸/接近点（datetime 昇順）
    track: pd.DataFrame | None = None     # 全経路（無ければ None）

    @property
    def year(self) -> int:
        return int(self.typhoon_id[:4])

    @property
    def number(self) -> int:
        return int(self.typhoon_id[4:])

    @property
    def reference_times(self) -> list[pd.Timestamp]:
        return [pd.Timestamp(t) for t in self.landfalls["datetime"]]

    @property
    def first_time(self) -> pd.Timestamp:
        return self.reference_times[0]

    @property
    def last_time(self) -> pd.Timestamp:
        return self.reference_times[-1]

    @property
    def label(self) -> str:
        t = self.first_time
        return f"{self.year}年 第{self.number}号（{t.month}/{t.day} 接近）"

    @property
    def center_pressure(self) -> float:
        return float(self.landfalls["pressure"].min())

    @property
    def max_wind_kt(self) -> float:
        return float(self.landfalls["max_wind_kt"].max())

    @property
    def landfall_lat(self) -> float:
        return float(self.landfalls["lat"].iloc[0])

    @property
    def landfall_lon(self) -> float:
        return float(self.landfalls["lon"].iloc[0])

    def fetch_window(self, days: int = MAX_WINDOW_DAYS) -> tuple[date, date]:
        """データ取得に使う日付範囲（両端含む）。"""
        return (
            (self.first_time - pd.Timedelta(days=days)).date(),
            (self.last_time + pd.Timedelta(days=days)).date(),
        )

    def display_window(self, days: int) -> tuple[pd.Timestamp, pd.Timestamp]:
        """画面に表示する時刻範囲。"""
        return (
            self.first_time - pd.Timedelta(days=days),
            self.last_time + pd.Timedelta(days=days),
        )


def _read(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig", dtype={"typhoon_id": str})
    return validate_typhoon(df)


def load_landfall(path: Path = LANDFALL_CSV) -> pd.DataFrame:
    """上陸/接近スナップショット。必須データなので無ければ FileNotFoundError。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"台風データがありません: {path}")
    return _read(path)


def load_track(path: Path = TRACK_CSV) -> pd.DataFrame | None:
    """全経路。任意データなので無ければ None。"""
    path = Path(path)
    if not path.exists():
        return None
    return _read(path)


def get_event(typhoon_id: str, landfall: pd.DataFrame, track: pd.DataFrame | None = None) -> TyphoonEvent:
    rows = landfall[landfall["typhoon_id"] == typhoon_id]
    if rows.empty:
        raise KeyError(f"台風 {typhoon_id} は landfall データにありません")
    trk = None
    if track is not None:
        trk = track[track["typhoon_id"] == typhoon_id].sort_values("datetime").reset_index(drop=True)
        if trk.empty:
            trk = None
    return TyphoonEvent(typhoon_id, rows.sort_values("datetime").reset_index(drop=True), trk)


def list_typhoons(landfall: pd.DataFrame, track: pd.DataFrame | None = None) -> list[TyphoonEvent]:
    """landfall にある台風をすべて TyphoonEvent にして、新しい順に返す。"""
    events = [get_event(str(tid), landfall, track) for tid in landfall["typhoon_id"].unique()]
    return sorted(events, key=lambda e: e.first_time, reverse=True)
```

- [ ] **Step 4: テストを通す**

Run: `uv run pytest tests/test_typhoon.py -q`
Expected: `6 passed`

- [ ] **Step 5: コミット**

```bash
git add typhoon_app/data/typhoon.py tests/test_typhoon.py
git commit -m "Add typhoon data loaders and TyphoonEvent with fetch/display windows"
```

---

### Task 6: data/source.py + data/weather.py（取得関数アダプタとハイブリッド取得）

**Files:**
- Create: `typhoon_app/data/source.py`, `typhoon_app/data/weather.py`
- Test: `tests/test_weather.py`

**Interfaces:**
- Consumes: `config.WEATHER_CACHE_DIR, FETCHER_MODULE, FETCHER_FUNCTION`, `schema.validate_weather, SchemaError, WEATHER_COLUMNS`
- Produces:
  - `source.WeatherFetcher = Callable[[str, date, date], pd.DataFrame]`
  - `source.get_fetcher(module_name=FETCHER_MODULE, function_name=FETCHER_FUNCTION) -> WeatherFetcher | None`
  - `weather.StationResult(station: str, status: Literal["cached","fetched","unavailable","error"], df: pd.DataFrame | None = None, message: str = "")` with `.ok: bool`
  - `weather.cache_path(typhoon_id, station, cache_dir=WEATHER_CACHE_DIR) -> Path`
  - `weather.read_cache(path) -> pd.DataFrame | None`, `weather.write_cache(df, path) -> None`
  - `weather.get_station_weather(typhoon_id, station, fetch_window: tuple[date, date], fetcher=None, cache_dir=WEATHER_CACHE_DIR) -> StationResult`（例外を投げない）
  - `weather.get_weather(typhoon_id, stations: Iterable[str], fetch_window, fetcher=None, cache_dir=...) -> dict[str, StationResult]`
  - `weather.combine(results: dict[str, StationResult]) -> pd.DataFrame`（成功分を結合。無ければ契約カラムだけの空 DataFrame）

- [ ] **Step 1: テストを書く**

`tests/test_weather.py`:
```python
from datetime import date

import pandas as pd

from typhoon_app.data.source import get_fetcher
from typhoon_app.data.weather import (
    cache_path,
    combine,
    get_station_weather,
    get_weather,
    write_cache,
)

WINDOW = (date(2025, 8, 14), date(2025, 8, 28))


def make_fetcher(df: pd.DataFrame, calls: list):
    def fetch(station, start, end):
        calls.append((station, start, end))
        return df[df["station"] == station]

    return fetch


def test_cache_hit_does_not_call_fetcher(tmp_path, weather_df):
    write_cache(weather_df[weather_df["station"] == "福岡"], cache_path("202512", "福岡", tmp_path))
    calls = []
    r = get_station_weather("202512", "福岡", WINDOW, make_fetcher(weather_df, calls), tmp_path)
    assert r.status == "cached" and r.ok
    assert calls == []
    assert len(r.df) == 6


def test_cache_miss_fetches_then_saves(tmp_path, weather_df):
    calls = []
    r = get_station_weather("202512", "鹿児島", WINDOW, make_fetcher(weather_df, calls), tmp_path)
    assert r.status == "fetched"
    assert calls == [("鹿児島", date(2025, 8, 14), date(2025, 8, 28))]
    assert cache_path("202512", "鹿児島", tmp_path).exists()
    again = get_station_weather("202512", "鹿児島", WINDOW, make_fetcher(weather_df, calls), tmp_path)
    assert again.status == "cached" and len(calls) == 1
    assert len(again.df) == 6


def test_no_fetcher_means_unavailable(tmp_path):
    r = get_station_weather("202512", "福岡", WINDOW, None, tmp_path)
    assert r.status == "unavailable" and not r.ok and r.df is None


def test_fetch_error_does_not_stop_other_stations(tmp_path, weather_df):
    def failing(station, start, end):
        if station == "福岡":
            raise RuntimeError("network down")
        return weather_df[weather_df["station"] == station]

    results = get_weather("202512", ["福岡", "鹿児島"], WINDOW, failing, tmp_path)
    assert results["福岡"].status == "error"
    assert "network down" in results["福岡"].message
    assert results["鹿児島"].status == "fetched"
    combined = combine(results)
    assert set(combined["station"]) == {"鹿児島"}


def test_bad_schema_from_fetcher_is_error(tmp_path, weather_df):
    def bad(station, start, end):
        return weather_df.drop(columns=["pressure"])

    r = get_station_weather("202512", "福岡", WINDOW, bad, tmp_path)
    assert r.status == "error" and "pressure" in r.message
    assert not cache_path("202512", "福岡", tmp_path).exists()


def test_combine_empty_has_contract_columns():
    df = combine({})
    assert df.empty and "pressure" in df.columns


def test_get_fetcher_missing_module_is_none():
    assert get_fetcher("no_such_module_xyz", "fetch_weather") is None


def test_get_fetcher_returns_callable():
    assert callable(get_fetcher("math", "sqrt"))
```

- [ ] **Step 2: 失敗を確認する**

Run: `uv run pytest tests/test_weather.py -q`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: source.py を書く**

`typhoon_app/data/source.py`:
```python
"""データ側が実装する取得関数 fetch_weather(station, start, end) へのアダプタ（設計書 §4-1）。"""
from __future__ import annotations

import importlib
from collections.abc import Callable
from datetime import date

import pandas as pd

from typhoon_app.config import FETCHER_FUNCTION, FETCHER_MODULE

WeatherFetcher = Callable[[str, date, date], pd.DataFrame]


def get_fetcher(module_name: str = FETCHER_MODULE, function_name: str = FETCHER_FUNCTION) -> WeatherFetcher | None:
    """取得関数を import して返す。モジュールや関数が無ければ None（キャッシュ専用モード）。"""
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return None
    fn = getattr(module, function_name, None)
    return fn if callable(fn) else None
```

- [ ] **Step 4: weather.py を書く**

`typhoon_app/data/weather.py`:
```python
"""気象データのハイブリッド取得（設計書 §4-3 / §7）。
キャッシュ CSV があれば読む。無ければ fetcher を呼んで保存する。例外は StationResult に畳み込む。"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import pandas as pd

from typhoon_app.config import WEATHER_CACHE_DIR
from typhoon_app.data.schema import WEATHER_COLUMNS, SchemaError, validate_weather
from typhoon_app.data.source import WeatherFetcher

Status = Literal["cached", "fetched", "unavailable", "error"]


@dataclass
class StationResult:
    station: str
    status: Status
    df: pd.DataFrame | None = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status in ("cached", "fetched")


def cache_path(typhoon_id: str, station: str, cache_dir: Path = WEATHER_CACHE_DIR) -> Path:
    return Path(cache_dir) / f"{typhoon_id}_{station}.csv"


def read_cache(path: Path) -> pd.DataFrame | None:
    path = Path(path)
    if not path.exists():
        return None
    return validate_weather(pd.read_csv(path, encoding="utf-8-sig"))


def write_cache(df: pd.DataFrame, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d %H:%M:%S")


def get_station_weather(
    typhoon_id: str,
    station: str,
    fetch_window: tuple[date, date],
    fetcher: WeatherFetcher | None = None,
    cache_dir: Path = WEATHER_CACHE_DIR,
) -> StationResult:
    """1 地点ぶんを取得する。例外は投げず、status/message で返す。"""
    path = cache_path(typhoon_id, station, cache_dir)
    try:
        cached = read_cache(path)
    except SchemaError as e:
        return StationResult(station, "error", message=f"キャッシュの形式が不正です: {e}")
    if cached is not None:
        return StationResult(station, "cached", cached)

    if fetcher is None:
        return StationResult(station, "unavailable", message="キャッシュが無く、取得関数も利用できません")

    start, end = fetch_window
    try:
        df = validate_weather(fetcher(station, start, end))
    except Exception as e:  # noqa: BLE001 — 取得失敗は種類を問わず地点単位で報告して続行する（設計書 §7）
        return StationResult(station, "error", message=f"{type(e).__name__}: {e}")
    write_cache(df, path)
    return StationResult(station, "fetched", df)


def get_weather(
    typhoon_id: str,
    stations: Iterable[str],
    fetch_window: tuple[date, date],
    fetcher: WeatherFetcher | None = None,
    cache_dir: Path = WEATHER_CACHE_DIR,
) -> dict[str, StationResult]:
    return {s: get_station_weather(typhoon_id, s, fetch_window, fetcher, cache_dir) for s in stations}


def combine(results: dict[str, StationResult]) -> pd.DataFrame:
    """成功した地点の DataFrame を 1 つに結合する。無ければ契約カラムだけの空 DataFrame。"""
    frames = [r.df for r in results.values() if r.ok and r.df is not None]
    if not frames:
        return pd.DataFrame(columns=list(WEATHER_COLUMNS))
    return pd.concat(frames, ignore_index=True).sort_values(["station", "datetime"]).reset_index(drop=True)
```

- [ ] **Step 5: テストを通す**

Run: `uv run pytest tests/test_weather.py -q`
Expected: `8 passed`

- [ ] **Step 6: コミット**

```bash
git add typhoon_app/data/source.py typhoon_app/data/weather.py tests/test_weather.py
git commit -m "Add hybrid weather loader: cache first, on-demand fetch fallback"
```

---

### Task 7: analysis/timeseries.py + analysis/track.py（絞り込み・時刻値・台風位置）

**Files:**
- Create: `typhoon_app/analysis/timeseries.py`, `typhoon_app/analysis/track.py`
- Test: `tests/test_timeseries.py`

**Interfaces:**
- Consumes: `data.typhoon.TyphoonEvent`
- Produces:
  - `timeseries.clip(df, start, end) -> pd.DataFrame`（両端含む）
  - `timeseries.time_steps(start, end, freq="1h") -> pd.DatetimeIndex`（start を切り上げ、end を切り捨てた正時）
  - `timeseries.values_at(df, var_key: str, t) -> pd.DataFrame`（列 `station, value`。該当時刻が無ければ空）
  - `track.position_at(track: pd.DataFrame | None, t) -> tuple[float, float] | None`（経路点を時間で線形補間。範囲外/None は None）
  - `track.typhoon_position(event: TyphoonEvent, t) -> tuple[float, float] | None`（経路があれば補間、無ければ 6 時間以内の最寄り上陸点、それも無ければ None）

- [ ] **Step 1: テストを書く**

`tests/test_timeseries.py`:
```python
import pandas as pd
import pytest

from typhoon_app.analysis.timeseries import clip, time_steps, values_at
from typhoon_app.analysis.track import position_at, typhoon_position
from typhoon_app.data.typhoon import get_event


def test_clip_is_inclusive(weather_df):
    out = clip(weather_df, pd.Timestamp("2025-08-21 22:00"), pd.Timestamp("2025-08-22 00:00"))
    assert len(out) == 6
    assert out["datetime"].min() == pd.Timestamp("2025-08-21 22:00")
    assert out["datetime"].max() == pd.Timestamp("2025-08-22 00:00")


def test_time_steps_hourly_within_bounds():
    steps = time_steps(pd.Timestamp("2025-08-21 21:30"), pd.Timestamp("2025-08-22 02:10"))
    assert steps[0] == pd.Timestamp("2025-08-21 22:00")
    assert steps[-1] == pd.Timestamp("2025-08-22 02:00")
    assert len(steps) == 5


def test_values_at_returns_station_value_pairs(weather_df):
    v = values_at(weather_df, "pressure", pd.Timestamp("2025-08-21 23:00"))
    assert dict(zip(v["station"], v["value"])) == {"福岡": 995.0, "鹿児島": 980.0}


def test_values_at_unknown_time_is_empty(weather_df):
    assert values_at(weather_df, "pressure", pd.Timestamp("2025-08-25 00:00")).empty


def test_position_at_interpolates_between_points(track_df):
    assert position_at(track_df, pd.Timestamp("2025-08-21 18:00")) == pytest.approx((31.8, 130.5))
    assert position_at(track_df, pd.Timestamp("2025-08-21 09:00")) == pytest.approx((30.0, 129.5))


def test_position_at_outside_range_is_none(track_df):
    assert position_at(track_df, pd.Timestamp("2025-08-23 00:00")) is None
    assert position_at(None, pd.Timestamp("2025-08-21 18:00")) is None


def test_typhoon_position_prefers_track(landfall_df, track_df):
    e = get_event("202512", landfall_df, track_df)
    assert typhoon_position(e, pd.Timestamp("2025-08-21 18:00")) == pytest.approx((31.8, 130.5))


def test_typhoon_position_falls_back_to_landfall_within_6h(landfall_df):
    e = get_event("202512", landfall_df)   # track なし
    assert typhoon_position(e, pd.Timestamp("2025-08-21 18:00")) == pytest.approx((31.6, 130.3))
    assert typhoon_position(e, pd.Timestamp("2025-08-23 00:00")) is None
```

- [ ] **Step 2: 失敗を確認する**

Run: `uv run pytest tests/test_timeseries.py -q`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: timeseries.py を書く**

`typhoon_app/analysis/timeseries.py`:
```python
"""時系列データの絞り込みと、特定時刻の値の取り出し（純関数）。"""
from __future__ import annotations

import pandas as pd


def clip(df: pd.DataFrame, start, end) -> pd.DataFrame:
    """start <= datetime <= end の行だけ返す。"""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    mask = (df["datetime"] >= start) & (df["datetime"] <= end)
    return df.loc[mask].reset_index(drop=True)


def time_steps(start, end, freq: str = "1h") -> pd.DatetimeIndex:
    """start 以上 end 以下の正時の並び（地図タブの時刻スライダー用）。"""
    return pd.date_range(pd.Timestamp(start).ceil("h"), pd.Timestamp(end).floor("h"), freq=freq)


def values_at(df: pd.DataFrame, var_key: str, t) -> pd.DataFrame:
    """時刻 t（正時に切り捨て）における各地点の var_key の値。列: station, value。"""
    t = pd.Timestamp(t).floor("h")
    rows = df.loc[df["datetime"] == t, ["station", var_key]].rename(columns={var_key: "value"})
    return rows.reset_index(drop=True)
```

- [ ] **Step 4: track.py を書く**

`typhoon_app/analysis/track.py`:
```python
"""台風の位置を時刻から求める（純関数）。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from typhoon_app.data.typhoon import TyphoonEvent

_FALLBACK_TOLERANCE = pd.Timedelta(hours=6)


def position_at(track: pd.DataFrame | None, t) -> tuple[float, float] | None:
    """経路点を時間で線形補間した位置。経路が無い／範囲外なら None。"""
    if track is None or track.empty:
        return None
    trk = track.dropna(subset=["datetime", "lat", "lon"]).sort_values("datetime")
    if trk.empty:
        return None
    t = pd.Timestamp(t)
    t0, t1 = trk["datetime"].iloc[0], trk["datetime"].iloc[-1]
    if t < t0 or t > t1:
        return None
    xs = (trk["datetime"] - t0).dt.total_seconds().to_numpy()
    x = (t - t0).total_seconds()
    lat = float(np.interp(x, xs, trk["lat"].to_numpy(dtype=float)))
    lon = float(np.interp(x, xs, trk["lon"].to_numpy(dtype=float)))
    return lat, lon


def typhoon_position(event: TyphoonEvent, t) -> tuple[float, float] | None:
    """経路があれば補間位置。無ければ 6 時間以内に上陸/接近点があればその位置。どちらも無ければ None。"""
    pos = position_at(event.track, t)
    if pos is not None:
        return pos
    t = pd.Timestamp(t)
    lf = event.landfalls
    deltas = (lf["datetime"] - t).abs()
    i = deltas.idxmin()
    if deltas.loc[i] > _FALLBACK_TOLERANCE:
        return None
    return float(lf.loc[i, "lat"]), float(lf.loc[i, "lon"])
```

- [ ] **Step 5: テストを通す**

Run: `uv run pytest tests/test_timeseries.py -q`
Expected: `8 passed`

- [ ] **Step 6: コミット**

```bash
git add typhoon_app/analysis/timeseries.py typhoon_app/analysis/track.py tests/test_timeseries.py
git commit -m "Add time-series clipping, hourly steps, and typhoon position interpolation"
```

---

### Task 8: analysis/summary.py（地点別サマリ）

**Files:**
- Create: `typhoon_app/analysis/summary.py`
- Test: `tests/test_summary.py`

**Interfaces:**
- Produces:
  - `SUMMARY_COLUMNS: list[str]` = `["station", "min_pressure", "min_pressure_time", "max_wind_speed", "max_wind_speed_time", "max_wind_direction", "total_precipitation", "max_precipitation", "max_precipitation_time", "max_temperature", "min_temperature", "missing_rate"]`
  - `MISSING_RATE_COLUMNS = ["temperature", "precipitation", "wind_speed", "pressure"]`
  - `summarize(df: pd.DataFrame) -> pd.DataFrame`（1 地点 1 行。`df` が空なら `SUMMARY_COLUMNS` だけの空 DataFrame。全欠測の指標は NaN / NaT / None）

- [ ] **Step 1: テストを書く**

`tests/test_summary.py`:
```python
import numpy as np
import pandas as pd
import pytest

from typhoon_app.analysis.summary import SUMMARY_COLUMNS, summarize
from typhoon_app.data.schema import WEATHER_COLUMNS


def test_summarize_fukuoka(weather_df):
    s = summarize(weather_df).set_index("station")
    f = s.loc["福岡"]
    assert f["min_pressure"] == 995.0
    assert f["min_pressure_time"] == pd.Timestamp("2025-08-21 23:00")
    assert f["max_wind_speed"] == 6.0
    assert f["max_wind_speed_time"] == pd.Timestamp("2025-08-21 23:00")
    assert f["max_wind_direction"] == "南東"
    assert f["total_precipitation"] == pytest.approx(3.5)
    assert f["max_precipitation"] == 2.0
    assert f["max_precipitation_time"] == pd.Timestamp("2025-08-21 23:00")
    assert f["max_temperature"] == 28.0
    assert f["min_temperature"] == 26.0
    assert f["missing_rate"] == pytest.approx(100 / 24)   # 気温 1 セル欠測 / 4 要素 × 6 時刻


def test_summarize_kagoshima_with_missing(weather_df):
    k = summarize(weather_df).set_index("station").loc["鹿児島"]
    assert k["min_pressure"] == 980.0
    assert k["max_wind_speed"] == 20.0
    assert k["max_wind_speed_time"] == pd.Timestamp("2025-08-22 00:00")
    assert k["max_wind_direction"] == "南東"
    assert k["total_precipitation"] == pytest.approx(44.5)
    assert k["max_precipitation"] == 20.5
    assert k["missing_rate"] == pytest.approx(200 / 24)   # 降水 1 + 風速 1


def test_summarize_columns_and_order(weather_df):
    s = summarize(weather_df)
    assert list(s.columns) == SUMMARY_COLUMNS
    assert s["station"].tolist() == ["福岡", "鹿児島"]


def test_summarize_empty_input():
    s = summarize(pd.DataFrame(columns=list(WEATHER_COLUMNS)))
    assert s.empty and list(s.columns) == SUMMARY_COLUMNS


def test_summarize_all_missing_variable(weather_df):
    df = weather_df.assign(pressure=np.nan, wind_speed=np.nan)
    s = summarize(df).set_index("station")
    assert pd.isna(s.loc["福岡", "min_pressure"])
    assert pd.isna(s.loc["福岡", "min_pressure_time"])
    assert s.loc["福岡", "max_wind_direction"] is None
```

- [ ] **Step 2: 失敗を確認する**

Run: `uv run pytest tests/test_summary.py -q`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: summary.py を書く**

`typhoon_app/analysis/summary.py`:
```python
"""地点別サマリ（設計書 §6）。NaN は無視する。"""
from __future__ import annotations

import numpy as np
import pandas as pd

MISSING_RATE_COLUMNS = ["temperature", "precipitation", "wind_speed", "pressure"]

SUMMARY_COLUMNS = [
    "station",
    "min_pressure", "min_pressure_time",
    "max_wind_speed", "max_wind_speed_time", "max_wind_direction",
    "total_precipitation", "max_precipitation", "max_precipitation_time",
    "max_temperature", "min_temperature",
    "missing_rate",
]


def _extreme(g: pd.DataFrame, col: str, kind: str):
    """(値, 発生時刻, 行ラベル)。全欠測なら (nan, NaT, None)。"""
    s = g[col].dropna()
    if s.empty:
        return np.nan, pd.NaT, None
    label = s.idxmax() if kind == "max" else s.idxmin()
    return float(s.loc[label]), g.loc[label, "datetime"], label


def _summarize_station(g: pd.DataFrame) -> dict:
    p, p_t, _ = _extreme(g, "pressure", "min")
    w, w_t, w_i = _extreme(g, "wind_speed", "max")
    w_dir = g.loc[w_i, "wind_direction"] if w_i is not None else None
    if w_dir is not None and pd.isna(w_dir):
        w_dir = None
    r, r_t, _ = _extreme(g, "precipitation", "max")
    t_max, _, _ = _extreme(g, "temperature", "max")
    t_min, _, _ = _extreme(g, "temperature", "min")
    total = float(g["precipitation"].sum()) if g["precipitation"].notna().any() else np.nan
    cells = g[MISSING_RATE_COLUMNS]
    missing_rate = float(cells.isna().to_numpy().mean() * 100) if cells.size else np.nan
    return {
        "min_pressure": p, "min_pressure_time": p_t,
        "max_wind_speed": w, "max_wind_speed_time": w_t, "max_wind_direction": w_dir,
        "total_precipitation": total, "max_precipitation": r, "max_precipitation_time": r_t,
        "max_temperature": t_max, "min_temperature": t_min,
        "missing_rate": missing_rate,
    }


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    """1 地点 1 行のサマリ。df が空なら SUMMARY_COLUMNS だけの空 DataFrame。"""
    if df.empty:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)
    rows = []
    for name, g in df.groupby("station", sort=True):
        rows.append({"station": str(name), **_summarize_station(g.reset_index(drop=True))})
    return pd.DataFrame(rows, columns=SUMMARY_COLUMNS)
```

- [ ] **Step 4: テストを通す**

Run: `uv run pytest tests/test_summary.py -q`
Expected: `5 passed`

- [ ] **Step 5: コミット**

```bash
git add typhoon_app/analysis/summary.py tests/test_summary.py
git commit -m "Add per-station summary: extremes, totals, and missing rate"
```

---

### Task 9: charts/common.py + charts/timeseries.py + charts/ranking.py

**Files:**
- Create: `typhoon_app/charts/common.py`, `typhoon_app/charts/timeseries.py`, `typhoon_app/charts/ranking.py`
- Test: `tests/test_charts.py`（Task 10 で地図のテストを追記する）

**Interfaces:**
- Consumes: `config.Variable`, `analysis.summary` の出力
- Produces:
  - `common.empty_figure(title: str) -> go.Figure`（トレース無し、「データなし」注釈）
  - `timeseries.variable_chart(df, var: Variable, reference_times=(), station_order=None) -> go.Figure`（地点ごと 1 トレース、`reference_times` ごとに縦線 shape 1 本）
  - `ranking.ranking_chart(summary, column: str, title: str, unit: str, ascending: bool) -> go.Figure`（横棒、上から順位順）

- [ ] **Step 1: テストを書く**

`tests/test_charts.py`:
```python
import pandas as pd

from typhoon_app.analysis.summary import summarize
from typhoon_app.charts.ranking import ranking_chart
from typhoon_app.charts.timeseries import variable_chart
from typhoon_app.config import VARIABLES
from typhoon_app.data.schema import WEATHER_COLUMNS


def test_variable_chart_line_one_trace_per_station_and_vlines(weather_df):
    fig = variable_chart(weather_df, VARIABLES["pressure"], [pd.Timestamp("2025-08-21 17:00")], ["鹿児島", "福岡"])
    assert len(fig.data) == 2
    assert fig.data[0].type == "scatter"
    assert fig.data[0].name == "鹿児島"        # station_order が効く
    assert len(fig.layout.shapes) == 1
    assert "hPa" in fig.layout.yaxis.title.text


def test_variable_chart_bar_for_precipitation(weather_df):
    fig = variable_chart(weather_df, VARIABLES["precipitation"])
    assert len(fig.data) == 2
    assert fig.data[0].type == "bar"


def test_variable_chart_empty(weather_df):
    fig = variable_chart(pd.DataFrame(columns=list(WEATHER_COLUMNS)), VARIABLES["pressure"])
    assert len(fig.data) == 0
    assert "データなし" in fig.layout.annotations[0].text


def test_ranking_chart_orders_by_value(weather_df):
    s = summarize(weather_df)
    fig = ranking_chart(s, "min_pressure", "最低気圧", "hPa", ascending=True)
    assert list(fig.data[0].y) == ["鹿児島", "福岡"]
    fig2 = ranking_chart(s, "total_precipitation", "総降水量", "mm", ascending=False)
    assert list(fig2.data[0].y) == ["鹿児島", "福岡"]
```

- [ ] **Step 2: 失敗を確認する**

Run: `uv run pytest tests/test_charts.py -q`
Expected: FAIL（`ModuleNotFoundError`）

- [ ] **Step 3: common.py を書く**

`typhoon_app/charts/common.py`:
```python
"""グラフ共通部品。"""
from __future__ import annotations

import plotly.graph_objects as go


def empty_figure(title: str) -> go.Figure:
    """データが無いときに出す空の Figure。"""
    fig = go.Figure()
    fig.update_layout(
        title=title,
        annotations=[dict(text="データなし", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)],
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig
```

- [ ] **Step 4: timeseries.py（charts）を書く**

`typhoon_app/charts/timeseries.py`:
```python
"""要素ごとの時系列グラフ（設計書 §3 時系列タブ）。"""
from __future__ import annotations

from collections.abc import Iterable, Sequence

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from typhoon_app.charts.common import empty_figure
from typhoon_app.config import Variable


def variable_chart(
    df: pd.DataFrame,
    var: Variable,
    reference_times: Iterable = (),
    station_order: Sequence[str] | None = None,
) -> go.Figure:
    """1 要素ぶんのグラフ。地点で色分け。降水は棒、他は折れ線（欠測は線を切る）。
    reference_times の時刻に赤い破線を引く。"""
    title = f"{var.label}（{var.unit}）"
    data = df.assign(station=df["station"].astype(str))
    if var.kind == "bar":
        data = data.dropna(subset=[var.key])
    if data.empty:
        return empty_figure(title)

    orders = {"station": list(station_order)} if station_order else None
    if var.kind == "bar":
        fig = px.bar(data, x="datetime", y=var.key, color="station", barmode="group", category_orders=orders)
    else:
        fig = px.line(data, x="datetime", y=var.key, color="station", category_orders=orders)
        fig.update_traces(connectgaps=False)

    for t in reference_times:
        fig.add_shape(type="line", x0=t, x1=t, y0=0, y1=1, yref="paper", line=dict(color="red", dash="dash"))
        fig.add_annotation(x=t, y=1, yref="paper", text="上陸/接近", showarrow=False, yanchor="bottom", font=dict(color="red", size=11))

    fig.update_layout(
        title=title,
        xaxis_title="日時",
        yaxis_title=f"{var.label}（{var.unit}）",
        legend_title="地点",
        hovermode="x unified",
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig
```

- [ ] **Step 5: ranking.py を書く**

`typhoon_app/charts/ranking.py`:
```python
"""地点ランキングの横棒グラフ（設計書 §3 概要タブ）。"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from typhoon_app.charts.common import empty_figure


def ranking_chart(summary: pd.DataFrame, column: str, title: str, unit: str, ascending: bool) -> go.Figure:
    """summary[column] で地点を並べた横棒グラフ。上が 1 位。"""
    data = summary.dropna(subset=[column]).sort_values(column, ascending=ascending)
    if data.empty:
        return empty_figure(title)
    data = data.assign(station=data["station"].astype(str))
    fig = px.bar(data, x=column, y="station", orientation="h", text=column)
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(
        title=title,
        xaxis_title=f"{title}（{unit}）",
        yaxis_title="地点",
        yaxis=dict(autorange="reversed"),   # 並び順の先頭を上に
        margin=dict(l=40, r=20, t=50, b=40),
        showlegend=False,
    )
    return fig
```

- [ ] **Step 6: テストを通す**

Run: `uv run pytest tests/test_charts.py -q`
Expected: `4 passed`

- [ ] **Step 7: コミット**

```bash
git add typhoon_app/charts/common.py typhoon_app/charts/timeseries.py typhoon_app/charts/ranking.py tests/test_charts.py
git commit -m "Add time-series and ranking charts (Plotly)"
```

---

### Task 10: charts/map.py（地点マーカー＋台風経路の地図）

**Files:**
- Create: `typhoon_app/charts/map.py`
- Modify: `tests/test_charts.py`（地図テストを追記）

**Interfaces:**
- Consumes: `config.Station, Variable, MAP_CENTER, MAP_ZOOM`, `data.station.load_stations`, `analysis.timeseries.values_at` の出力
- Produces:
  - `station_map(stations: dict[str, Station], values: pd.DataFrame | None, var: Variable | None, landfalls: pd.DataFrame, track: pd.DataFrame | None = None, typhoon_pos: tuple[float, float] | None = None, title: str = "") -> go.Figure`
    - トレース名: `"台風経路"`（track があるとき）, `"上陸/接近地点"`, `"観測地点"`（値で色分け）, `"観測地点（欠測）"`, `"台風中心"`（typhoon_pos があるとき）
    - `layout.map.style == "open-street-map"`

- [ ] **Step 1: テストを追記する**

`tests/test_charts.py` の末尾に追加:
```python
from pathlib import Path

from typhoon_app.analysis.timeseries import values_at
from typhoon_app.charts.map import station_map
from typhoon_app.data.station import load_stations


def test_station_map_with_values_track_and_position(weather_df, landfall_df, track_df):
    stations = load_stations(Path("/nonexistent/station.csv"))
    values = values_at(weather_df, "pressure", pd.Timestamp("2025-08-21 23:00"))
    fig = station_map(stations, values, VARIABLES["pressure"], landfall_df, track_df, (31.8, 130.5), title="t")
    names = [tr.name for tr in fig.data]
    assert "台風経路" in names and "上陸/接近地点" in names and "台風中心" in names
    assert "観測地点" in names and "観測地点（欠測）" in names   # 福岡・鹿児島以外は値が無い
    assert fig.layout.map.style == "open-street-map"
    assert fig.layout.map.zoom == 5


def test_station_map_without_values_or_track(landfall_df):
    stations = load_stations(Path("/nonexistent/station.csv"))
    fig = station_map(stations, None, None, landfall_df)
    names = [tr.name for tr in fig.data]
    assert "台風経路" not in names and "台風中心" not in names
    assert "上陸/接近地点" in names and "観測地点" in names
```

- [ ] **Step 2: 失敗を確認する**

Run: `uv run pytest tests/test_charts.py -q`
Expected: FAIL（`ModuleNotFoundError: typhoon_app.charts.map`）

- [ ] **Step 3: map.py を書く**

`typhoon_app/charts/map.py`:
```python
"""地図タブの Figure（設計書 §3）。OpenStreetMap タイルなのでトークン不要。"""
from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go

from typhoon_app.config import MAP_CENTER, MAP_ZOOM, Station, Variable


def _fmt_time(ts) -> str:
    ts = pd.Timestamp(ts)
    return f"{ts.month}/{ts.day} {ts:%H:%M}"


def station_map(
    stations: dict[str, Station],
    values: pd.DataFrame | None,
    var: Variable | None,
    landfalls: pd.DataFrame,
    track: pd.DataFrame | None = None,
    typhoon_pos: tuple[float, float] | None = None,
    title: str = "",
) -> go.Figure:
    fig = go.Figure()

    # 1) 台風経路（あれば）
    if track is not None and not track.empty:
        fig.add_trace(go.Scattermap(
            lat=track["lat"], lon=track["lon"], mode="lines+markers", name="台風経路",
            line=dict(color="gray", width=2), marker=dict(size=6, color="gray"),
            hovertext=[_fmt_time(t) for t in track["datetime"]], hoverinfo="text",
        ))

    # 2) 上陸/接近地点
    if landfalls is not None and not landfalls.empty:
        fig.add_trace(go.Scattermap(
            lat=landfalls["lat"], lon=landfalls["lon"], mode="markers", name="上陸/接近地点",
            marker=dict(size=12, color="red"),
            hovertext=[f"上陸/接近 {_fmt_time(t)}" for t in landfalls["datetime"]], hoverinfo="text",
        ))

    # 3) 観測地点（値があれば色分け、無ければ灰色）
    names = list(stations)
    value_map: dict[str, float] = {}
    if values is not None and var is not None and not values.empty:
        value_map = {str(s): float(v) for s, v in zip(values["station"], values["value"]) if not pd.isna(v)}
    colored = [n for n in names if n in value_map]
    grey = [n for n in names if n not in value_map]

    if colored:
        marker = dict(size=16, color=[value_map[n] for n in colored], colorscale="Viridis", showscale=True)
        if var is not None:
            marker["colorbar"] = dict(title=f"{var.label}（{var.unit}）")
        unit = var.unit if var is not None else ""
        fig.add_trace(go.Scattermap(
            lat=[stations[n].lat for n in colored], lon=[stations[n].lon for n in colored],
            mode="markers+text", name="観測地点", text=colored, textposition="top right",
            marker=marker,
            hovertext=[f"{n}: {value_map[n]:.1f} {unit}" for n in colored], hoverinfo="text",
        ))
    if grey:
        fig.add_trace(go.Scattermap(
            lat=[stations[n].lat for n in grey], lon=[stations[n].lon for n in grey],
            mode="markers+text", name="観測地点" if not colored else "観測地点（欠測）",
            text=grey, textposition="top right",
            marker=dict(size=14, color="lightgray"),
            hovertext=[f"{n}: データなし" for n in grey], hoverinfo="text",
        ))

    # 4) 台風中心（この時刻の位置）
    if typhoon_pos is not None and not any(math.isnan(v) for v in typhoon_pos):
        fig.add_trace(go.Scattermap(
            lat=[typhoon_pos[0]], lon=[typhoon_pos[1]], mode="markers", name="台風中心",
            marker=dict(size=22, color="orange", opacity=0.8), hovertext=["台風中心"], hoverinfo="text",
        ))

    fig.update_layout(
        title=title,
        map=dict(style="open-street-map", center=dict(lat=MAP_CENTER[0], lon=MAP_CENTER[1]), zoom=MAP_ZOOM),
        margin=dict(l=0, r=0, t=40, b=0),
        height=550,
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.7)"),
    )
    return fig
```

- [ ] **Step 4: テストを通す**

Run: `uv run pytest tests/test_charts.py -q`
Expected: `6 passed`

- [ ] **Step 5: コミット**

```bash
git add typhoon_app/charts/map.py tests/test_charts.py
git commit -m "Add station/typhoon map chart with OpenStreetMap tiles"
```

---

### Task 11: ui 部品（state / loaders / sidebar / header / glossary）

**Files:**
- Create: `typhoon_app/ui/state.py`, `typhoon_app/ui/loaders.py`, `typhoon_app/ui/sidebar.py`, `typhoon_app/ui/header.py`, `typhoon_app/ui/glossary.py`

**Interfaces:**
- Consumes: `config.MAX_WINDOW_DAYS, DEFAULT_WINDOW_DAYS, VARIABLES, DEFAULT_VARIABLES`, `data.typhoon.TyphoonEvent, load_landfall, load_track`, `data.station.load_stations`, `data.weather.StationResult`
- Produces:
  - `state.Selection(typhoon_id: str, stations: tuple[str, ...], window_days: int, variables: tuple[str, ...])`（frozen dataclass）
  - `loaders.load_landfall_cached()`, `loaders.load_track_cached()`, `loaders.load_stations_cached()`（`st.cache_data` 付き。引数なし）
  - `sidebar.render_sidebar(events: list[TyphoonEvent], station_names: list[str]) -> Selection`
  - `sidebar.render_data_status(results: dict[str, StationResult], fetcher_available: bool) -> None`
  - `header.render_header(event: TyphoonEvent, nearest_name: str) -> None`
  - `glossary.render_glossary() -> None`（サイドバーの expander）
- UI 層は自動テスト対象外（Task 13 の AppTest スモークで全体をカバーする）

- [ ] **Step 1: state.py を書く**

`typhoon_app/ui/state.py`:
```python
"""サイドバーの選択状態。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Selection:
    typhoon_id: str
    stations: tuple[str, ...]
    window_days: int
    variables: tuple[str, ...]
```

- [ ] **Step 2: loaders.py を書く**

`typhoon_app/ui/loaders.py`:
```python
"""読込系のメモリキャッシュ（ファイルが永続キャッシュ、こちらは再描画の高速化）。"""
from __future__ import annotations

import streamlit as st

from typhoon_app.data.station import load_stations
from typhoon_app.data.typhoon import load_landfall, load_track


@st.cache_data(show_spinner=False)
def load_landfall_cached():
    return load_landfall()


@st.cache_data(show_spinner=False)
def load_track_cached():
    return load_track()


@st.cache_data(show_spinner=False)
def load_stations_cached():
    return load_stations()
```

- [ ] **Step 3: sidebar.py を書く**

`typhoon_app/ui/sidebar.py`:
```python
"""サイドバー: 条件の選択とデータ状態の表示（設計書 §3 / §7）。"""
from __future__ import annotations

import streamlit as st

from typhoon_app.config import DEFAULT_VARIABLES, DEFAULT_WINDOW_DAYS, MAX_WINDOW_DAYS, VARIABLES
from typhoon_app.data.typhoon import TyphoonEvent
from typhoon_app.data.weather import StationResult
from typhoon_app.ui.state import Selection

_STATUS_LABEL = {
    "cached": "● キャッシュ済み",
    "fetched": "● 取得完了",
    "unavailable": "○ 未取得",
    "error": "✕ 取得失敗",
}


def render_sidebar(events: list[TyphoonEvent], station_names: list[str]) -> Selection:
    labels = {e.typhoon_id: e.label for e in events}
    with st.sidebar:
        st.header("表示条件")
        typhoon_id = st.selectbox(
            "台風を選択", options=[e.typhoon_id for e in events], format_func=lambda i: labels[i]
        )
        stations = st.multiselect("地点を選択", options=station_names, default=station_names)
        window_days = st.slider(
            "表示期間（接近日の前後 N 日）", min_value=1, max_value=MAX_WINDOW_DAYS, value=DEFAULT_WINDOW_DAYS
        )
        variables = st.multiselect(
            "気象要素",
            options=list(VARIABLES),
            default=list(DEFAULT_VARIABLES),
            format_func=lambda k: VARIABLES[k].label,
        )
    return Selection(typhoon_id, tuple(stations), window_days, tuple(variables))


def render_data_status(results: dict[str, StationResult], fetcher_available: bool) -> None:
    with st.sidebar:
        st.divider()
        st.subheader("データ状態")
        if not fetcher_available:
            st.caption("取得関数が見つからないため、キャッシュ専用モードで動作中です")
        for r in results.values():
            st.write(f"{_STATUS_LABEL[r.status]}：{r.station}")
            if r.message:
                st.caption(r.message)
        col1, col2 = st.columns(2)
        if any(r.status == "error" for r in results.values()):
            if col1.button("再試行"):
                st.rerun()
        if col2.button("データを再読込"):
            st.cache_data.clear()
            st.rerun()
```

- [ ] **Step 4: header.py を書く**

`typhoon_app/ui/header.py`:
```python
"""台風ヘッダ（設計書 §3）。"""
from __future__ import annotations

import math

import streamlit as st

from typhoon_app.data.typhoon import TyphoonEvent


def _fmt(v: float, unit: str, digits: int = 0) -> str:
    return "—" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{digits}f} {unit}"


def render_header(event: TyphoonEvent, nearest_name: str) -> None:
    st.title(f"🌀 台風 第{event.number}号（{event.year}年）")
    times = "、".join(f"{t.month}/{t.day} {t:%H:%M}" for t in event.reference_times)
    c1, c2, c3 = st.columns(3)
    c1.metric("上陸/接近時刻", times)
    c1.caption(f"{nearest_name}付近（北緯 {event.landfall_lat:.1f}°・東経 {event.landfall_lon:.1f}°）")
    c2.metric("中心気圧（接近時）", _fmt(event.center_pressure, "hPa"))
    c3.metric("最大風速（接近時）", _fmt(event.max_wind_kt, "kt"))
```

- [ ] **Step 5: glossary.py を書く**

`typhoon_app/ui/glossary.py`:
```python
"""用語の説明（非専門家向け、設計書 §2・§3）。"""
from __future__ import annotations

import streamlit as st


def render_glossary() -> None:
    with st.sidebar:
        with st.expander("ℹ 用語の説明"):
            st.markdown(
            """
- **hPa（ヘクトパスカル）**: 気圧の単位。台風が近づくほど下がる。
- **上陸/接近時刻**: 気象庁の記録にある、台風がその地域に上陸または最も近づいた時刻。グラフの赤い破線。
- **最接近時刻（地点）**: この画面では「その地点の気圧が最も低くなった時刻」を目安として使っている。
- **kt（ノット）**: 台風の最大風速の単位。1 kt ≒ 0.51 m/s。
- **欠測率**: 表示期間中に観測値が無かった割合。高いほど集計の信頼度が下がる。
- **降水量 0.0**: 「雨が降らなかった」こと。「欠測」とは区別して扱っている。
                """
            )
```

- [ ] **Step 6: import が通ることを確認する**

Run: `uv run python -c "import typhoon_app.ui.state, typhoon_app.ui.loaders, typhoon_app.ui.sidebar, typhoon_app.ui.header, typhoon_app.ui.glossary; print('ok')"`
Expected: `ok`（Streamlit の "missing ScriptRunContext" 警告は出てもよい）

- [ ] **Step 7: コミット**

```bash
git add typhoon_app/ui/state.py typhoon_app/ui/loaders.py typhoon_app/ui/sidebar.py typhoon_app/ui/header.py typhoon_app/ui/glossary.py
git commit -m "Add sidebar, header, glossary, and cached loaders for the UI"
```

---

### Task 12: ui タブ（overview / timeseries / map）＋ app.py 配線

**Files:**
- Create: `typhoon_app/ui/tab_overview.py`, `typhoon_app/ui/tab_timeseries.py`, `typhoon_app/ui/tab_map.py`
- Modify: `app.py`（現在は空ファイル）

**Interfaces:**
- Consumes: Task 2〜11 のすべて
- Produces:
  - `tab_overview.render_overview(summary: pd.DataFrame, variables: Sequence[str]) -> None`
  - `tab_timeseries.render_timeseries(df, variables, reference_times, station_order) -> None`
  - `tab_map.render_map(df, stations: dict[str, Station], event: TyphoonEvent, variables, window: tuple[Timestamp, Timestamp]) -> None`
  - `app.main()`

- [ ] **Step 1: tab_overview.py を書く**

`typhoon_app/ui/tab_overview.py`:
```python
"""概要タブ: 地点別サマリ表とランキング（設計書 §3 / §6）。"""
from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import streamlit as st

from typhoon_app.charts.ranking import ranking_chart

# 要素 → サマリ表に出す列
_COLUMNS_BY_VARIABLE = {
    "pressure": ["min_pressure", "min_pressure_time"],
    "wind_speed": ["max_wind_speed", "max_wind_speed_time", "max_wind_direction"],
    "precipitation": ["total_precipitation", "max_precipitation", "max_precipitation_time"],
    "temperature": ["max_temperature", "min_temperature"],
}
_LABELS = {
    "station": "地点",
    "min_pressure": "最低気圧 (hPa)", "min_pressure_time": "最低気圧の時刻",
    "max_wind_speed": "最大風速 (m/s)", "max_wind_speed_time": "最大風速の時刻", "max_wind_direction": "そのときの風向",
    "total_precipitation": "総降水量 (mm)", "max_precipitation": "最大1時間降水量 (mm)", "max_precipitation_time": "その時刻",
    "max_temperature": "最高気温 (℃)", "min_temperature": "最低気温 (℃)",
    "missing_rate": "欠測率 (%)",
}
# 要素 → ランキング (列, タイトル, 単位, 昇順か)
_RANKINGS = {
    "pressure": ("min_pressure", "最低気圧", "hPa", True),
    "wind_speed": ("max_wind_speed", "最大風速", "m/s", False),
    "precipitation": ("total_precipitation", "総降水量", "mm", False),
    "temperature": ("max_temperature", "最高気温", "℃", False),
}


def _fmt_time(v) -> str:
    if pd.isna(v):
        return "—"
    t = pd.Timestamp(v)
    return f"{t.month}/{t.day} {t:%H:%M}"


def render_overview(summary: pd.DataFrame, variables: Sequence[str]) -> None:
    if summary.empty:
        st.info("表示できるデータがありません。")
        return
    cols = ["station"] + [c for v in variables for c in _COLUMNS_BY_VARIABLE.get(v, [])] + ["missing_rate"]
    table = summary[cols].copy()
    for c in [c for c in cols if c.endswith("_time")]:
        table[c] = table[c].map(_fmt_time)
    table = table.rename(columns=_LABELS)

    st.subheader("地点別サマリ")
    st.dataframe(table, hide_index=True, width="stretch")

    items = [(v, *_RANKINGS[v]) for v in variables if v in _RANKINGS]
    if items:
        st.subheader("ランキング")
        for col, (_, column, title, unit, asc) in zip(st.columns(len(items)), items):
            col.plotly_chart(ranking_chart(summary, column, title, unit, ascending=asc), width="stretch")
```

- [ ] **Step 2: tab_timeseries.py を書く**

`typhoon_app/ui/tab_timeseries.py`:
```python
"""時系列タブ: 要素ごとに 1 枚のグラフ（設計書 §3）。"""
from __future__ import annotations

from collections.abc import Iterable, Sequence

import pandas as pd
import streamlit as st

from typhoon_app.charts.timeseries import variable_chart
from typhoon_app.config import VARIABLES


def render_timeseries(
    df: pd.DataFrame, variables: Sequence[str], reference_times: Iterable, station_order: Sequence[str]
) -> None:
    if df.empty:
        st.info("表示できるデータがありません。")
        return
    if not variables:
        st.info("サイドバーで気象要素を 1 つ以上選んでください。")
        return
    ref = list(reference_times)
    for key in variables:
        st.plotly_chart(variable_chart(df, VARIABLES[key], ref, station_order), width="stretch")
```

- [ ] **Step 3: tab_map.py を書く**

`typhoon_app/ui/tab_map.py`:
```python
"""地図タブ: 時刻スライダー＋地点マーカー＋台風位置（設計書 §3）。"""
from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import streamlit as st

from typhoon_app.analysis.timeseries import time_steps, values_at
from typhoon_app.analysis.track import typhoon_position
from typhoon_app.charts.map import station_map
from typhoon_app.config import VARIABLES, Station
from typhoon_app.data.typhoon import TyphoonEvent


def _fmt(t: pd.Timestamp) -> str:
    return f"{t.month}/{t.day} {t:%H:%M}"


def render_map(
    df: pd.DataFrame,
    stations: dict[str, Station],
    event: TyphoonEvent,
    variables: Sequence[str],
    window: tuple[pd.Timestamp, pd.Timestamp],
) -> None:
    steps = list(time_steps(*window))
    if not steps:
        st.info("表示できる時刻がありません。")
        return
    default = min(steps, key=lambda t: abs(t - event.first_time))
    t = st.select_slider("時刻", options=steps, value=default, format_func=_fmt)

    var_key = None
    if variables:
        var_key = st.radio(
            "マーカーの色にする要素", options=list(variables), horizontal=True, format_func=lambda k: VARIABLES[k].label
        )
    values = values_at(df, var_key, t) if (var_key and not df.empty) else None
    var = VARIABLES[var_key] if var_key else None

    fig = station_map(
        stations, values, var, event.landfalls, event.track, typhoon_position(event, t), title=f"{_fmt(t)} の状況"
    )
    st.plotly_chart(fig, width="stretch")
    if event.track is None:
        st.caption("全経路データが無いため、台風は上陸/接近地点のみ表示しています。")
```

- [ ] **Step 4: app.py を書く**

`app.py`:
```python
"""Typhoon-Analyze: 台風接近時の九州・沖縄 8 地点の気象変化を可視化する Streamlit アプリ。
ここは配線だけ。ロジックは typhoon_app/ 配下にある。"""
from __future__ import annotations

import streamlit as st

from typhoon_app.analysis.summary import summarize
from typhoon_app.analysis.timeseries import clip
from typhoon_app.data.schema import SchemaError
from typhoon_app.data.source import get_fetcher
from typhoon_app.data.station import nearest_station
from typhoon_app.data.typhoon import get_event, list_typhoons
from typhoon_app.data.weather import StationResult, cache_path, combine, get_station_weather
from typhoon_app.ui.glossary import render_glossary
from typhoon_app.ui.header import render_header
from typhoon_app.ui.loaders import load_landfall_cached, load_stations_cached, load_track_cached
from typhoon_app.ui.sidebar import render_data_status, render_sidebar
from typhoon_app.ui.tab_map import render_map
from typhoon_app.ui.tab_overview import render_overview
from typhoon_app.ui.tab_timeseries import render_timeseries


def main() -> None:
    st.set_page_config(page_title="台風と九州・沖縄の気象", page_icon="🌀", layout="wide")

    # 必須データ（無い／形式が違うときはメッセージを出して停止: 設計書 §7）
    try:
        landfall = load_landfall_cached()
        track = load_track_cached()
        stations = load_stations_cached()
    except FileNotFoundError as e:
        st.error(f"台風データがありません。data/processed/typhoon/landfall.csv を置いてください。\n\n{e}")
        st.stop()
    except SchemaError as e:
        st.error(f"データの形式が設計書 §4 と違います（データ担当に共有してください）。\n\n{e}")
        st.stop()
    events = list_typhoons(landfall, track)

    # 条件選択
    selection = render_sidebar(events, list(stations))
    event = get_event(selection.typhoon_id, landfall, track)

    # 気象データ（キャッシュ → 無ければオンデマンド取得）
    fetcher = get_fetcher()
    results: dict[str, StationResult] = {}
    for name in selection.stations:
        if cache_path(event.typhoon_id, name).exists():
            results[name] = get_station_weather(event.typhoon_id, name, event.fetch_window(), fetcher)
        else:
            with st.spinner(f"{name}: 気象庁から取得中…"):
                results[name] = get_station_weather(event.typhoon_id, name, event.fetch_window(), fetcher)
    render_data_status(results, fetcher is not None)
    render_glossary()

    # ヘッダ
    nearest = nearest_station(event.landfall_lat, event.landfall_lon, stations)
    render_header(event, nearest.name)

    if not selection.stations:
        st.info("サイドバーで地点を 1 つ以上選んでください。")
        st.stop()

    window = event.display_window(selection.window_days)
    df = clip(combine(results), *window)
    summary = summarize(df)

    tab_overview, tab_timeseries, tab_map = st.tabs(["概要", "時系列", "地図"])
    with tab_overview:
        render_overview(summary, selection.variables)
    with tab_timeseries:
        render_timeseries(df, selection.variables, event.reference_times, list(selection.stations))
    with tab_map:
        render_map(df, {n: stations[n] for n in selection.stations if n in stations}, event, selection.variables, window)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: データ無しの状態で起動し、エラー画面が出ることを確認する**

Run: `uv run streamlit run app.py --server.headless true --server.port 8502 &` → ブラウザで `http://localhost:8502` を開く
Expected: 赤いエラーボックス「台風データがありません。data/processed/typhoon/landfall.csv を置いてください。」が表示され、例外のスタックトレースは出ない。確認後 `kill %1`

- [ ] **Step 6: 全テストが通ることを確認する**

Run: `uv run pytest -q`
Expected: 全件 PASS（これまでの 40 件前後）

- [ ] **Step 7: コミット**

```bash
git add app.py typhoon_app/ui/tab_overview.py typhoon_app/ui/tab_timeseries.py typhoon_app/ui/tab_map.py
git commit -m "Wire up Streamlit app with overview, time-series, and map tabs"
```

---

### Task 13: 【暫定】開発用サンプルデータ生成 ＋ AppTest スモークテスト

> データ担当の成果物（`landfall.csv`・キャッシュ CSV）が揃うまで、手元の生データから **同じスキーマ** の `data/processed/` を作って動作確認するためのスクリプト。データ担当の成果物が来たら上書きされる前提。スキーマは spec §4 と同一なのでアプリ側の変更は不要。

**Files:**
- Create: `scripts/dev_sample_data.py`, `tests/test_app_smoke.py`
- Create（生成物）: `data/processed/typhoon/landfall.csv`, `data/processed/weather/2025{08,12,15}_{8 地点}.csv`

**Interfaces:**
- Consumes: `data/typhoon/typhoon_track.csv`（実体は xlsx）, `data/weather/weather_2025.csv`（cp932、行 3 = 地点名、行 6 以降データ、地点ごとに [気温, 降水量, 風速, 風向, 現地気圧, 天気] の 6 列）, `schema.validate_*`, `typhoon.get_event`, `weather.cache_path, write_cache`
- Produces: 上記の生成物（アプリがそのまま読める）

- [ ] **Step 1: dev_sample_data.py を書く**

`scripts/dev_sample_data.py`:
```python
"""【暫定】開発用サンプルデータを data/processed/ に生成する。

データ担当の成果物（同じスキーマ）が揃ったら不要になる。
使い方: uv run python scripts/dev_sample_data.py
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from typhoon_app.config import LANDFALL_CSV, STATION_NAMES  # noqa: E402
from typhoon_app.data.schema import validate_typhoon, validate_weather  # noqa: E402
from typhoon_app.data.typhoon import get_event  # noqa: E402
from typhoon_app.data.weather import cache_path, write_cache  # noqa: E402

RAW_TRACK = ROOT / "data" / "typhoon" / "typhoon_track.csv"      # 拡張子は csv だが中身は xlsx
RAW_WEATHER = ROOT / "data" / "weather" / "weather_2025.csv"    # 気象庁一括 DL（cp932、多段ヘッダ）
TARGET_TYPHOONS = ["202508", "202512", "202515"]

_JST_RE = re.compile(r"(\d{4})年(\d{2})月(\d{2})日(\d{2})時(\d{2})分")
_DAY_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日(\d{1,2})時")
_MISSING = {"", "×", "///", "#"}


def build_landfall() -> pd.DataFrame:
    # 拡張子は .csv だが中身は xlsx なので engine を明示する
    raw = pd.read_excel(RAW_TRACK, header=0, engine="openpyxl").iloc[:, 1:9]
    raw.columns = ["typhoon_id", "time", "lat", "lon", "pressure", "max_wind_kt", "storm_diameter_nm", "gale_diameter_nm"]
    raw = raw.dropna(subset=["typhoon_id"]).reset_index(drop=True)

    def parse_time(s):
        m = _JST_RE.search(str(s))
        return pd.Timestamp(*map(int, m.groups())) if m else pd.NaT

    def num(s):
        return pd.to_numeric(pd.Series(s).replace("-", np.nan), errors="coerce")

    df = pd.DataFrame({
        "typhoon_id": raw["typhoon_id"].astype(int).astype(str),
        "datetime": raw["time"].map(parse_time),
        "lat": num(raw["lat"]).to_numpy(),
        "lon": num(raw["lon"]).to_numpy(),
        "pressure": num(raw["pressure"]).to_numpy(),
        "max_wind_kt": num(raw["max_wind_kt"]).to_numpy(),
        "storm_diameter_nm": num(raw["storm_diameter_nm"]).to_numpy(),
        "gale_diameter_nm": num(raw["gale_diameter_nm"]).to_numpy(),
    })
    return validate_typhoon(df)


def _num(s: str, none_is_zero: bool = False) -> float:
    s = "" if s is None else str(s).strip()
    if s in _MISSING:
        return np.nan
    if s == "--":                      # 現象なし
        return 0.0 if none_is_zero else np.nan
    m = re.match(r"-?\d+(\.\d+)?", s)  # 末尾の ")" "]" などの品質記号は捨てる
    return float(m.group()) if m else np.nan


def _direction(s: str):
    s = "" if s is None else str(s).strip()
    return np.nan if s in _MISSING else s


def _parse_day_hour(s: str) -> pd.Timestamp:
    y, mo, d, h = map(int, _DAY_RE.match(s).groups())
    return pd.Timestamp(y, mo, d) + pd.Timedelta(hours=h)   # 24時 → 翌日 0 時


def build_weather() -> pd.DataFrame:
    with open(RAW_WEATHER, encoding="cp932", newline="") as f:
        rows = list(csv.reader(f))
    station_row = rows[2]
    data_rows = [r for r in rows[5:] if r and r[0].strip()]
    n_stations = (len(station_row) - 1) // 6
    stations = [station_row[1 + 6 * i] for i in range(n_stations)]
    times = [_parse_day_hour(r[0]) for r in data_rows]

    frames = []
    for i, name in enumerate(stations):
        b = 1 + 6 * i
        frames.append(pd.DataFrame({
            "station": name,
            "datetime": times,
            "temperature": [_num(r[b]) for r in data_rows],
            "precipitation": [_num(r[b + 1], none_is_zero=True) for r in data_rows],
            "wind_speed": [_num(r[b + 2]) for r in data_rows],
            "wind_direction": [_direction(r[b + 3]) for r in data_rows],
            "pressure": [_num(r[b + 4]) for r in data_rows],
            "weather_code": [_num(r[b + 5]) for r in data_rows],
        }))
    return validate_weather(pd.concat(frames, ignore_index=True))


def main() -> int:
    landfall = build_landfall()
    LANDFALL_CSV.parent.mkdir(parents=True, exist_ok=True)
    landfall.to_csv(LANDFALL_CSV, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d %H:%M:%S")
    print(f"landfall.csv: {len(landfall)} 行 → {LANDFALL_CSV}")

    weather = build_weather()
    print(f"weather: {len(weather)} 行, 地点 {sorted(set(weather['station']))}")
    for tid in TARGET_TYPHOONS:
        event = get_event(tid, landfall)
        start, end = event.fetch_window()
        lo, hi = pd.Timestamp(start), pd.Timestamp(end) + pd.Timedelta(days=1)
        for name in STATION_NAMES:
            sub = weather[(weather["station"] == name) & (weather["datetime"] >= lo) & (weather["datetime"] < hi)]
            if sub.empty:
                print(f"  {tid} {name}: 期間内データなし（スキップ）")
                continue
            write_cache(sub, cache_path(tid, name))
            print(f"  {tid} {name}: {len(sub)} 行 → {cache_path(tid, name).name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: 実行して生成物を確認する**

Run: `uv run python scripts/dev_sample_data.py && ls data/processed/typhoon data/processed/weather | head -30`
Expected: `landfall.csv: 258 行`、`weather: 8064 行`（42 日 × 24 時間 × 8 地点。多少前後してよい）、24 ファイル（`202508_福岡.csv` … `202515_那覇.csv`）が作られる。202508 は期間の前半（7/21〜7/26）が元データに無いので行数が少なめでよい

- [ ] **Step 3: AppTest スモークテストを書く**

`tests/test_app_smoke.py`:
```python
"""アプリ全体が例外なく描画できることの確認。data/processed が無ければスキップ。"""
import pytest
from streamlit.testing.v1 import AppTest

from typhoon_app.config import LANDFALL_CSV

pytestmark = pytest.mark.skipif(not LANDFALL_CSV.exists(), reason="data/processed/typhoon/landfall.csv が未整備")


def test_app_renders_without_exception():
    at = AppTest.from_file("app.py", default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    assert at.title[0].value.startswith("🌀 台風")
    assert len(at.tabs) == 3


def test_app_switching_typhoon_and_window():
    at = AppTest.from_file("app.py", default_timeout=120)
    at.run()
    at.selectbox[0].select("202512").run()
    at.slider[0].set_value(1).run()
    assert not at.exception, at.exception
```

- [ ] **Step 4: テストを実行する**

Run: `uv run pytest tests/test_app_smoke.py -q`
Expected: `2 passed`（landfall.csv が無い環境では `2 skipped`）

- [ ] **Step 5: ブラウザで目視確認する**

Run: `uv run streamlit run app.py`
Expected: 台風 第15号（2025）が既定で表示され、概要タブにサマリ表とランキング、時系列タブに気圧・風速・降水の 3 枚（赤い破線 2 本）、地図タブに 8 地点と赤い上陸点、サイドバーに「● キャッシュ済み」×8 が出る。台風を 第8号 に切り替えると欠測率が高め（期間前半が無いため）で表示される

- [ ] **Step 6: コミット**

```bash
git add scripts/dev_sample_data.py tests/test_app_smoke.py data/processed
git commit -m "Add dev sample data generator (temporary) and app smoke test"
```

---

### Task 14: scripts/build_cache.py（発表前のキャッシュ一括生成）

**Files:**
- Create: `scripts/build_cache.py`

**Interfaces:**
- Consumes: `config.STATION_NAMES`, `data.source.get_fetcher`, `data.typhoon.load_landfall, load_track, get_event`, `data.weather.get_station_weather`
- Produces: CLI `uv run python scripts/build_cache.py 202508 202512 202515`（終了コード 0=成功, 1=取得関数なし, 2=引数なし）

- [ ] **Step 1: スクリプトを書く**

`scripts/build_cache.py`:
```python
"""対象台風 × 全地点のキャッシュ CSV を事前生成する（設計書 §4-3 / §9）。

使い方: uv run python scripts/build_cache.py 202508 202512 202515
既にキャッシュがある地点はスキップ（status=cached）。データ側の fetch_weather が必要。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from typhoon_app.config import FETCHER_FUNCTION, FETCHER_MODULE, STATION_NAMES  # noqa: E402
from typhoon_app.data.source import get_fetcher  # noqa: E402
from typhoon_app.data.typhoon import get_event, load_landfall, load_track  # noqa: E402
from typhoon_app.data.weather import get_station_weather  # noqa: E402


def main(argv: list[str]) -> int:
    ids = argv[1:]
    if not ids:
        print("使い方: uv run python scripts/build_cache.py <台風番号> [<台風番号> ...]  例: 202512")
        return 2
    fetcher = get_fetcher()
    if fetcher is None:
        print(f"取得関数が見つかりません: {FETCHER_MODULE}.{FETCHER_FUNCTION}（データ担当の実装が必要）")
        return 1
    landfall = load_landfall()
    track = load_track()
    failed = 0
    for tid in ids:
        event = get_event(tid, landfall, track)
        print(f"== {event.label} 取得窓 {event.fetch_window()}")
        for name in STATION_NAMES:
            r = get_station_weather(tid, name, event.fetch_window(), fetcher)
            rows = len(r.df) if r.df is not None else 0
            print(f"  {name}: {r.status} {rows} 行 {r.message}")
            failed += r.status == "error"
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 2: 取得関数が無い状態での挙動を確認する**

Run: `uv run python scripts/build_cache.py 202512; echo "exit=$?"`
Expected: `取得関数が見つかりません: preprocess.weather_source.fetch_weather（データ担当の実装が必要）` と `exit=1`

Run: `uv run python scripts/build_cache.py; echo "exit=$?"`
Expected: 使い方が表示され `exit=2`

- [ ] **Step 3: コミット**

```bash
git add scripts/build_cache.py
git commit -m "Add build_cache script to pre-generate weather cache for target typhoons"
```

---

### Task 15: README と最終確認

**Files:**
- Modify: `README.md`（現在は空）, `requirements.txt`（依存が変わっていれば再生成）

- [ ] **Step 1: README.md を書く**

`README.md`:
```markdown
# Typhoon-Analyze

2025 年に九州・沖縄へ接近した台風について、8 地点（福岡・佐賀・長崎・熊本・大分・宮崎・鹿児島・那覇）の
気圧・風速・降水量・気温の時間変化を、台風の接近時刻と重ねて可視化する Streamlit アプリです。

## 起動方法（uv）

```bash
uv sync                         # 依存のインストール（初回のみ）
uv run streamlit run app.py     # http://localhost:8501
uv run pytest                   # テスト
```

## データの置き場所

アプリは `data/processed/` だけを読みます（設計書 §4 参照）。

| パス | 内容 | 必須 |
|---|---|---|
| `data/processed/typhoon/landfall.csv` | 台風の上陸/接近点 | 必須 |
| `data/processed/typhoon/track.csv` | 台風の全経路（あれば地図に線） | 任意 |
| `data/processed/station.csv` | 地点の緯度経度（無ければ内蔵値） | 任意 |
| `data/processed/weather/{台風番号}_{地点}.csv` | 気象データのキャッシュ | 無ければオンデマンド取得 |

- 開発用に手元の生データから仮の `data/processed/` を作る: `uv run python scripts/dev_sample_data.py`（暫定）
- 発表前にキャッシュを一括生成する: `uv run python scripts/build_cache.py 202508 202512 202515`
  （データ側の `preprocess/weather_source.py` の `fetch_weather(station, start, end)` が必要）

## ディレクトリ

- `app.py` — Streamlit の入口
- `typhoon_app/` — `data`（読込・データ契約）/ `analysis`（集計）/ `charts`（Plotly）/ `ui`（画面）
- `scripts/` — データ生成ユーティリティ
- `tests/` — pytest
- `docs/superpowers/specs/` — 設計書、`docs/superpowers/plans/` — 実装計画

## Streamlit Community Cloud へのデプロイ

GitHub リポジトリを連携し、メインファイルに `app.py` を指定します。`requirements.txt` は
`uv export --format requirements-txt --no-dev --no-hashes -o requirements.txt` で生成したものをコミットしてください。
```

- [ ] **Step 2: requirements.txt を再生成して差分を確認する**

Run: `uv export --format requirements-txt --no-dev --no-hashes -o requirements.txt && git diff --stat requirements.txt`
Expected: 依存が Task 1 から変わっていなければ差分なし

- [ ] **Step 3: 全テストと起動確認**

Run: `uv run pytest -q`
Expected: 全件 PASS（AppTest 含む）

Run: `uv run streamlit run app.py`
Expected: Task 13 Step 5 と同じ画面が出る

- [ ] **Step 4: コミット**

```bash
git add README.md requirements.txt
git commit -m "Add README with setup, data layout, and deploy notes"
```

---

## データ担当への連絡（実装と並行して）

spec §10 のとおり。特に次の 2 点が揃うとこの計画の「暫定」部分が不要になる:
1. `preprocess/weather_source.py` に `fetch_weather(station: str, start: date, end: date) -> pd.DataFrame`（spec §4-2 のスキーマ）を実装 → `scripts/build_cache.py` が動く
2. `data/processed/typhoon/landfall.csv`（必要なら `track.csv`）を spec §4-4 の形で配置 → `scripts/dev_sample_data.py` が不要になる
