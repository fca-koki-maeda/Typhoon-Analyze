"""地点ランキングの横棒グラフ（設計書 §3 概要タブ）。"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from typhoon_app.charts.common import empty_figure


def ranking_chart(summary: pd.DataFrame, column: str, title: str, unit: str, ascending: bool) -> go.Figure:
    """summary[column] で地点を並べた横棒グラフ。上が 1 位。"""
    data = summary.dropna(subset=[column]).sort_values(column, ascending=ascending)
    if data.empty:
        return empty_figure(title)
    data = data.assign(station=data["station"].astype(str))
    fig = px.bar(data, x=column, y="station", orientation="h", text=column)
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(
        title=title,
        xaxis_title=f"{title}（{unit}）",
        yaxis_title="地点",
        yaxis=dict(autorange="reversed"),   # 並び順の先頭を上に
        margin=dict(l=40, r=20, t=50, b=40),
        showlegend=False,
    )
    return fig
