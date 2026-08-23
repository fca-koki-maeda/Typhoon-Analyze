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
