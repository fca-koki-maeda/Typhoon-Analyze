"""scripts/build_station_master.py のパーサのテスト（フィクスチャ使用・通信なし）。"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_station_master import extract_prec_nos, extract_stations  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_prec_nos():
    prec_nos = extract_prec_nos((FIXTURES / "jma_select_pref00.html").read_text(encoding="utf-8", errors="ignore"))
    assert len(prec_nos) == 61
    assert prec_nos[0] == 11
    assert 82 in prec_nos


def test_extract_stations_fukuoka():
    stations = extract_stations((FIXTURES / "jma_select_pref82.html").read_text(encoding="utf-8", errors="ignore"), 82)
    by_name = {s["station"]: s for s in stations}
    assert set(by_name) == {"福岡", "飯塚"}
    f = by_name["福岡"]
    assert f["block_no"] == 47807 and f["prec_no"] == 82
    assert f["lat"] == pytest.approx(33.5817, abs=1e-3)
    assert f["lon"] == pytest.approx(130.375, abs=1e-3)
