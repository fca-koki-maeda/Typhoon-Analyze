"""アプリ全体が例外なく描画できることの確認。data/processed が無ければスキップ。"""
import pytest
from streamlit.testing.v1 import AppTest

from typhoon_app.config import PROJECT_ROOT, TRACK_CSV

APP_PATH = str(PROJECT_ROOT / "app.py")   # AppTest.from_file はテストファイル基準で解決するため絶対パスにする

pytestmark = pytest.mark.skipif(not TRACK_CSV.exists(), reason="data/processed/typhoon/track.csv が未整備")


def test_app_renders_without_exception():
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    assert at.title[0].value.startswith("🌀 台風")
    assert len(at.tabs) == 3


def test_app_switching_typhoon():
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    at.run()
    at.selectbox[0].select("202512").run()
    assert not at.exception, at.exception


def test_app_no_cache_typhoon_shows_warning_not_exception():
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    at.run()
    at.selectbox[0].select("202505").run()   # 2025年 第5号: キャッシュ無し
    assert not at.exception, at.exception
    assert any("未取得" in w.value or "取得できません" in w.value for w in at.warning)


def test_app_no_stations_selected_stops_with_info():
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    at.run()
    at.multiselect[0].set_value([]).run()   # 地点を全解除
    assert not at.exception, at.exception
    assert any("地点" in i.value for i in at.info)
