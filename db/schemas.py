def get_info_table_sql(table_name: str) -> str:
    return f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account TEXT NOT NULL UNIQUE,
        balance REAL NOT NULL,
        points INTEGER NOT NULL,
        volume REAL NOT NULL,
        margin_fee REAL NOT NULL,
        user_id INTEGER NOT NULL,
        api_key TEXT,
        api_secret TEXT,
        email TEXT NOT NULL,
        password TEXT NOT NULL,
        cookies TEXT,
        proxy TEXT
    )
    """

def get_insert_or_update_sql(table_name: str) -> str:
    return f"""
    INSERT INTO {table_name} 
        (account, balance, points, volume, margin_fee, user_id, api_key, api_secret, email, password, cookies, proxy)
    VALUES 
        (:account, :balance, :points, :volume, :margin_fee, :user_id, :api_key, :api_secret, :email, :password, :cookies, :proxy)
    ON CONFLICT(account) DO UPDATE SET
        balance = excluded.balance,
        points = excluded.points,
        volume = excluded.volume,
        margin_fee = excluded.margin_fee,
        user_id = excluded.user_id,
        api_key = excluded.api_key,
        api_secret = excluded.api_secret,
        email = excluded.email,
        password = excluded.password,
        cookies = excluded.cookies,
        proxy = excluded.proxy
    """

def get_select_all_sql(table_name: str) -> str:
    return f"SELECT * FROM {table_name}"

def get_clear_table_sql(table_name: str) -> str:
    return f"DELETE FROM {table_name}"

def get_select_by_user_sql(table_name: str) -> str:
    return f"SELECT * FROM {table_name} WHERE user_id = :user_id"

def get_select_by_account_sql(table_name: str) -> str:
    return f"SELECT * FROM {table_name} WHERE account = :account"