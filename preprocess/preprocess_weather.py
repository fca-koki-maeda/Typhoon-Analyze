import pandas as pd

input_file = "../data/weather/weather_2025.csv"

# 先頭10行をそのまま表示
df = pd.read_csv(
    input_file,
    # header=None,
    encoding="cp932",
    # nrows=10
)

print(df)

print("\n列数 =", df.shape[1])