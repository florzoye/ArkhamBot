import aiosqlite
from typing import List, Dict

class AsyncDatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def execute(self, query: str, params: Dict = None):
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.cursor()
            if params:
                await cursor.execute(query, params)
            else:
                await cursor.execute(query)
            await conn.commit()

    async def fetchall(self, query: str, params: Dict = None) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.cursor()
            if params:
                await cursor.execute(query, params)
            else:
                await cursor.execute(query)
            rows = await cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in rows]


