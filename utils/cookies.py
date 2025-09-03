import time
import json
from yarl import URL

from utils.session import AsyncSession


async def check_cookies_from_db(db_manager, table_name: str, account: str) -> bool:
    try:
        row = await db_manager.fetchone(
            f"SELECT cookies FROM {table_name} WHERE account = :account",
            {"account": account}
        )
        
        if not row or not row.get("cookies"):
            return False
        
        cookies_data = json.loads(row["cookies"])
        created_at = cookies_data.get("created_at")

        if not created_at:
            return False  
        
        age = int(time.time()) - int(created_at)
        return age < 3600
    except Exception as e:
        print("ERR in check_cookies_from_db:", type(e), e)
        return False

async def apply_cookies_from_db(session, db_manager, table_name: str, account: str, url: str = "https://arkm.com") -> bool:
    """Загрузить куки из БД и добавить их в aiohttp.ClientSession"""
    try:
        row = await db_manager.fetchone(
            f"SELECT cookies FROM {table_name} WHERE account = :account",
            {"account": account}
        )
        
        if not row or not row.get("cookies"):
            return False
            
        cookies_data = json.loads(row["cookies"])
        cookies = {k: v for k, v in cookies_data.items() if k not in ("created_at", "time")}
        
        session.cookie_jar.update_cookies(cookies, response_url=URL(url))
        return True
        
    except Exception as e:
        print(f"Ошибка загрузки cookies из БД: {e}")
        return False


async def save_cookies_to_db(session: AsyncSession, db_manager, table_name: str, account: str, url: str = "https://arkm.com"):
    """Сохранить куки текущей сессии в БД"""
    try:
        cookies = session.cookie_jar.filter_cookies(URL(url))
        dict_cookies = {key: cookie.value for key, cookie in cookies.items()}
        dict_cookies["created_at"] = int(time.time())
        
        cookies_json = json.dumps(dict_cookies, ensure_ascii=False)
        
        await db_manager.execute(
            f"UPDATE {table_name} SET cookies = :cookies WHERE account = :account",
            {"account": account, "cookies": cookies_json}
        )
        return dict_cookies
    
    except Exception as e:
        print(f"Ошибка сохранения cookies в БД: {e}")
        return None