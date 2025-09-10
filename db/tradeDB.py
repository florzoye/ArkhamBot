from loguru import logger
from typing import Dict, List
import json

from db.manager import AsyncDatabaseManager
from db.schemas import (
    get_info_table_sql,
    get_insert_or_update_sql,
    get_select_all_sql,
    get_clear_table_sql,
    get_select_by_account_sql,
)
from utils.cookies import check_cookies_from_db

class TradeSQL:
    def __init__(self, db: AsyncDatabaseManager): 
        self.db = db

    async def create_table(self, table_name: str):
        try:
            await self.db.execute(get_info_table_sql(table_name))
            logger.success(f"Таблица '{table_name}' создана или уже существует")
        except Exception as e:
            logger.error(f"Ошибка создания таблицы '{table_name}': {e}")
            raise

    async def add_info(self, table_name: str, info: Dict):
        try:
            await self.db.execute(get_insert_or_update_sql(table_name), info)
            logger.success(f"Информация для аккаунта '{info['account']}' сохранена")
        except Exception as e:
            logger.error(f"Ошибка сохранения информации для аккаунта '{info.get('account', 'unknown')}': {e}")
            raise

    async def get_all(self, table_name: str) -> List[Dict]:
        try:
            return await self.db.fetchall(get_select_all_sql(table_name))
        except Exception as e:
            logger.error(f"Ошибка получения данных из таблицы '{table_name}': {e}")
            return []

    async def clear_table(self, table_name: str):
        try:
            await self.db.execute(get_clear_table_sql(table_name))
            logger.warning(f"Таблица '{table_name}' очищена")
        except Exception as e:
            logger.error(f"Ошибка очистки таблицы '{table_name}': {e}")
            raise

    async def get_account(self, table_name: str, account: str) -> Dict | None:
        """Получить конкретный аккаунт"""
        try:
            rows = await self.db.fetchall(get_select_by_account_sql(table_name), {"account": account})
            return rows[0] if rows else None
        except Exception as e:
            logger.error(f"Ошибка получения аккаунта '{account}': {e}")
            return None
    
    async def get_cookies(self, table_name: str, account: str) -> dict | None:
        """Вернуть cookies для аккаунта в виде dict"""
        try:
            row = await self.db.fetchone(get_select_by_account_sql(table_name), {"account": account})
            if row and row.get("cookies"):
                return json.loads(row["cookies"])
            return None
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Ошибка получения cookies для аккаунта '{account}': {e}")
            return None

    async def update_cookies(self, table_name: str, account: str, cookies: dict):
        """Обновить cookies для аккаунта"""
        try:
            cookies_json = json.dumps(cookies, ensure_ascii=False)
            await self.db.execute(
                f"UPDATE {table_name} SET cookies = :cookies WHERE account = :account",
                {"account": account, "cookies": cookies_json}
            )
            logger.success(f"Cookies для аккаунта '{account}' обновлены")
        except Exception as e:
            logger.error(f"Ошибка обновления cookies для аккаунта '{account}': {e}")
            raise

    async def get_proxy(self, table_name: str, account: str) -> str | None:
        """Получить прокси для конкретного аккаунта"""
        try:
            row = await self.db.fetchone(get_select_by_account_sql(table_name), {"account": account})
            return row.get("proxy") if row else None
        except Exception as e:
            logger.error(f"Ошибка получения прокси для аккаунта '{account}': {e}")
            return None

    async def update_proxy(self, table_name: str, account: str, proxy: str):
        """Обновить прокси для аккаунта"""
        try:
            await self.db.execute(
                f"UPDATE {table_name} SET proxy = :proxy WHERE account = :account",
                {"account": account, "proxy": proxy}
            )
            logger.success(f"Прокси для аккаунта '{account}' обновлен")
        except Exception as e:
            logger.error(f"Ошибка обновления прокси для аккаунта '{account}': {e}")
            raise

    async def get_email_password(self, table_name: str, account: str) -> tuple[str | None, str | None]:
        """Получить email и password для аккаунта"""
        try:
            row = await self.db.fetchone(get_select_by_account_sql(table_name), {"account": account})
            if row:
                return row.get("email"), row.get("password")
            return None, None
        except Exception as e:
            logger.error(f"Ошибка получения email/password для аккаунта '{account}': {e}")
            return None, None

    async def update_email_password(self, table_name: str, account: str, email: str, password: str):
        """Обновить email и password для аккаунта"""
        try:
            await self.db.execute(
                f"UPDATE {table_name} SET email = :email, password = :password WHERE account = :account",
                {"account": account, "email": email, "password": password}
            )
            logger.success(f"Email/password для аккаунта '{account}' обновлены")
        except Exception as e:
            logger.error(f"Ошибка обновления email/password для аккаунта '{account}': {e}")
            raise
    
    async def update_account_data(
            self,
            table_name: str,
            account: str,
            balance: str | None,
            volume: str | None,
            points: str | None,
            fee: str | None,
            bonus: str | None,
            cookies: dict | None,
        ):
            try:
                cookies_json = json.dumps(cookies, ensure_ascii=False) if cookies else None

                await self.db.execute(
                    f"""
                    UPDATE {table_name}
                    SET balance = :balance,
                        volume = :volume,
                        points = :points,
                        margin_fee = :margin_fee,
                        margin_bonus = :margin_bonus,
                        cookies = COALESCE(:cookies, cookies)
                    WHERE account = :account
                    """,
                    {
                        "account": account,
                        "balance": balance or "0",
                        "volume": volume or "0",
                        "points": points or "0",
                        "margin_fee": fee or "0",
                        "margin_bonus": bonus or "0",
                        "cookies": cookies_json,
                    }
                )
                logger.success(f"✅ Данные аккаунта '{account}' обновлены")
            except Exception as e:
                logger.error(f"Ошибка обновления данных аккаунта '{account}': {e}")
                raise
    async def delete_account(self, table_name: str, account: str) -> bool:
        """Удалить конкретный аккаунт из таблицы"""
        try:
            # Проверяем существует ли аккаунт
            existing_account = await self.get_account(table_name, account)
            if not existing_account:
                logger.warning(f"Аккаунт '{account}' не найден в таблице '{table_name}'")
                return False

            # Удаляем аккаунт
            await self.db.execute(
                f"DELETE FROM {table_name} WHERE account = :account",
                {"account": account}
            )
            
            logger.success(f"Аккаунт '{account}' успешно удален из таблицы '{table_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления аккаунта '{account}': {e}")
            return False
        
    async def check_cookies_valid(self, table_name: str, account: str) -> bool:
        """Проверить валидность куков для аккаунта"""
        return await check_cookies_from_db(self.db, table_name, account)