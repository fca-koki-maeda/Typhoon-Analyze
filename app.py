"""Typhoon-Analyze: 台風接近時の九州・沖縄 8 地点の気象変化を可視化する Streamlit アプリ。
ここは配線だけ。ロジックは typhoon_app/ 配下にある。"""
from __future__ import annotations

import streamlit as st

from typhoon_app.analysis.summary import summarize
from typhoon_app.analysis.timeseries import clip
from typhoon_app.data.schema import SchemaError
from typhoon_app.data.source import get_fetcher
from typhoon_app.data.station import nearest_station
from typhoon_app.data.typhoon import get_event, list_typhoons
from typhoon_app.data.weather import StationResult, cache_path, combine, get_station_weather
from typhoon_app.ui.glossary import render_glossary
from typhoon_app.ui.header import render_header
from typhoon_app.ui.loaders import load_landfall_cached, load_stations_cached, load_track_cached
from typhoon_app.ui.sidebar import render_data_status, render_sidebar
from typhoon_app.ui.tab_map import render_map
from typhoon_app.ui.tab_overview import render_overview
from typhoon_app.ui.tab_timeseries import render_timeseries


def main() -> None:
    st.set_page_config(page_title="台風と九州・沖縄の気象", page_icon="🌀", layout="wide")

    # 必須データ（無い／形式が違うときはメッセージを出して停止: 設計書 §7）
    try:
        landfall = load_landfall_cached()
        track = load_track_cached()
        stations = load_stations_cached()
    except FileNotFoundError as e:
        st.error(f"台風データがありません。data/processed/typhoon/landfall.csv を置いてください。\n\n{e}")
        st.stop()
    except SchemaError as e:
        st.error(f"データの形式が設計書 §4 と違います（データ担当に共有してください）。\n\n{e}")
        st.stop()
    events = list_typhoons(landfall, track)

    # 条件選択
    selection = render_sidebar(events, list(stations))
    event = get_event(selection.typhoon_id, landfall, track)

    # 気象データ（キャッシュ → 無ければオンデマンド取得）
    fetcher = get_fetcher()
    results: dict[str, StationResult] = {}
    for name in selection.stations:
        if cache_path(event.typhoon_id, name).exists():
            results[name] = get_station_weather(event.typhoon_id, name, event.fetch_window(), fetcher)
        else:
            with st.spinner(f"{name}: 気象庁から取得中…"):
                results[name] = get_station_weather(event.typhoon_id, name, event.fetch_window(), fetcher)
    render_data_status(results, fetcher is not None)
    render_glossary()

    # ヘッダ
    nearest = nearest_station(event.landfall_lat, event.landfall_lon, stations)
    render_header(event, nearest.name)

    if not selection.stations:
        st.info("サイドバーで地点を 1 つ以上選んでください。")
        st.stop()

    window = event.display_window(selection.window_days)
    df = clip(combine(results), *window)
    summary = summarize(df)

    tab_overview, tab_timeseries, tab_map = st.tabs(["概要", "時系列", "地図"])
    with tab_overview:
        render_overview(summary, selection.variables)
    with tab_timeseries:
        render_timeseries(df, selection.variables, event.reference_times, list(selection.stations))
    with tab_map:
        render_map(df, {n: stations[n] for n in selection.stations if n in stations}, event, selection.variables, window)


if __name__ == "__main__":
    main()
