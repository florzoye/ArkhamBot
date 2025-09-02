def get_info_table_sql(table_name: str) -> str:
    return f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        account TEXT PRIMARY KEY,
        balance REAL NOT NULL,
        points INTEGER NOT NULL,
        volume REAL NOT NULL,
        margin_fee REAL NOT NULL
    )
    """

def get_insert_or_update_sql(table_name: str) -> str:
    """Добавление или обновление записи за один вызов"""
    return f"""
    INSERT INTO {table_name} (account, balance, points, volume, margin_fee)
    VALUES (:account, :balance, :points, :volume, :margin_fee)
    ON CONFLICT(account) DO UPDATE SET
        balance = excluded.balance,
        points = excluded.points,
        volume = excluded.volume,
        margin_fee = excluded.margin_fee
    """

def get_select_all_sql(table_name: str) -> str:
    return f"SELECT * FROM {table_name}"

def get_clear_table_sql(table_name: str) -> str:
    return f"DELETE FROM {table_name}"


