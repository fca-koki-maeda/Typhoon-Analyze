"""動作確認用 CLI: 指定地点・期間の時別値を取得して CSV に保存する。

取得ロジック本体は preprocess/weather_source.py の fetch_weather に移動した。
使い方: uv run python scraper/jma_scraper.py 福岡 2025-07-27 2025-07-28
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from preprocess.weather_source import WeatherFetchError, fetch_weather  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("使い方: uv run python scraper/jma_scraper.py <地点名> <開始日 YYYY-MM-DD> <終了日 YYYY-MM-DD>")
        return 2
    station, start_s, end_s = argv[1], argv[2], argv[3]
    start, end = date.fromisoformat(start_s), date.fromisoformat(end_s)
    try:
        df = fetch_weather(station, start, end)
    except WeatherFetchError as e:
        print(f"取得に失敗しました: {e}")
        return 1
    out = ROOT / "data" / "weather" / f"{station}_{start}_{end}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d %H:%M:%S")
    print(f"{len(df)} 行 → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
