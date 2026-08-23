"""アプリ全体が例外なく描画できることの確認。data/processed が無ければスキップ。"""
import pytest
from streamlit.testing.v1 import AppTest

from typhoon_app.config import LANDFALL_CSV, PROJECT_ROOT

APP_PATH = str(PROJECT_ROOT / "app.py")   # AppTest.from_file はテストファイル基準で解決するため絶対パスにする

pytestmark = pytest.mark.skipif(not LANDFALL_CSV.exists(), reason="data/processed/typhoon/landfall.csv が未整備")


def test_app_renders_without_exception():
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    assert at.title[0].value.startswith("🌀 台風")
    assert len(at.tabs) == 3


def test_app_switching_typhoon_and_window():
    at = AppTest.from_file(APP_PATH, default_timeout=120)
    at.run()
    at.selectbox[0].select("202512").run()
    at.slider[0].set_value(1).run()
    assert not at.exception, at.exception
