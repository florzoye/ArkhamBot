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
ENABLE_2FA = True              # включить ли 2FA ввод

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
POINTS_GRADE = [
    {'200': 200000},
    {'400': 500000},
]

volume = 501



for item in POINTS_GRADE:
    key, value = list(item.items())[0]
    if int(value) >= volume:
        print(list((POINTS_GRADE[POINTS_GRADE.index({key: value})-1]).values())[0])