from pathlib import Path

import pytest

from typhoon_app.data.schema import SchemaError
from typhoon_app.data.station import haversine_km, load_stations, nearest_station


def test_load_stations_defaults_when_file_missing(tmp_path):
    stations = load_stations(tmp_path / "station.csv")
    assert len(stations) == 8
    assert stations["福岡"].block_no == 47807


def test_load_stations_overrides_from_csv(tmp_path):
    p = tmp_path / "station.csv"
    p.write_text("station,lat,lon,prec_no,block_no\n福岡,33.6,130.4,82,47807\n", encoding="utf-8")
    stations = load_stations(p)
    assert stations["福岡"].lat == 33.6
    assert len(stations) == 8   # 他の地点は既定のまま


def test_load_stations_rejects_bad_columns(tmp_path):
    p = tmp_path / "station.csv"
    p.write_text("name,lat,lon\n福岡,33.6,130.4\n", encoding="utf-8")
    with pytest.raises(SchemaError, match="station"):
        load_stations(p)


def test_load_stations_rejects_non_numeric_cells(tmp_path):
    p = tmp_path / "station.csv"
    p.write_text("station,lat,lon,prec_no,block_no\n福岡,abc,130.4,82,47807\n", encoding="utf-8")
    with pytest.raises(SchemaError, match="station.csv"):
        load_stations(p)


def test_haversine_fukuoka_kagoshima():
    d = haversine_km(33.582, 130.375, 31.555, 130.547)
    assert 200 < d < 250


def test_nearest_station():
    stations = load_stations(Path("/nonexistent/station.csv"))
    assert nearest_station(31.6, 130.3, stations).name == "鹿児島"
    assert nearest_station(26.6, 128.0, stations).name == "那覇"
