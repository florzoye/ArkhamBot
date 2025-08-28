import aiosqlite
from typing import List, Dict
from db.schemas import (
    get_info_table_sql,
    get_update_info_sql,
    get_insert_info_sql,
    get_select_all_sql
)

class TradeSQL:
    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn

    async def create_table(self, table_name: str) -> None:
        await self.conn.execute(get_info_table_sql(table_name))
        await self.conn.commit()

    async def add_info(self, table_name: str, news: Dict) -> None:
        # Проверим есть ли запись (например по account)
        async with self.conn.execute(f"SELECT 1 FROM {table_name} WHERE account = :account", news) as cursor:
            existing = await cursor.fetchone()

        if existing:
            await self.conn.execute(
                get_update_info_sql(table_name),
                news
            )
        else:
            await self.conn.execute(
                get_insert_info_sql(table_name),
                news
            )

        await self.conn.commit()

    async def get_all(self, table_name: str) -> List[Dict]:
        async with self.conn.execute(get_select_all_sql(table_name)) as cursor:
            columns = [col[0] for col in cursor.description]
            rows = await cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

    async def clear_table(self, table_name: str):
        await self.conn.execute(f"DELETE FROM {table_name}")
        await self.conn.commit()
