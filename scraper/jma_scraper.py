# -*- coding: utf-8 -*-
import os
import datetime
import csv
import urllib.request
from bs4 import BeautifulSoup

STATIONS = {
    "福岡":     {"prec_no": 82, "block_no": 47807},
    "佐賀":     {"prec_no": 85, "block_no": 47813},
    "長崎":     {"prec_no": 84, "block_no": 47817},
    "熊本":     {"prec_no": 86, "block_no": 47819},
    "大分":     {"prec_no": 83, "block_no": 47624},
    "宮崎":     {"prec_no": 87, "block_no": 47830},
    "鹿児島":   {"prec_no": 88, "block_no": 47827},
    "那覇":     {"prec_no": 91, "block_no": 47936},
}

def str2float(weather_data):
    try:
        return float(weather_data)
    except:
        return 0

def scraping(url, date):

    # 気象データのページを取得
    html = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table", {"class": "data2_s"})

    # ヘッダー
    headers = []

    # データ
    data_list_per_hour = []

    trs = table.find_all("tr")

    # -------------------------
    # ヘッダー取得
    # -------------------------
    header_row = trs[0].find_all(["th", "td"])

    headers.append("年月日")

    for th in header_row:
        headers.append(th.get_text(strip=True))

    # -------------------------
    # データ取得
    # -------------------------
    for tr in trs[2:]:

        tds = tr.find_all("td")

        if len(tds) == 0:
            continue

        # 時刻が空なら終了
        if tds[0].get_text(strip=True) == "":
            break

        row = [str(date)]

        for td in tds:
            row.append(td.get_text(strip=True))

        data_list_per_hour.append(row)

    return headers, data_list_per_hour

def create_csv(start_date, end_date, station):

    # CSV 出力先ディレクトリ
    output_dir = r"C:\Users\K.Maeda\Typhoon-Analyze\data\weather"
    os.makedirs(output_dir, exist_ok=True)

    # 出力ファイル名
    output_file = f"{station}_{start_date}_{end_date}.csv"

    # CSV の列
    fields = ["年月日", "時間", "気圧（現地）", "気圧（海面）",
              "降水量", "気温", "露点湿度", "蒸気圧", "湿度",
              "風速", "風向", "日照時間", "全天日射量", "降雪", "積雪"] # 天気、雲量、視程は今回は対象外とする

    with open(
        os.path.join(output_dir, output_file),
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:
        writer = csv.writer(f, lineterminator='\n')
        header_written = False

        date = start_date
        while date != end_date + datetime.timedelta(1):

            print(f"{station} {date} を取得中...")

            # 対象URL
            if station not in STATIONS:
                raise ValueError(f"未対応の観測地点です: {station}")

            prec_no = STATIONS[station]["prec_no"]
            block_no = STATIONS[station]["block_no"]

            url = (
                "https://www.data.jma.go.jp/obd/stats/etrn/view/hourly_s1.php?"
                f"prec_no={prec_no}"
                f"&block_no={block_no}"
                f"&year={date.year}"
                f"&month={date.month}"
                f"&day={date.day}"
                "&view="
            )

            headers, data_per_day = scraping(url, date)

            if not header_written:
                writer.writerow(headers)
                header_written = True
                
            for dpd in data_per_day:
                writer.writerow(dpd)

            date += datetime.timedelta(1)

# テストデータ
if __name__ == "__main__":

    start_date = datetime.date(2025, 7, 27)
    end_date = datetime.date(2025, 7, 28)

    create_csv(
        start_date,
        end_date,
        "福岡"
    )