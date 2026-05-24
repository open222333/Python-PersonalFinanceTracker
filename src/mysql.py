from pymysql import connect
from pymysql.cursors import DictCursor
from pymysql.pool import ConnectionPool
from src import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

_pool = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            charset='utf8mb4',
            cursorclass=DictCursor,
            autocommit=True,
            maxconnections=10
        )
    return _pool


def get_conn():
    """取得 MySQL 連線，使用完畢後需手動 close()"""
    return get_pool().connection()


def query(sql: str, args=None) -> list:
    """執行 SELECT，回傳 list[dict]"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()
    finally:
        conn.close()


def execute(sql: str, args=None) -> int:
    """執行 INSERT / UPDATE / DELETE，回傳影響筆數"""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.rowcount
    finally:
        conn.close()
