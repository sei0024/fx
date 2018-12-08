# ライブラリ定義
import json
import logging
import logging.config
import configparser
import numpy as np
import pandas as pd
from sklearn.externals import joblib
from oandapyV20 import API
from keras.models import load_model
from oanda import get_from_to_iso, get_candles, reform_candles
from oanda import get_balance, get_price, get_position
from oanda import close_positions, get_units, create_order

# コンフィグ
config = configparser.ConfigParser()
config.read('/home/sei0024/fx/conf/fx.conf')
ACCOUNT_ID = config['oanda']['account_id']
ACCESS_TOKEN = config['oanda']['access_token']
GRANULARITY = config['oanda']['granularity']
INSTRUMENT = config['oanda']['instrument']
ENVIRONMENT = config['oanda']['environment']
LEVERAGE = int(config['oanda']['leverage'])
SPREAD = float(config['oanda']['spread'])
UNITS_UPPER_LIMIT = int(config['oanda']['units_upper_limit'])
UNITS_LOWER_LIMIT = int(config['oanda']['units_lower_limit'])
LOSS_PRICE = float(config['oanda']['loss_price'])
WINDOW_SIZE = int(config['train']['window_size'])
X_SCALER_PATH = config['train']['x_scaler_path']
Y_SCALER_PATH = config['train']['y_scaler_path']
MODEL_PATH = config['train']['model_path']
PRE_PREDICT_PATH = config['trade']['pre_predict_path']

# ロギンング
logging.config.fileConfig('/home/sei0024/fx/conf/logging.conf')
logger = logging.getLogger()

logger.info('Start Trade Process')

# クライアントを定義
client = API(access_token=ACCESS_TOKEN, environment=ENVIRONMENT)

# ローソクを取得
iso = get_from_to_iso()

candles = get_candles(iso['from'], iso['to'])
if len(candles) != WINDOW_SIZE:
    logger.error('Unexpected candles length: {}'.format(len(candles)))
    exit(0)

candles = reform_candles(candles)
candles = pd.DataFrame(candles)

# 前処理
x_scaler = joblib.load(X_SCALER_PATH)
normed_candles = x_scaler.transform(candles)  # pandas -> numpy に変換される
X = np.reshape(
    normed_candles, (1, normed_candles.shape[0], normed_candles.shape[1])
)

# 予測
model = load_model(MODEL_PATH)
P = model.predict(X)

# 後処理
y_scaler = joblib.load(Y_SCALER_PATH)
predicts = y_scaler.inverse_transform(P)
predict = float(predicts[0][0])  # numpy -> float 変換

# 情報取得
balance = get_balance()
price = get_price()
position = get_position()

# 前回の予測結果を取得
pre_predict = float(json.load(open(PRE_PREDICT_PATH, 'r'))['pre_predict'])

# 情報を表示
logger.info('balance: {}, predict: {}, ask: {}, bid: {}'.format(
    balance, predict, price['ask'], price['bid'])
)

# ロングポジションがある場合
if int(position['long']['units']) > 0:
    long_price = float(position['long']['averagePrice'])
    if (long_price <= predict) or (pre_predict > predict):
        logger.info('KEEP: long={}, predict={}'.format(long_price, predict))
    else:
        logger.info('CLOSE: logn={}, predict={}'.format(long_price, predict))
        close_positions(ACCOUNT_ID, instrument=INSTRUMENT)

# ショートポジションがある場合
if int(position['short']['units']) > 0:
    short_price = float(position['short']['averagePrice'])
    if (short_price >= predict) or (pre_predict < predict):
        logger.info('KEEP: short={}, predict={}'.format(long_price, predict))
    else:
        close_positions(ACCOUNT_ID, instrument=INSTRUMENT)
        logger.info('CLOSE: short={}, predict={}'.format(long_price, predict))

# ポジションがない場合
if (int(position['long']['units']) <= 0) and (int(position['short']['units']) <= 0):
    mid = (price['ask'] + price['bid']) / 2
    if mid + SPREAD < predict:
        units = get_units(balance, price['ask'])
        units = '+' + str(units)
        loss_price = price['ask'] - LOSS_PRICE
        create_order(units, loss_price)
        logger.info('LONG: predict={}'.format(predict))
    elif mid - SPREAD > predict:
        units = get_units(balance, price['bid'])
        units = '-' + str(units)
        loss_price = price['bid'] + LOSS_PRICE
        create_order(units, loss_price)
        logger.info('SHORT: predict={}'.format(predict))
    else:
        logger.info('NOTHING: predict={}'.format(predict))

# 予測結果を保存
json.dump({'pre_predict': predict}, open(PRE_PREDICT_PATH, 'w')) 

logger.info('Finish Trade Process')
