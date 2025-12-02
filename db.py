# db.py
import os
import psycopg2
import psycopg2.pool

# exemplo de URL local. depois você pode sobrescrever com variável de ambiente
DEFAULT_DB_URL = "postgresql://chatbot_user:movelina121@localhost:5432/chatbot"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

POOL = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=5,
    dsn=DATABASE_URL,
)

def db_get_conn():
    return POOL.getconn()

def db_put_conn(conn):
    POOL.putconn(conn)

def db_query_one(sql, params=None):
    params = params or ()
    conn = db_get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        return row
    finally:
        db_put_conn(conn)

def db_query_all(sql, params=None):
    params = params or ()
    conn = db_get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return rows
    finally:
        db_put_conn(conn)

def db_execute(sql, params=None):
    params = params or ()
    conn = db_get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
    finally:
        db_put_conn(conn)
