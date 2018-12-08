import logging
import logging.config
import configparser
from oanda import get_position, has_position, close_positions

# コンフィグ
config = configparser.ConfigParser()
config.read('./conf/fx.conf')
THRESHOLD = float(config['balance']['threshold'])

# ロギンング
logging.config.fileConfig('./conf/logging.conf')
logger = logging.getLogger()

# メイン
logger.info('Start Close Positions Process.')

position = get_position()
if has_position(position):
    try:
        close_positions()
        logger.info('Success close positions: {}'.format(position))
    except Exception as e:
        logger.error('Fatal to close positions: {}'.format(e))
else:
    logger.info('No positions')

logger.info('Finish Close Positions Process.')
