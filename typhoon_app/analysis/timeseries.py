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
