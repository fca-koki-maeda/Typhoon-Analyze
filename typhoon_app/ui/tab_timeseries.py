"""時系列タブ: 要素ごとに 1 枚のグラフ（設計書 §3）。"""
from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import streamlit as st

from typhoon_app.charts.timeseries import variable_chart
from typhoon_app.config import VARIABLES


def render_timeseries(
    df: pd.DataFrame, variables: Sequence[str], period: tuple, station_order: Sequence[str]
) -> None:
    if df.empty:
        st.info("表示できるデータがありません。")
        return
    if not variables:
        st.info("サイドバーで気象要素を 1 つ以上選んでください。")
        return
    for key in variables:
        st.plotly_chart(variable_chart(df, VARIABLES[key], period, station_order), width="stretch")
