# -*- coding: utf-8 -*-
"""
Shared database helper for AIMS platform skills.
Auto-detects MySQL via data-layer config, falls back to SQLite.
Usage: from db_helper import db
"""
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# 尝试导入data-layer获取MySQL配置，失败则降级SQLite
# Load data-layer for MySQL config & connection
try:
    import importlib.util
    _dl_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data-layer', 'main.py'))
    if os.path.exists(_dl_path):
        _dl_spec = importlib.util.spec_from_file_location("db_helper_dl", _dl_path)
        if _dl_spec:
            _dl_mod = importlib.util.module_from_spec(_dl_spec)
            sys.modules["db_helper_dl"] = _dl_mod
            _dl_spec.loader.exec_module(_dl_mod)
            _get_mysql_conn = lambda: _dl_mod.get_db()
            _mysql_ph = lambda: _dl_mod._db.placeholder()
            _mysql_available = lambda: _dl_mod._db.detect()
            _init_tables = lambda: _dl_mod.init_db()
            _DL_IMPORTED = True
        else:
            _DL_IMPORTED = False
    else:
        _DL_IMPORTED = False
except Exception:
    _DL_IMPORTED = False

if not _DL_IMPORTED:
    _get_mysql_conn = lambda: None
    _mysql_ph = lambda: "?"
    _mysql_available = lambda: False
    _init_tables = lambda: None

import sqlite3 as _sqlite3
DB_DIR = os.path.dirname(os.path.abspath(__file__))


def _get_sqlite_path(name: str) -> str:
    return os.path.join(DB_DIR, f"{name}.db")


def connection(db_name: str = "shared"):
    """获取数据库连接（优先MySQL，降级SQLite），返回(conn, is_mysql)"""

    """Get best available connection: MySQL > SQLite."""
    if _mysql_available():
        try:
            c = _get_mysql_conn()
            return c, True
        except Exception:
            pass
    path = _get_sqlite_path(db_name)
    c = _sqlite3.connect(path)
    c.row_factory = _sqlite3.Row
    return c, False


def placeholder(is_mysql: bool) -> str:
    return "%s" if is_mysql else "?"


def execute(conn, sql: str, params: tuple = None):
    c = conn.cursor()
    if params:
        c.execute(sql, params)
    else:
        c.execute(sql)
    return c


def query(conn, sql: str, params: tuple = None) -> List[Dict]:
    c = execute(conn, sql, params)
    return [dict(r) for r in c.fetchall()]


def query_one(conn, sql: str, params: tuple = None) -> Optional[Dict]:
    rows = query(conn, sql, params)
    return rows[0] if rows else None


def insert(conn, table: str, data: Dict) -> bool:
    ph = placeholder(isinstance(conn, _sqlite3.Connection) is False)
    cols = ", ".join(data.keys())
    vals = ", ".join([ph] * len(data))
    try:
        execute(conn, f"INSERT INTO {table} ({cols}) VALUES ({vals})", tuple(data.values()))
        conn.commit()
        return True
    except Exception:
        return False


def update(conn, table: str, data: Dict, where_field: str, where_val: Any) -> bool:
    ph = placeholder(isinstance(conn, _sqlite3.Connection) is False)
    set_clause = ", ".join([f"{k}={ph}" for k in data])
    vals = tuple(data.values()) + (where_val,)
    try:
        execute(conn, f"UPDATE {table} SET {set_clause} WHERE {where_field}={ph}", vals)
        conn.commit()
        return True
    except Exception:
        return False


def count(conn, table: str, condition: str = None, params: tuple = None) -> int:
    sql = f"SELECT COUNT(*) as cnt FROM {table}"
    if condition:
        sql += f" WHERE {condition}"
    row = query_one(conn, sql, params)
    return row["cnt"] if row else 0


def init_tables():
    """Initialize data-layer tables if MySQL is available."""
    if _mysql_available():
        try:
            _init_tables()
            return True
        except Exception:
            return False
    return False
