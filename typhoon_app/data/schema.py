"""データ契約（設計書 §4-2 / §4-4）の検証と型変換。"""
from __future__ import annotations

import pandas as pd


class SchemaError(ValueError):
    """データ契約に合わないときに送出する。メッセージにカラム名を含める。"""


WEATHER_COLUMNS: dict[str, str] = {
    "station": "string",
    "datetime": "datetime",
    "temperature": "float",
    "precipitation": "float",
    "wind_speed": "float",
    "wind_direction": "string",
    "pressure": "float",
    "weather_code": "int",
}

TYPHOON_COLUMNS: dict[str, str] = {
    "typhoon_id": "string",
    "datetime": "datetime",
    "lat": "float",
    "lon": "float",
    "pressure": "float",
    "max_wind_kt": "float",
    "storm_diameter_nm": "float",
    "gale_diameter_nm": "float",
}


def _coerce(df: pd.DataFrame, spec: dict[str, str], name: str) -> pd.DataFrame:
    missing = [c for c in spec if c not in df.columns]
    if missing:
        raise SchemaError(f"{name}: 欠けているカラム: {missing}")

    out = df.copy()
    problems: list[str] = []
    for col, kind in spec.items():
        src = out[col]
        if kind == "string":
            out[col] = src.astype("string")
            continue
        if kind == "datetime":
            coerced = pd.to_datetime(src, errors="coerce")
        else:
            coerced = pd.to_numeric(src, errors="coerce")
            if kind == "int":
                try:
                    coerced = coerced.astype("Int64")
                except (TypeError, ValueError):
                    problems.append(f"{col}: 整数でない値があります")
            else:
                coerced = coerced.astype("float64")
        # 元は値があるのに変換後 NaN になったセル = 解釈できない値
        nonblank = src.notna() & (src.astype("string").str.strip() != "")
        bad = coerced.isna() & nonblank.fillna(False)
        if bad.any():
            problems.append(f"{col}={src[bad].iloc[0]!r}")
        out[col] = coerced

    if problems:
        raise SchemaError(f"{name}: 解釈できない値があります: " + ", ".join(problems))
    return out


def validate_weather(df: pd.DataFrame) -> pd.DataFrame:
    """気象データ（tidy）を検証し、型変換して station, datetime 昇順で返す。"""
    out = _coerce(df, WEATHER_COLUMNS, "weather")
    return out.sort_values(["station", "datetime"]).reset_index(drop=True)


def validate_typhoon(df: pd.DataFrame) -> pd.DataFrame:
    """台風データ（landfall / track 共通）を検証し、typhoon_id, datetime 昇順で返す。"""
    out = _coerce(df, TYPHOON_COLUMNS, "typhoon")
    return out.sort_values(["typhoon_id", "datetime"]).reset_index(drop=True)
