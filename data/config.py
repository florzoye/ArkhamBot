# config.py
from enum import Enum

# =========================
#  Пользовательские данные
# =========================
API_KEY_2CAPTCHA = "7d0cfeb3aec1d6bf7daff68cb33174be"
LOGIN_EMAIL = "loalalaskff@gmail.com"
LOGIN_PASSWORD = "xjPMoPZxvr2!"
ARKHAM_API_KEY = "849ac655-bb0e-4584-9ebb-be5d0e5e2ac7"
ARKHAM_API_SECRET = "PM0vJf9okYn8XBcGY/I20GrKkrollqxP2JuBFt6aMq0="
PROXY = 'http://user235306:591efk@185.189.245.165:6187'

# =========================
#  Системные константы
# =========================
SITE_KEY = "0x4AAAAAABCVqfQCJfxkyXT8"
PAGE_URL = "https://arkm.com/uk/login?redirectPath=%2Fuk"
RES_URL = "http://2captcha.com/res.php"
CREATE_URL = "http://2captcha.com/in.php"
COOKIE_FILE = "cookies.json"

# =========================
# 🔧 Пользовательские настройки
# =========================
NUMBER_ATTEMPTS_REQUESTS = 10  # сколько раз проверять капчу (по умолчанию 10)
ENABLE_2FA = True              # включена ли 2FA 

# =========================
#  Enum для плеча
# =========================
class Leverage(Enum):
    X1 = 1
    X2 = 2
    X3 = 3
    X4 = 4
    X5 = 5
    X6 = 6
    X7 = 7
    X8 = 8
    X9 = 9
    X10 = 10
    X11 = 11
    X12 = 12
    X13 = 13
    X14 = 14
    X15 = 15
    X16 = 16
    X17 = 17
    X18 = 18
    X19 = 19
    X20 = 20
    X21 = 21
    X22 = 22
    X23 = 23
    X24 = 24
    X25 = 25


# =========================
#  Points
# =========================
SPOT_FEE = 0.001  
FUTURES_FEE = 0.0005  
    
SPOT_POINTS_TIERS = [
    {'tier': 1, 'volume': 100000, 'points': 200},
    {'tier': 2, 'volume': 250000, 'points': 500},
    {'tier': 3, 'volume': 500000, 'points': 1000},
    {'tier': 4, 'volume': 1000000, 'points': 2000},
    {'tier': 5, 'volume': 2500000, 'points': 5000},
    {'tier': 6, 'volume': 5000000, 'points': 10000},
    {'tier': 7, 'volume': 10000000, 'points': 20000},
    {'tier': 8, 'volume': float('inf'), 'points_per_100k': 300}
]

# Таблица очков для фьючерсов
FUTURES_POINTS_TIERS = [
    {'tier': 1, 'volume': 200000, 'points': 200},
    {'tier': 2, 'volume': 500000, 'points': 500},
    {'tier': 3, 'volume': 1000000, 'points': 1000},
    {'tier': 4, 'volume': 2000000, 'points': 2000},
    {'tier': 5, 'volume': 5000000, 'points': 5000},
    {'tier': 6, 'volume': 10000000, 'points': 10000},
    {'tier': 7, 'volume': 20000000, 'points': 20000},
    {'tier': 8, 'volume': float('inf'), 'points_per_200k': 300}
]
