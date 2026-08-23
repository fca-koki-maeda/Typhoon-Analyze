# Typhoon-Analyze

2025 年に九州・沖縄へ接近した台風について、8 地点（福岡・佐賀・長崎・熊本・大分・宮崎・鹿児島・那覇）の
気圧・風速・降水量・気温の時間変化を、台風の接近時刻と重ねて可視化する Streamlit アプリです。

## 起動方法（uv）

```bash
uv sync                         # 依存のインストール（初回のみ）
uv run streamlit run app.py     # http://localhost:8501
uv run pytest                   # テスト
```

## データの置き場所

アプリは `data/processed/` だけを読みます（設計書 §4 参照）。

| パス | 内容 | 必須 |
|---|---|---|
| `data/processed/typhoon/landfall.csv` | 台風の上陸/接近点 | 必須 |
| `data/processed/typhoon/track.csv` | 台風の全経路（あれば地図に線） | 任意 |
| `data/processed/station.csv` | 地点の緯度経度（無ければ内蔵値） | 任意 |
| `data/processed/weather/{台風番号}_{地点}.csv` | 気象データのキャッシュ | 無ければオンデマンド取得 |

- 開発用に手元の生データから仮の `data/processed/` を作る: `uv run python scripts/dev_sample_data.py`（暫定）
- 発表前にキャッシュを一括生成する: `uv run python scripts/build_cache.py 202508 202512 202515`
  （データ側の `preprocess/weather_source.py` の `fetch_weather(station, start, end)` が必要）

## ディレクトリ

- `app.py` — Streamlit の入口
- `typhoon_app/` — `data`（読込・データ契約）/ `analysis`（集計）/ `charts`（Plotly）/ `ui`（画面）
- `scripts/` — データ生成ユーティリティ
- `tests/` — pytest
- `docs/superpowers/specs/` — 設計書、`docs/superpowers/plans/` — 実装計画

## Streamlit Community Cloud へのデプロイ

GitHub リポジトリを連携し、メインファイルに `app.py` を指定します。`requirements.txt` は
`uv export --format requirements-txt --no-dev --no-hashes -o requirements.txt` で生成したものをコミットしてください。
Advanced settings で Python 3.12 を選んでください（pandas 3 系は Python 3.11 以上が必要。.python-version は Cloud では読まれません）。
