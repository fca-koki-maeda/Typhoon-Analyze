"""気象庁「過去の気象データ検索」時別値ページから気象データを取得する（設計書 §4-1 / §4-2）。

scraper/jma_scraper.py の取得ロジックを関数化し、データ契約（6 列）に合わせたもの。
アプリからは typhoon_app.data.source.get_fetcher() 経由で呼ばれる。
"""
from __future__ import annotations

import re
import time
from datetime import date, timedelta

import pandas as pd
import requests
from bs4 import BeautifulSoup

from typhoon_app.data.station import load_stations

BASE_URL = "https://www.data.jma.go.jp/stats/etrn/view/hourly_s1.php"
REQUEST_INTERVAL_SECONDS = 1.0  # 連続アクセスの間隔（マナー）
TIMEOUT_SECONDS = 30

WEATHER_COLUMNS = ["station", "datetime", "temperature", "precipitation", "wind_speed", "pressure"]


class WeatherFetchError(Exception):
    """取得・解析に失敗したときに送出する。"""


def _num(text: str | None, none_is_zero: bool = False) -> float:
    """観測値の文字列を float にする。'--' は現象なし（降水量のみ 0.0）、記号・空欄は欠測（NaN）。
    '25.5)' のような品質記号付きは数値部分のみ採用する。"""
    s = ("" if text is None else str(text)).strip()
    if s == "--":
        return 0.0 if none_is_zero else float("nan")
    if s in ("", "×", "///", "#"):
        return float("nan")
    m = re.match(r"-?\d+(\.\d+)?", s)
    return float(m.group()) if m else float("nan")


def _parse_day(html: bytes, day: date, station: str) -> list[dict]:
    """1 日ぶんのページからデータ行を取り出す。列: 0=時, 1=現地気圧, 3=降水量, 4=気温, 8=風速。"""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"class": "data2_s"})
    if table is None:
        raise WeatherFetchError(f"{station} {day}: データ表が見つかりません（ページ構造が変わった可能性があります）")
    rows: list[dict] = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 9:
            continue
        hour_text = tds[0].get_text(strip=True)
        if not hour_text.isdigit():
            continue
        rows.append({
            "station": station,
            "datetime": pd.Timestamp(day) + pd.Timedelta(hours=int(hour_text)),  # 24 時 → 翌日 0 時
            "temperature": _num(tds[4].get_text(strip=True)),
            "precipitation": _num(tds[3].get_text(strip=True), none_is_zero=True),
            "wind_speed": _num(tds[8].get_text(strip=True)),
            "pressure": _num(tds[1].get_text(strip=True)),
        })
    return rows


def fetch_weather(station: str, start: date, end: date) -> pd.DataFrame:
    """指定地点・期間（両端の日を含む）の時別値を取得し、データ契約（6 列）の DataFrame を返す。
    失敗したら WeatherFetchError を送出する。リクエスト間に REQUEST_INTERVAL_SECONDS 待つ。"""
    stations = load_stations()
    if station not in stations:
        raise WeatherFetchError(f"未対応の観測地点です: {station}")
    prec_no, block_no = stations[station].prec_no, stations[station].block_no
    records: list[dict] = []
    day = start
    while day <= end:
        params = {
            "prec_no": prec_no, "block_no": block_no,
            "year": day.year, "month": day.month, "day": day.day, "view": "",
        }
        try:
            res = requests.get(BASE_URL, params=params, timeout=TIMEOUT_SECONDS)
            res.raise_for_status()
        except requests.RequestException as e:
            raise WeatherFetchError(f"{station} {day}: 気象庁サイトから取得できません: {e}") from e
        records.extend(_parse_day(res.content, day, station))
        day += timedelta(days=1)
        if day <= end:
            time.sleep(REQUEST_INTERVAL_SECONDS)
    return pd.DataFrame(records, columns=WEATHER_COLUMNS)
