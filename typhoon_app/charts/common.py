"""グラフ共通部品。"""
from __future__ import annotations

import plotly.graph_objects as go


def empty_figure(title: str) -> go.Figure:
    """データが無いときに出す空の Figure。"""
    fig = go.Figure()
    fig.update_layout(
        title=title,
        annotations=[dict(text="データなし", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)],
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig
