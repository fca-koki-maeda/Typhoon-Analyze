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
