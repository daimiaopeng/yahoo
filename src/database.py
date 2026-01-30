import sqlite3
import pandas as pd
from datetime import datetime
import os
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_FILE = os.getenv('DB_PATH', 'market_data.db')


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db_connection()
    c = conn.cursor()

    # 创建日线数据表
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_prices (
            symbol TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (symbol, date)
        )
    ''')

    conn.commit()
    conn.close()
    logger.info("Database initialized.")


def get_latest_date(symbol):
    """获取指定股票最新的数据日期"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT MAX(date) FROM daily_prices WHERE symbol = ?', (symbol,))
    result = c.fetchone()[0]
    conn.close()
    return result


def save_daily_data(symbol, df):
    """保存日线数据到数据库"""
    if df.empty:
        return 0

    conn = get_db_connection()
    c = conn.cursor()

    count = 0
    # 确保索引是 datetime，并重置索引以便 date 成为列
    data_to_save = df.reset_index()

    for _, row in data_to_save.iterrows():
        # yfinance date 可能是 Date 或 DateTime 类型
        date_str = row['Date'].strftime('%Y-%m-%d')

        try:
            c.execute('''
                INSERT OR REPLACE INTO daily_prices (symbol, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol,
                date_str,
                row['Open'],
                row['High'],
                row['Low'],
                row['Close'],
                row['Volume']
            ))
            count += 1
        except Exception as e:
            logger.error(
                f"Error inserting row for {symbol} on {date_str}: {e}")

    conn.commit()
    conn.close()
    logger.info(f"Saved {count} records for {symbol}")
    return count


def get_daily_data(symbol, start_date=None, end_date=None):
    """从数据库获取日线数据，返回 DataFrame"""
    conn = get_db_connection()

    query = "SELECT date as Date, open as Open, high as High, low as Low, close as Close, volume as Volume FROM daily_prices WHERE symbol = ?"
    params = [symbol]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date ASC"

    try:
        df = pd.read_sql_query(query, conn, params=params)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
    except Exception as e:
        logger.error(f"Error querying data for {symbol}: {e}")
        df = pd.DataFrame()
    finally:
        conn.close()

    return df
