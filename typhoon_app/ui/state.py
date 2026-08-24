"""サイドバーの選択状態。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Selection:
    typhoon_id: str
    stations: tuple[str, ...]
    variables: tuple[str, ...]
