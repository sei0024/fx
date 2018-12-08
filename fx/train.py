import logging
import logging.config
import configparser
import numpy as np
import pandas as pd
import datetime as dt
from mysql import connector
from sklearn.preprocessing import MinMaxScaler
from sklearn.externals import joblib
from keras.models import Sequential
from keras.layers import Dense, LSTM

# コンフィグ
config = configparser.ConfigParser()
config.read('./conf/fx.conf')
GRANULARITY = config['oanda']['granularity']
MYSQL_HOST = config['mysql']['host']
MYSQL_PORT = config['mysql']['port']
MYSQL_USER = config['mysql']['user']
MYSQL_PASSWORD = config['mysql']['password']
WINDOW_SIZE = int(config['train']['window_size'])
EPOCHS = int(config['train']['epochs'])
BATCH_SIZE = int(config['train']['batch_size'])
UNIT_SIZE = int(config['train']['unit_size'])
X_SCALER_PATH = config['train']['x_scaler_path']
Y_SCALER_PATH = config['train']['y_scaler_path']
MODEL_PATH = config['train']['model_path']

# ロギンング
logging.config.fileConfig('./conf/logging.conf')
logger = logging.getLogger()

logger.info('Start Train Process')

# 日付情報取得
now = dt.datetime.now()
from_date = (now - dt.timedelta(days=365)).strftime('%Y-%m-%d 00:00:00')
to_date = now.strftime('%Y-%m-%d 00:00:00')

# データ取得
logger.info('Load Datasets from {} to {}'.format(from_date, to_date))
conn = connector.connect(
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    user=MYSQL_USER,
    # password=MYSQL_PASSWORD
)
cur = conn.cursor(dictionary=True)
sql = "SELECT open,high,low,close FROM candles.usd_jpy_{granularity} ".format(
    granularity=GRANULARITY)
sql += "WHERE time BETWEEN '{from_date}' AND '{to_date}'".format(
    from_date=from_date, to_date=to_date)
cur.execute(sql)
train_candles = cur.fetchall()
cur.close()

#  正解データ追加
train_candles = pd.DataFrame(train_candles)
train_corrects = train_candles.copy().close.shift(-1)
train_candles = train_candles[:-1]
train_corrects = pd.DataFrame(train_corrects[:-1])

# 正規化
x_scaler = MinMaxScaler(feature_range=(-1, 1))
x_scaler.fit(train_candles)
train_candles_norm = x_scaler.transform(train_candles)

y_scaler = MinMaxScaler(feature_range=(-1, 1))
y_scaler.fit(train_corrects)
train_corrects_norm = y_scaler.transform(train_corrects)

# scalerを保存
joblib.dump(x_scaler, X_SCALER_PATH)
joblib.dump(y_scaler, Y_SCALER_PATH)

# データセット作成
train_X = np.array([
    train_candles_norm[i:i+WINDOW_SIZE, :4]
    for i in range(len(train_candles_norm) - WINDOW_SIZE)
])
train_Y = train_corrects_norm[WINDOW_SIZE:]

# 学習
model = Sequential()
model.add(LSTM(UNIT_SIZE, input_shape=(train_X.shape[1], train_X.shape[2])))
model.add(Dense(1, activation='linear'))
model.compile(loss='mse', optimizer='adam', metrics=['mean_absolute_error'])
history = model.fit(
    train_X, train_Y, epochs=EPOCHS, batch_size=BATCH_SIZE,
    verbose=2, shuffle=False
)
loss = history.history['loss'][-1]
mae = history.history['mean_absolute_error'][-1]
logger.info('loss: {}, mean_absolute_error: {}'.format(loss, mae))

# モデルを保存
model.save(MODEL_PATH)

logger.info('Finish Train Process')
