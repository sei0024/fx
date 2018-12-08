import logging
import logging.config
import configparser
from mail import send
from oanda import get_balance

# コンフィグ
config = configparser.ConfigParser()
config.read('./conf/fx.conf')
THRESHOLD = float(config['balance']['threshold'])

# ロギンング
logging.config.fileConfig('./conf/logging.conf')
logger = logging.getLogger()

# メイン
logger.info('Start Check Balance Process.')

balance = get_balance()
if balance < THRESHOLD:
    logger.warn('Balance < Threshold (Balance: {}, Threshold: {})'.format(
        balance, THRESHOLD))
    subject = 'Balance Check Warning (Test)'
    body = 'Balance: {}, Threshold: {}'.format(balance, THRESHOLD)
    send(subject, body)
else:
    logger.info('Balance: {}'.format(balance))

logger.info('Finish Check Balance Process.')
