"""対象台風 × 内蔵 8 地点（config.STATION_NAMES）のキャッシュ CSV を事前生成する（設計書 §4-3 / §9）。

使い方: uv run python scripts/build_cache.py 202508 202512 202515
既にキャッシュがある地点はスキップ（status=cached）。データ側の fetch_weather が必要。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from typhoon_app.config import FETCHER_FUNCTION, FETCHER_MODULE, STATION_NAMES  # noqa: E402
from typhoon_app.data.source import get_fetcher  # noqa: E402
from typhoon_app.data.typhoon import get_event, load_track  # noqa: E402
from typhoon_app.data.weather import get_station_weather  # noqa: E402


def main(argv: list[str]) -> int:
    ids = argv[1:]
    if not ids:
        print("使い方: uv run python scripts/build_cache.py <台風番号> [<台風番号> ...]  例: 202512")
        return 2
    fetcher = get_fetcher()
    if fetcher is None:
        print(f"取得関数が見つかりません: {FETCHER_MODULE}.{FETCHER_FUNCTION}（データ担当の実装が必要）")
        return 1
    track = load_track()
    failed = 0
    for tid in ids:
        event = get_event(tid, track)
        print(f"== {event.label} 取得窓 {event.fetch_window()}")
        for name in STATION_NAMES:
            r = get_station_weather(tid, name, event.fetch_window(), fetcher)
            rows = len(r.df) if r.df is not None else 0
            print(f"  {name}: {r.status} {rows} 行 {r.message}")
            failed += r.status == "error"
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
