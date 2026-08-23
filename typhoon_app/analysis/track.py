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
