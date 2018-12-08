import configparser
import datetime as dt
from oandapyV20 import API
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.orders as orders
from utils import date_to_iso

# コンフィグ
config = configparser.ConfigParser()
config.read('/home/sei0024/fx/conf/fx.conf')
ACCOUNT_ID = config['oanda']['account_id']
ACCESS_TOKEN = config['oanda']['access_token']
ENVIRONMENT = config['oanda']['environment']
INSTRUMENT = config['oanda']['instrument']
GRANULARITY = config['oanda']['granularity']
UNITS_UPPER_LIMIT = int(config['oanda']['units_upper_limit'])
UNITS_LOWER_LIMIT = int(config['oanda']['units_lower_limit'])
LEVERAGE = int(config['oanda']['leverage'])


client = API(access_token=ACCESS_TOKEN, environment=ENVIRONMENT)


def get_from_to_iso():
    now = dt.datetime.now()
    minute = int(now.minute / 15) * 15

    to_time = dt.datetime(now.year, now.month, now.day, now.hour, minute)
    from_time = to_time - dt.timedelta(hours=3)
    from_iso = date_to_iso(from_time)
    to_iso = date_to_iso(to_time)

    return {'from': from_iso, 'to': to_iso}


def get_candles(from_iso, to_iso):
    params = {'granularity': GRANULARITY, 'from': from_iso, 'to': to_iso}
    request = instruments.InstrumentsCandles(
        instrument=INSTRUMENT, params=params
    )
    response = client.request(request)
    return response['candles']


def get_balance():
    request = accounts.AccountDetails(ACCOUNT_ID)
    response = client.request(request)
    return float(response["account"]["balance"])


def get_position():
    request = positions.PositionList(accountID=ACCOUNT_ID)
    response = client.request(request)
    return response['positions'][0]


def has_position(position):
    if int(position["long"]["units"]) > 0:
        return True
    if int(position["short"]["units"]) > 0:
        return True
    return False


def close_positions():
    data = {"longUnits": "ALL"}
    request = positions.PositionClose(
        ACCOUNT_ID, instrument=INSTRUMENT, data=data
    )
    client.request(request)


def check_candles_length(candles, length):
    if len(candles) != length:
        return False
    return True


def reform_candles(candles):
    reformed_candles = []
    for candle in candles:
        reformed_candles.append({
            "open": float(candle["mid"]["o"]),
            "high": float(candle["mid"]["h"]),
            "low": float(candle["mid"]["l"]),
            "close": float(candle["mid"]["c"]),
        })
    return reformed_candles


def get_price():
    params = {'instruments': INSTRUMENT}
    request = pricing.PricingInfo(accountID=ACCOUNT_ID, params=params)
    response = client.request(request)
    price = response["prices"][0]
    return {
        'ask': float(price["asks"][0]["price"]),
        'bid': float(price["bids"][0]["price"]),
    }


def get_units(balance, price):
    units = (balance * LEVERAGE) / price
    if units > UNITS_UPPER_LIMIT:
        return UNITS_UPPER_LIMIT
    if units < UNITS_LOWER_LIMIT:
        return UNITS_LOWER_LIMIT
    units = int(units / UNITS_LOWER_LIMIT) * UNITS_LOWER_LIMIT
    return units


def build_order(units, loss_price):
    order = {"order": {}}
    order["order"]["type"] = "MARKET"
    order["order"]["instrument"] = "USD_JPY"
    order["order"]["units"] = str(units)
    order["order"]["timeInForce"] = "FOK"
    order["order"]["positionFill"] = "DEFAULT"
    order["order"]["stopLossOnFill"] = {}
    order["order"]["stopLossOnFill"]["price"] = str(loss_price)
    order["order"]["stopLossOnFill"]["timeInForce"] = "GTC"
    return order


def create_order(units, loss_price):
    data = build_order(units, loss_price)
    request = orders.OrderCreate(ACCOUNT_ID, data=data)
    response = client.request(request)

    if "orderCancelTransaction" in response:
        reason = response["orderCancelTransaction"]["reason"]
        print("Failed to order: {}".format(reason))

    return response
