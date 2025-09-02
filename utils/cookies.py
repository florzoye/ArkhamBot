from data import config
import os
import time
import json
from yarl import URL

from utils.session import AsyncSession

def check_cookies_file(path: str = config.COOKIE_FILE) -> bool:
    """Проверить, что cookies.json существует и ещё не устарел"""
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)  
        created_at = data.get("created_at") or data.get("time")
        if not created_at:
            return False
        age = int(time.time()) - int(created_at)
        return age < 3600  # True если куки свежее часа
    except (json.JSONDecodeError, OSError, ValueError):
        return False

async def apply_cookies(session, path: str = config.COOKIE_FILE, url: str = "https://arkm.com"):
    """Загрузить куки из файла и добавить их в aiohttp.ClientSession"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cookies = {k: v for k, v in data.items() if k not in ("created_at", "time")}
        session.cookie_jar.update_cookies(cookies, response_url=URL(url))
        return True
    except Exception as e:
        print(f"Ошибка загрузки cookies: {e}")
        return False

async def get_cookies_json(session: AsyncSession , url: str = "https://arkm.com") -> str:
    """Вернуть куки текущей сессии в формате JSON-строки"""
    cookies = session.cookie_jar.filter_cookies(URL(url))
    dict_cookies = {key: cookie.value for key, cookie in cookies.items()}
    dict_cookies["created_at"] = int(time.time()) 
    return dict_cookies