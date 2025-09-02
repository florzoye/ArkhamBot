def get_insert_spread_sql(table_name: str) -> str:
    return f"""
    INSERT INTO {table_name} (
        account, balance, points, volume
    )
    VALUES (?, ?, ?)
    """

def get_select_all_sql(table_name: str) -> str:
    return f"SELECT * FROM {table_name}"

def get_info_table_sql(table_name: str) -> str:
    return f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        account TEXT NOT NULL,
        balance REAL NOT NULL,
        points INTEGER NOT NULL,
        volume REAL NOT NULL
    )
    """

def get_update_info_sql(table_name: str) -> str:
    return f"""
    UPDATE {table_name} 
    SET balance = :balance, points = :points, volume = :volume
    WHERE account = :account
    """

def get_insert_info_sql(table_name: str) -> str:
    return f"""
    INSERT INTO {table_name} (account, balance, points, volume)
    VALUES (:account, :balance, :points, :volume)
    """

def get_select_column_sql(table_name: str, column_name: str) -> str:
    return f"SELECT {column_name} FROM {table_name}"