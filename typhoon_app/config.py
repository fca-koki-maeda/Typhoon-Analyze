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
