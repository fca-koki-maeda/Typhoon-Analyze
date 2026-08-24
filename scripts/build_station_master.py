"""気象庁の観測所選択ページから全国の気象官署一覧を作り、data/processed/station.csv に保存する。

対象は気象官署（viewPoint の種別 's'）のみ。アメダスは対象外。
リクエストは 都道府県一覧 1 回 + 都道府県ごと 61 回（間隔 1 秒）。
使い方: uv run python scripts/build_station_master.py
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from typhoon_app.config import STATION_CSV  # noqa: E402

INDEX_URL = "https://www.data.jma.go.jp/stats/etrn/select/prefecture00.php"
PREF_URL = "https://www.data.jma.go.jp/stats/etrn/select/prefecture.php"
REQUEST_INTERVAL_SECONDS = 1.0
TIMEOUT_SECONDS = 30

_PREC_RE = re.compile(r"prefecture\.php\?prec_no=(\d+)")
_STATION_RE = re.compile(
    r"viewPoint\('s','(\d{5})','([^']+)','[^']*','(\d+)','([\d.]+)','(\d+)','([\d.]+)'"
)


def extract_prec_nos(html: str) -> list[int]:
    return sorted({int(m) for m in _PREC_RE.findall(html)})


def extract_stations(html: str, prec_no: int) -> list[dict]:
    """1 都道府県ページから気象官署を抜き出す（ページ内の重複は block_no で除去）。"""
    seen: dict[int, dict] = {}
    for block_no, name, lat_d, lat_m, lon_d, lon_m in _STATION_RE.findall(html):
        seen.setdefault(int(block_no), {
            "station": name,
            "lat": round(int(lat_d) + float(lat_m) / 60, 4),
            "lon": round(int(lon_d) + float(lon_m) / 60, 4),
            "prec_no": prec_no,
            "block_no": int(block_no),
        })
    return list(seen.values())


def main() -> int:
    index = requests.get(INDEX_URL, timeout=TIMEOUT_SECONDS)
    index.raise_for_status()
    prec_nos = extract_prec_nos(index.text)
    print(f"都道府県ページ: {len(prec_nos)} 件")

    rows: list[dict] = []
    for i, prec_no in enumerate(prec_nos):
        time.sleep(REQUEST_INTERVAL_SECONDS)
        res = requests.get(PREF_URL, params={"prec_no": prec_no}, timeout=TIMEOUT_SECONDS)
        res.raise_for_status()
        found = extract_stations(res.text, prec_no)
        rows.extend(found)
        print(f"[{i + 1}/{len(prec_nos)}] prec_no={prec_no}: {len(found)} 地点")

    df = pd.DataFrame(rows, columns=["station", "lat", "lon", "prec_no", "block_no"])
    df = df.drop_duplicates(subset="block_no")
    dup_names = df[df["station"].duplicated(keep=False)]
    if not dup_names.empty:
        print("警告: 同名の地点があります（先勝ちで残します）:")
        print(dup_names.sort_values("station").to_string(index=False))
        df = df.drop_duplicates(subset="station")
    df = df.sort_values(["prec_no", "block_no"]).reset_index(drop=True)
    STATION_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(STATION_CSV, index=False, encoding="utf-8-sig")
    print(f"{len(df)} 地点 → {STATION_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
