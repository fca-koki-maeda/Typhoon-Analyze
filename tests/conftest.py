from pathlib import Path

import pandas as pd
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def weather_raw() -> pd.DataFrame:
    """CSV をそのまま読んだ、検証前の気象データ。"""
    return pd.read_csv(FIXTURES / "weather_small.csv", encoding="utf-8-sig")


@pytest.fixture
def weather_df(weather_raw) -> pd.DataFrame:
    """検証済み（型変換済み）の気象データ。"""
    from typhoon_app.data.schema import validate_weather

    return validate_weather(weather_raw)


@pytest.fixture
def landfall_df() -> pd.DataFrame:
    from typhoon_app.data.typhoon import load_landfall

    return load_landfall(FIXTURES / "landfall_small.csv")


@pytest.fixture
def track_df() -> pd.DataFrame:
    from typhoon_app.data.typhoon import load_track

    return load_track(FIXTURES / "track_small.csv")
