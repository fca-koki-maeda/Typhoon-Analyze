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
