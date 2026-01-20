import unittest
import os
import sys
import pandas as pd
from datetime import datetime

# Add parent directory to path to import database
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database


class TestDatabase(unittest.TestCase):
    def setUp(self):
        # 使用测试数据库文件
        database.DB_FILE = 'test_market.db'
        database.init_db()

    def tearDown(self):
        # 清理测试文件
        if os.path.exists('test_market.db'):
            os.remove('test_market.db')

    def test_save_and_get_data(self):
        # 创建模拟数据
        data = {
            'Open': [100.0, 101.0],
            'High': [102.0, 103.0],
            'Low': [99.0, 100.0],
            'Close': [101.0, 102.0],
            'Volume': [1000, 2000],
        }
        dates = [pd.Timestamp('2023-01-01'), pd.Timestamp('2023-01-02')]
        df = pd.DataFrame(data, index=dates)
        df.index.name = 'Date'

        # 保存数据
        count = database.save_daily_data('TEST_SYM', df)
        self.assertEqual(count, 2)

        # 验证最新日期
        latest_date = database.get_latest_date('TEST_SYM')
        self.assertEqual(latest_date, '2023-01-02')

        # 读取数据
        loaded_df = database.get_daily_data('TEST_SYM')
        self.assertEqual(len(loaded_df), 2)
        self.assertEqual(loaded_df.loc[datetime(2023, 1, 1), 'Close'], 101.0)

    def test_incremental_update(self):
        # 1. 保存第1天数据
        data1 = {
            'Open': [100.0], 'High': [102.0], 'Low': [99.0], 'Close': [101.0], 'Volume': [1000]
        }
        df1 = pd.DataFrame(data1, index=[pd.Timestamp('2023-01-01')])
        df1.index.name = 'Date'
        database.save_daily_data('TEST_SYM', df1)

        # 2. 保存第2天数据 (模拟增量)
        data2 = {
            'Open': [101.0], 'High': [103.0], 'Low': [100.0], 'Close': [102.0], 'Volume': [2000]
        }
        df2 = pd.DataFrame(data2, index=[pd.Timestamp('2023-01-02')])
        df2.index.name = 'Date'
        database.save_daily_data('TEST_SYM', df2)

        # 验证
        loaded_df = database.get_daily_data('TEST_SYM')
        self.assertEqual(len(loaded_df), 2)
        self.assertEqual(database.get_latest_date('TEST_SYM'), '2023-01-02')


if __name__ == '__main__':
    unittest.main()
