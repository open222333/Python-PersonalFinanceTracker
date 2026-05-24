from configparser import ConfigParser
from os.path import exists, join
from os import makedirs, environ
import logging


config = ConfigParser()
config.read(join('conf', 'config.ini'))


# logs相關參數
# 關閉log功能 輸入選項 (true, True, 1) 預設 不關閉
LOG_DISABLE = config.getboolean('LOG', 'LOG_DISABLE', fallback=False)
# logs路徑 預設 logs
LOG_PATH = config.get('LOG', 'LOG_PATH', fallback='logs')
# 設定紀錄log等級 DEBUG,INFO,WARNING,ERROR,CRITICAL 預設WARNING
LOG_LEVEL = config.get('LOG', 'LOG_LEVEL', fallback='WARNING')
# 關閉紀錄log檔案 輸入選項 (true, True, 1)  預設 不關閉
LOG_FILE_DISABLE = config.getboolean('LOG', 'LOG_FILE_DISABLE', fallback=False)

# 建立log資料夾
if not exists(LOG_PATH) and not LOG_DISABLE:
    makedirs(LOG_PATH)

if LOG_DISABLE:
    logging.disable()


# flask json 設定檔路徑 預設值 conf/flask.json
FLASK_JSON_PATH = config.get('SETTING', 'FLASK_JSON_PATH', fallback=join('conf', 'flask.json'))

# 後台管理頁面名稱 預設值 後台管理
ADMIN_TITLE = config.get('SETTING', 'ADMIN_TITLE', fallback='後台管理')

# Flask 參數
FLASK_PORT = int(environ.get('FLASK_PORT', 5000))
JWT_ACCESS_TOKEN_EXPIRES_HOURS = int(environ.get('JWT_ACCESS_TOKEN_EXPIRES_HOURS', 8))

# MongoDB 連線參數
MONGO_URI = config.get('MONGO', 'MONGO_URI', fallback='mongodb://localhost:27017')
MONGO_DB = config.get('MONGO', 'MONGO_DB', fallback='flask_app')

# MySQL 連線參數
MYSQL_HOST = config.get('MYSQL', 'MYSQL_HOST', fallback='localhost')
MYSQL_PORT = config.getint('MYSQL', 'MYSQL_PORT', fallback=3306)
MYSQL_USER = config.get('MYSQL', 'MYSQL_USER', fallback='root')
MYSQL_PASSWORD = config.get('MYSQL', 'MYSQL_PASSWORD', fallback='')
MYSQL_DB = config.get('MYSQL', 'MYSQL_DB', fallback='flask_app')

# Redis 連線參數
REDIS_HOST = config.get('REDIS', 'REDIS_HOST', fallback='localhost')
REDIS_PORT = config.getint('REDIS', 'REDIS_PORT', fallback=6379)
REDIS_PASSWORD = config.get('REDIS', 'REDIS_PASSWORD', fallback='')
REDIS_DB = config.getint('REDIS', 'REDIS_DB', fallback=0)
