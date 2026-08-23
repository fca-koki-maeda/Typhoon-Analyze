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
