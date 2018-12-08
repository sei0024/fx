import configparser
import datetime as dt
from mysql import connector
import oandapyV20
import oandapyV20.endpoints.instruments as instruments
from utils import date_to_iso, iso_to_date, date_to_str

# コンフィグ
config = configparser.ConfigParser()
config.read('./conf/fx.conf')
ACCOUNT_ID = config['oanda']['account_id']
ACCESS_TOKEN = config['oanda']['access_token']
INSTRUMENT = config['oanda']['instrument']
GRANULARITY = config['oanda']['granularity']
MYSQL_HOST = config['mysql']['host']
MYSQL_PORT = config['mysql']['port']
MYSQL_USER = config['mysql']['user']
MYSQL_PASSWORD = config['mysql']['password']

# 日付情報取得
now = dt.datetime.now()
from_date_str = (now - dt.timedelta(days=1)).strftime('%Y%m%d')
to_date_str = now.strftime('%Y%m%d')

from_date = dt.datetime.strptime(from_date_str, "%Y%m%d")
to_date = dt.datetime.strptime(to_date_str, "%Y%m%d")

tmp_date = from_date

client = oandapyV20.API(access_token=ACCESS_TOKEN, environment="practice")

conn = connector.connect(
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    user=MYSQL_USER,
    # password=MYSQL_PASSWORD,
)

while True:
    if tmp_date >= to_date:
        break

    from_iso = date_to_iso(tmp_date)
    to_iso = date_to_iso(tmp_date + dt.timedelta(days=1))

    params = {"granularity": GRANULARITY, "from": from_iso, "to": to_iso}

    request = instruments.InstrumentsCandles(
        instrument=INSTRUMENT, params=params)
    try:
        response = client.request(request)
    except Exception as e:
        print("Failed to download candles in {}: {}".format(tmp_date, e))
        tmp_date = tmp_date + dt.timedelta(days=1)
        continue

    if not response["candles"]:
        print("Skip process in {}".format(tmp_date))
        tmp_date = tmp_date + dt.timedelta(days=1)
        continue

    candles = []
    for candle in response["candles"]:
        candles.append([
            date_to_str(iso_to_date(candle["time"])),
            candle["mid"]["l"],
            candle["mid"]["c"],
            candle["mid"]["o"],
            candle["mid"]["h"],
            candle["volume"],
            candle["complete"],
        ])

    table = "usd_jpy_{}".format(GRANULARITY.lower())
    sql = "insert into candles.{table} values ".format(table=table)
    for candle in candles:
        sql += "("
        for val in candle:
            sql += "'{}',".format(val)
        sql = sql[:-1]  # 最後のカンマを削除
        sql += "),"
    sql = sql[:-1]  # 最後のカンマを削除

    cur = conn.cursor()
    try:
        cur.execute(sql)
        conn.commit()
    except Exception as e:
        print("Failed to insert candles in {}: {}".format(tmp_date, e))
        conn.rollback()
    finally:
        cur.close()

    print("Finish process in {}".format(tmp_date))
    tmp_date = tmp_date + dt.timedelta(days=1)

conn.close()
