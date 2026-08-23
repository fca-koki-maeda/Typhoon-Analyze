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
