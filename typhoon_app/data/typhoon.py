"""台風データ（設計書 §4-4）の読込と、台風 1 個ぶんの情報をまとめる TyphoonEvent。
台風データは 1 時間ごと程度の track 1 本（必須）。最接近時刻の特定は行わない。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from typhoon_app.config import TRACK_CSV, WINDOW_DAYS
from typhoon_app.data.schema import validate_typhoon


@dataclass(frozen=True)
class TyphoonEvent:
    typhoon_id: str
    track: pd.DataFrame  # この台風の経路（datetime 昇順・1 行以上）

    @property
    def year(self) -> int:
        return int(self.typhoon_id[:4])

    @property
    def number(self) -> int:
        return int(self.typhoon_id[4:])

    @property
    def first_time(self) -> pd.Timestamp:
        return pd.Timestamp(self.track["datetime"].iloc[0])

    @property
    def last_time(self) -> pd.Timestamp:
        return pd.Timestamp(self.track["datetime"].iloc[-1])

    @property
    def period(self) -> tuple[pd.Timestamp, pd.Timestamp]:
        """台風データが存在する期間（時系列グラフの帯に使う）。"""
        return self.first_time, self.last_time

    @property
    def label(self) -> str:
        f, l = self.first_time, self.last_time
        if (f.month, f.day) == (l.month, l.day):
            return f"{self.year}年 第{self.number}号（{f.month}/{f.day}）"
        return f"{self.year}年 第{self.number}号（{f.month}/{f.day}〜{l.month}/{l.day}）"

    @property
    def center_pressure(self) -> float:
        return float(self.track["pressure"].min())

    @property
    def max_wind_kt(self) -> float:
        return float(self.track["max_wind_kt"].max())

    def fetch_window(self, days: int = WINDOW_DAYS) -> tuple[date, date]:
        """データ取得に使う日付範囲（両端含む）。台風期間の前後 days 日。"""
        return (
            (self.first_time - pd.Timedelta(days=days)).date(),
            (self.last_time + pd.Timedelta(days=days)).date(),
        )

    def display_window(self, days: int = WINDOW_DAYS) -> tuple[pd.Timestamp, pd.Timestamp]:
        """画面に表示する時刻範囲。"""
        return (
            self.first_time - pd.Timedelta(days=days),
            self.last_time + pd.Timedelta(days=days),
        )


def load_track(path: Path = TRACK_CSV) -> pd.DataFrame:
    """台風の経路データ。必須データなので無ければ FileNotFoundError。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"台風データがありません: {path}")
    df = pd.read_csv(path, encoding="utf-8-sig", dtype={"typhoon_id": str})
    return validate_typhoon(df)


def get_event(typhoon_id: str, track: pd.DataFrame) -> TyphoonEvent:
    rows = track[track["typhoon_id"] == typhoon_id]
    if rows.empty:
        raise KeyError(f"台風 {typhoon_id} は track データにありません")
    return TyphoonEvent(typhoon_id, rows.sort_values("datetime").reset_index(drop=True))


def list_typhoons(track: pd.DataFrame) -> list[TyphoonEvent]:
    """track にある台風をすべて TyphoonEvent にして、新しい順に返す。"""
    events = [get_event(str(tid), track) for tid in track["typhoon_id"].unique()]
    return sorted(events, key=lambda e: e.first_time, reverse=True)
