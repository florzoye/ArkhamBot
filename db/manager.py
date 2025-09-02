import aiosqlite
from contextlib import asynccontextmanager
from .tradeDB import TradeSQL  


class AsyncDatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    @asynccontextmanager
    async def get_cursor(self):
        conn = await aiosqlite.connect(self.db_path)
        try:
            cursor = await conn.cursor()
            yield cursor
            await conn.commit()
        except Exception as e:
            await conn.rollback()
            raise e
        finally:
            await conn.close()

    async def get_info_handler(self):
        async with self.get_cursor() as cursor:
            return TradeSQL(cursor)
