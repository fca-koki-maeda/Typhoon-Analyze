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
