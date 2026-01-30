"""
Yahoo Finance API 配置文件
"""

# 支持的基准指数
SUPPORTED_BENCHMARKS = {
    'QQQ': 'QQQ',       # 纳斯达克100 ETF
    'SPY': 'SPY',       # 标普500 ETF
    'DIA': 'DIA',       # 道琼斯工业 ETF
    'IWM': 'IWM',       # 罗素2000 ETF
    'VTI': 'VTI',       # 全美股市 ETF
}

# 默认启动时订阅的符号列表
INITIAL_SYMBOLS = [
    'QQQ', 'SPY', 'QLD', 'TQQQ', 'VTI','WELL','MCK','NVO','PGR',
    'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMD', 'META', 'AMZN', 'GOOGL',  
    'COIN', 'HOOD', 'PLTR', 'SNOW'
]
