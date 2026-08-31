# Typhoon-Analyze

2025 年に九州・沖縄へ接近した台風について、8 地点（福岡・佐賀・長崎・熊本・大分・宮崎・鹿児島・那覇）の
気圧・風速・降水量・気温の時間変化を、台風の接近期間と重ねて可視化する Streamlit アプリです。

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
| `data/processed/typhoon/track.csv` | 台風の経路（`data/typhoon/typhoon_track.csv` から変換） | 必須 |
| `data/processed/station.csv` | 全国の気象官署一覧（`scripts/build_station_master.py` で生成・同梱済み） | 任意（無ければ内蔵 8 地点） |
| `data/processed/weather/{台風番号}_{地点}.csv` | 気象データのキャッシュ | 無ければオンデマンド取得 |

- `data/processed/` を生データから生成する: `uv run python scripts/dev_sample_data.py`（台風データはこれが正式ルート。気象キャッシュは `fetch_weather` 完成までの暫定）
- 発表前にキャッシュを一括生成する: `uv run python scripts/build_cache.py 202508 202512 202515`
  （`preprocess/weather_source.py` の `fetch_weather` を使用。実装済み）
- 地点マスタの再生成: `uv run python scripts/build_station_master.py`

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

## 開発概要

背景  
台風の接近時には、天気の変化・気圧の低下・風速の増加・降水量の急増など、気象要素に特徴的な変化が現れる。  
気象庁は過去の観測データをCSV形式で公開しており、これを活用することで台風接近前後の気象変化を定量的に分析できる。  
また、過去の台風接近・上陸等の情報はデジタル台風のHP上で確認できる。  
  
目的  
気象庁の過去観測データとデジタル台風の台風情報を組み合わせ、台風接近時に各気象要素(天気・気圧・風速・降水量など)がどのように変化するかを可視化・分析するWebアプリケーションを開発する。  
  
ゴール例  
・台風接近の何時間前から気圧は下がり始めるか  
・台風の中心距離と風速・降水量にはどのような関係があるか  
・台風ごと・地点ごとに気象変化のパターンに違いはあるか  
  
システム概要  
WEBアプリ、Python、ブラウザ閲覧  
  
取得するデータ  
天気情報：自動取得  
台風情報：デジタル台風サイトより進路図も同時に取得  

これが過去の台風上陸・接近データ一覧（typhoon_track.csv）  
https://agora.ex.nii.ac.jp/cgi-bin/dt/lfjp.pl?lang=ja&basin=wnp&sort=time&order=dec&stype=char  
左側の台風番号にアクセスすると詳細ベストラック（進路図）の画像を取得できる。  
  
===================  
  
流れ  
  
STEP1  
デジタル台風CSV取得  

STEP2  
気象庁CSVデータ取得ロジック作成  
  
STEP3  
ディレクトリ作成  
  
STEP4  
取得したCSVを整理するロジック  
例えば、以下の形のように必要なデータのみを整理する  
datetime	station	temperature	pressure	wind	rain  
2025/9/5 1:00	福岡	27.7		1005.9		1.9	0  
2025/9/5 2:00	福岡	27.7		1005.8		1.2	0  
  
STEP5  
デジタル台風データを整理  
2025年09月05日16時00分(JST)→→→2025-09-05 16:00  
列名を typhoon_no, datetime, lat, lon, pressure, wind, rain などの扱いやすい形にする  
  
STEP6  
観測所座標を作る  
station.csv 
station	緯度	経度  
福岡	33.58	130.38  
佐賀	33.27	130.30  
長崎	32.75	129.87  
熊本	32.81	130.71  
大分	33.24	131.61  
宮崎	31.94	131.42   
鹿児島	31.56	130.56  
那覇	26.21	127.68   
  
STEP7  
距離計算  
台風の緯度経度が33.0/132.0→→→全観測所との距離を計算→→→一番近い観測所を求める  
  
STEP8  
データの結び付け  
ユーザーが「台風番号」「観測所」を選択  
（台風番号はtyphoon_track.csvに入っているものしかプルダウンに表示させない）  
↓  
該当する台風番号からデータ取得  
台風日時と位置を取得  
同時に進路図も取得  
（台風番号が202515なら、https://agora.ex.nii.ac.jp/digital-typhoon/summary/wnp/l/202515.html.ja）  
↓  
宮崎を選択しているなら  
↓  
weather_all.csv  
station=宮崎  
datetime=9/5 1:00  
  
STEP9  
グラフを3つ以上作成  
表示するグラフを選択できる  
横軸：時間・台風までの距離を表示  
縦軸：気圧／風速／降水量などでグラフを複数作成  
  
STEP10  
StreamlitでWEBアプリ作成  
  
STEP11（発展）  
分析結果を自動でまとめるAI  
「最も気圧が低下したのは接近○時間前」  
「最大風速は最接近時刻の○時間後に観測された」  
「降水量は通過後にピークとなった」  
といったコメントを自動生成する  
単なる可視化ツールではなく分析支援アプリになる  
