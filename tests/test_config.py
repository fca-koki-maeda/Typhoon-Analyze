from typhoon_app import config


def test_default_stations_are_eight_kyushu_okinawa_points():
    names = [s.name for s in config.DEFAULT_STATIONS]
    assert names == ["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "那覇"]
    assert config.STATION_NAMES == names
    for s in config.DEFAULT_STATIONS:
        assert 24 < s.lat < 35 and 126 < s.lon < 133
    by_name = {s.name: s for s in config.DEFAULT_STATIONS}
    assert by_name["大分"].block_no == 47815   # 旧値 47624 は前橋（回帰防止）


def test_variables_and_windows():
    assert set(config.VARIABLES) == {"pressure", "wind_speed", "precipitation", "temperature"}
    assert config.VARIABLES["precipitation"].kind == "bar"
    assert config.VARIABLES["pressure"].agg == "min"
    assert config.WINDOW_DAYS == 1
