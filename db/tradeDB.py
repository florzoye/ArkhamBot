from loguru import logger
from typing import Dict, List

from db.manager import AsyncDatabaseManager
from db.schemas import (
    get_info_table_sql,
    get_insert_or_update_sql,
    get_select_all_sql,
    get_clear_table_sql
)

class TradeSQL:
    def __init__(self, db: AsyncDatabaseManager):
        self.db = db

    async def create_table(self, table_name: str):
        await self.db.execute(get_info_table_sql(table_name))
        logger.success(f"Таблица '{table_name}' создана или уже существует")

    async def add_info(self, table_name: str, info: Dict):
        await self.db.execute(get_insert_or_update_sql(table_name), info)
        logger.success(f"Информация для аккаунта '{info['account']}' сохранена")

    async def get_all(self, table_name: str) -> List[Dict]:
        return await self.db.fetchall(get_select_all_sql(table_name))

    async def clear_table(self, table_name: str):
        await self.db.execute(get_clear_table_sql(table_name))
        logger.warning(f"Таблица '{table_name}' очищена")
