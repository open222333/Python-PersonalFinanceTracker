"""
MySQL 連線池模組（使用 DBUtils.PooledDB 取代已移除的 pymysql.pool）
PyMySQL >= 1.0 已刪除 pymysql.pool，改用 DBUtils 提供連線池功能。
"""
import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB
from src import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

_pool: PooledDB = None


def get_pool() -> PooledDB:
    global _pool
    if _pool is None:
        _pool = PooledDB(
            creator=pymysql,
            maxconnections=10,
            mincached=1,
            maxcached=5,
            blocking=True,
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            charset='utf8mb4',
            cursorclass=DictCursor,
            autocommit=True,
        )
    return _pool


def get_conn():
    """從連線池取得連線，使用完畢後呼叫 close() 歸還（不是真的關閉）"""
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
