"""
Yahoo Finance API 服务
提供多基准指数数据（QQQ、SPY 等）的历史和实时数据
保留原有 /api/data 和 /api/status 接口
"""

from datetime import timedelta
import database
import time
from datetime import datetime
from queue import Queue
import yfinance as yf
import threading
from flask import Flask, jsonify, request
import os
import sys
import socket
import logging
import config  # 导入配置

# ========== 智能代理检测 - 必须在 import yfinance 之前 ==========


def check_proxy_available(host="127.0.0.1", port=7899, timeout=1):
    """检测代理端口是否可用"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


# 尝试常见代理端口
PROXY_PORTS = [7899, 7897, 7890, 1080, 10808]
proxy_found = False

for port in PROXY_PORTS:
    if check_proxy_available("127.0.0.1", port):
        PROXY = f"http://127.0.0.1:{port}"
        os.environ['HTTP_PROXY'] = PROXY
        os.environ['HTTPS_PROXY'] = PROXY
        os.environ['ALL_PROXY'] = PROXY
        proxy_found = True
        print(f"✅ 检测到代理: {PROXY}")
        break

if not proxy_found:
    print("ℹ️ 未检测到代理，使用直连模式")


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./yfinance_server.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

# 添加CORS支持（手动实现，避免依赖flask-cors）

VERSION = os.getenv('APP_VERSION', 'local-dev')
COMMIT_TIME = os.getenv('APP_COMMIT_TIME', 'unknown')


@app.route('/', methods=['GET'])
def get_api_docs():
    """获取服务信息和完整 API 文档"""
    return jsonify({
        'service': 'Yahoo Finance API',
        'version': VERSION,
        'commit_time': COMMIT_TIME,
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'endpoints': [
            {
                'path': '/api/data',
                'method': 'GET',
                'description': '获取 qqq 实时数据',
                'params': [],
                'example': '/api/data',
                'response_example': {
                      "change": -5.51001,
                      "change_percent": -0.8753968,
                      "exchange": "NGM",
                      "id": "QQQ",
                      "market_hours": 4,
                      "price": 623.92,
                      "price_hint": "2",
                      "quote_type": 20,
                      "time": "1769756714000"
                    }
                },
            {
                'path': '/api/status',
                'method': 'GET',
                'description': '获取连接状态和支持的基准列表',
                'params': [],
                'example': '/api/status',
                'response_example': {
                    'status': 'connected',
                    'supported_benchmarks': ['QQQ', 'SPY', 'DIA', 'IWM', 'VTI']
                }
            },
            {
                'path': '/api/benchmarks',
                'method': 'GET',
                'description': '获取支持的基准 ETF 列表',
                'params': [],
                'example': '/api/benchmarks',
                'response_example': {
                    'benchmarks': [
                        {'symbol': 'QQQ', 'name': '纳斯达克100 ETF',
                            'description': '追踪纳斯达克100指数'}
                    ]
                }
            },
            {
                'path': '/api/history/<symbol>',
                'method': 'GET',
                'description': '获取指定股票/ETF 的历史数据',
                'params': [
                    {'name': 'period', 'type': 'string', 'required': False, 'default': '1mo', 'description': '时间范围', 'options': [
                        '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'ytd', 'max']},
                    {'name': 'interval', 'type': 'string', 'required': False, 'default': '1d',
                        'description': '数据间隔', 'options': ['1m', '5m', '15m', '30m', '1h', '1d', '1wk', '1mo']}
                ],
                'example': '/api/history/QQQ?period=1mo&interval=1d',
                'response_example': {
                    'symbol': 'QQQ',
                    'period': '1mo',
                    'interval': '1d',
                    'cached': False,
                    'data': [
                        {'date': '2026-01-01', 'open': 450.0, 'high': 455.0, 'low': 448.0,
                            'close': 453.0, 'volume': 50000000, 'change_percent': 0.0}
                    ]
                }
            },
            {
                'path': '/api/intraday/<symbol>',
                'method': 'GET',
                'description': '获取指定股票的日内分钟级数据',
                'params': [
                    {'name': 'interval', 'type': 'string', 'required': False, 'default': '5m',
                        'description': '数据间隔', 'options': ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h']},
                    {'name': 'period', 'type': 'string', 'required': False,
                        'default': '1d', 'description': '时间范围', 'options': ['1d', '5d']}
                ],
                'example': '/api/intraday/SPY?interval=5m&period=1d',
                'response_example': {
                    'symbol': 'SPY',
                    'period': '1d',
                    'interval': '5m',
                    'data': [
                        {'timestamp': '2026-01-29T09:30:00-05:00', 'open': 500.0,
                            'high': 501.0, 'low': 499.5, 'close': 500.5, 'volume': 1000000}
                    ]
                }
            },
            {
                'path': '/api/compare',
                'method': 'GET',
                'description': '对比多个基准的收益率',
                'params': [
                    {'name': 'symbols', 'type': 'string', 'required': False,
                        'default': 'QQQ,SPY', 'description': '逗号分隔的股票代码'},
                    {'name': 'period', 'type': 'string', 'required': False,
                        'default': '1mo', 'description': '时间范围'}
                ],
                'example': '/api/compare?symbols=QQQ,SPY,DIA&period=3mo',
                'response_example': {
                    'period': '3mo',
                    'benchmarks': {
                        'QQQ': {'start_price': 430.0, 'end_price': 453.0, 'total_change': 5.35, 'data': []},
                        'SPY': {'start_price': 480.0, 'end_price': 500.0, 'total_change': 4.17, 'data': []}
                    }
                }
            },
            {
                'path': '/api/quote/<symbol>',
                'method': 'GET',
                'description': '获取当前实时报价',
                'params': [],
                'example': '/api/quote/QQQ',
                'response_example': {
                    'symbol': 'QQQ',
                    'name': 'Invesco QQQ Trust',
                    'price': 453.25,
                    'change': 3.15,
                    'change_percent': 0.70,
                    'volume': 45000000,
                    'previous_close': 450.10
                }
            },
            {
                'path': '/api/health',
                'method': 'GET',
                'description': '健康检查接口',
                'params': [],
                'example': '/api/health',
                'response_example': {
                    'status': 'healthy',
                    'timestamp': '2026-01-29T13:58:52'
                }
            },
            {
                'path': '/api/test',
                'method': 'GET',
                'description': '测试 API 功能，验证系统是否正常',
                'params': [],
                'example': '/api/test',
                'response_example': {
                    'timestamp': '2026-01-29T13:58:52',
                    'system': {'version': '1.0.0', 'commit_time': '...', 'environment': 'production'},
                    'tests': [
                        {'name': 'QQQ历史数据', 'status': 'success', 'data_points': 22}
                    ]
                }
            },
            {
                'path': '/api/realtime/<symbol>',
                'method': 'GET',
                'description': '获取单个符号的实时数据（自动订阅）',
                'params': [],
                'example': '/api/realtime/AAPL',
                'response_example': {
                    'symbol': 'AAPL',
                    'status': 'ok',
                    'data': {'price': 150.0, 'timestamp': '...'}
                }
            },
            {
                'path': '/api/realtime',
                'method': 'GET',
                'description': '批量获取实时数据（自动订阅）',
                'params': [
                    {'name': 'symbols', 'type': 'string',
                        'description': '逗号分隔的符号列表', 'default': '', 'required': False}
                ],
                'example': '/api/realtime?symbols=AAPL,MSFT',
                'response_example': {
                    'status': 'ok',
                    'results': {'AAPL': {'status': 'ok', 'data': {'price': 150.0, 'timestamp': '...'}}}
                }
            },
            {
                'path': '/api/subscriptions',
                'method': 'GET',
                'description': '获取当前所有订阅的符号列表',
                'params': [],
                'example': '/api/subscriptions',
                'response_example': {
                    'subscribed_symbols': ['AAPL', 'QQQ'],
                    'subscribed_count': 2
                }
            }
        ]
    })


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response


# 支持的基准指数 (已移至 config.py)

# 存储最新的数据和连接状态（原有功能）
latest_data = None
latest_data_lock = threading.Lock()
connection_status = 'disconnected'
status_lock = threading.Lock()

# 数据队列
data_queue = Queue()

# 缓存数据，避免频繁请求
data_cache = {}
cache_lock = threading.Lock()
CACHE_DURATION = 60  # 缓存60秒

# ========== 实时数据相关全局变量 ==========
# 存储所有订阅符号的最新实时数据 {symbol: {price, change, volume, timestamp, ...}}
realtime_data = {}
realtime_data_lock = threading.Lock()

# 已订阅的符号集合
subscribed_symbols = set()
subscribed_symbols_lock = threading.Lock()

# WebSocket 实例引用，用于动态添加订阅
ws_instance = None
ws_instance_lock = threading.Lock()


def get_cached_data(symbol, period='1mo'):
    """获取缓存的历史数据"""
    cache_key = f"{symbol}_{period}"
    now = time.time()

    with cache_lock:
        if cache_key in data_cache:
            cached_time, data = data_cache[cache_key]
            if now - cached_time < CACHE_DURATION:
                return data
    return None


def set_cached_data(symbol, period, data):
    """设置缓存数据"""
    cache_key = f"{symbol}_{period}"
    with cache_lock:
        data_cache[cache_key] = (time.time(), data)


# 初始化数据库
try:
    database.init_db()
except Exception as e:
    logging.error(f"Failed to init database: {e}")


def get_start_date_from_period(period):
    """根据 period 计算起始日期"""
    now = datetime.now()
    if period == '1d':
        return now - timedelta(days=1)
    if period == '5d':
        return now - timedelta(days=5)
    if period == '1mo':
        return now - timedelta(days=30)
    if period == '3mo':
        return now - timedelta(days=90)
    if period == '6mo':
        return now - timedelta(days=180)
    if period == '1y':
        return now - timedelta(days=365)
    if period == '2y':
        return now - timedelta(days=365*2)
    if period == '5y':
        return now - timedelta(days=365*5)
    if period == '10y':
        return now - timedelta(days=365*10)
    if period == 'ytd':
        return datetime(now.year, 1, 1)
    if period == 'max':
        return None
    return now - timedelta(days=30)  # Default


def fetch_historical_data(symbol, period='1mo', interval='1d'):
    """获取历史数据 (集成数据库缓存)"""
    # 目前仅对日线数据使用数据库缓存
    if interval != '1d':
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                return None

            data = []
            if len(hist) > 0:
                base_close = hist['Close'].iloc[0]
                for date, row in hist.iterrows():
                    # Intraday data index is datetime with timezone
                    date_str = date.strftime(
                        '%Y-%m-%d %H:%M') if interval != '1d' else date.strftime('%Y-%m-%d')
                    data.append({
                        'date': date_str,
                        'open': round(row['Open'], 2),
                        'high': round(row['High'], 2),
                        'low': round(row['Low'], 2),
                        'close': round(row['Close'], 2),
                        'volume': int(row['Volume']),
                        'change_percent': ((row['Close'] - base_close) / base_close) * 100
                    })
            return data
        except Exception as e:
            logging.error(f"Error fetching direct data for {symbol}: {e}")
            return None

    # === 日线数据逻辑 ===
    
    # 1. 尝试更新数据 (即使失败也继续读取数据库)
    try:
        # 获取本地最新日期
        latest_date = database.get_latest_date(symbol)

        # 决定拉取策略
        if latest_date:
            # 增量更新：从 latest_date 的下一天开始
            # start_date 包含 latest_date，yf.download 会处理，但为了稳妥我们检查日期
            start_date = latest_date # yfinance include start date
            
            # 只有当今天不是 latest_date 才拉取 (简单检查)
            if start_date != datetime.now().strftime('%Y-%m-%d'):
                logging.info(f"Incremental update for {symbol} from {start_date}")
                ticker = yf.Ticker(symbol)
                # history(start=...) 会包含 start_date，save_daily_data 使用 REPLACE INTO 所以没问题
                new_data = ticker.history(start=start_date, interval='1d')
                if not new_data.empty:
                    database.save_daily_data(symbol, new_data)
        else:
            # 全量拉取
            logging.info(f"Full fetch for {symbol}")
            ticker = yf.Ticker(symbol)
            new_data = ticker.history(period='max', interval='1d')
            if not new_data.empty:
                database.save_daily_data(symbol, new_data)

    except Exception as e:
        # 记录错误但不中断，继续尝试读取数据库
        logging.error(f"Failed to update data for {symbol} (using cached if available): {e}")

    # 2. 从数据库查询所需数据
    try:
        query_start = get_start_date_from_period(period)
        query_start_str = query_start.strftime(
            '%Y-%m-%d') if query_start else None

        df = database.get_daily_data(symbol, start_date=query_start_str)

        if df.empty:
            return None

        data = []
        base_close = df['Close'].iloc[0]

        for date, row in df.iterrows():
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'open': round(row['Open'], 2),
                'high': round(row['High'], 2),
                'low': round(row['Low'], 2),
                'close': round(row['Close'], 2),
                'volume': int(row['Volume']),
                'change_percent': ((row['Close'] - base_close) / base_close) * 100
            })

        return data

    except Exception as e:
        logging.error(f"Error in DB logic for {symbol}: {e}")
        return None


def add_subscription(symbol):
    """动态添加订阅符号"""
    global ws_instance, subscribed_symbols
    symbol = symbol.upper()

    with subscribed_symbols_lock:
        if symbol in subscribed_symbols:
            return False  # 已订阅
        subscribed_symbols.add(symbol)

    # 尝试添加到 WebSocket 订阅
    with ws_instance_lock:
        if ws_instance is not None:
            try:
                ws_instance.subscribe([symbol])
                logging.info(f"动态订阅符号: {symbol}")
                return True
            except Exception as e:
                logging.error(f"动态订阅 {symbol} 失败: {e}")
                return False
    return False


def websocket_data_handler():
    """通过WebSocket获取yfinance数据（支持动态订阅）"""
    global latest_data, connection_status, ws_instance, realtime_data

    # 默认初始订阅列表 (从 config.py 获取)
    # 清洗数据：转大写，去空，去重
    initial_symbols = [s.strip().upper()
                       for s in config.INITIAL_SYMBOLS if s.strip()]

    with subscribed_symbols_lock:
        subscribed_symbols.update(initial_symbols)

    while True:
        try:
            with status_lock:
                connection_status = 'connecting'

            # 创建WebSocket对象获取实时数据
            ws = yf.WebSocket(verbose=False)

            # 保存 WebSocket 实例引用
            with ws_instance_lock:
                ws_instance = ws

            # 设置消息处理回调
            def on_message(message):
                global latest_data, realtime_data

                # 提取符号ID
                symbol = message.get('id', '').upper()

                if symbol:
                    # 存储到实时数据字典
                    with realtime_data_lock:
                        realtime_data[symbol] = {
                            'symbol': symbol,
                            'price': message.get('price'),
                            'change': message.get('change'),
                            'change_percent': message.get('changePercent'),
                            'volume': message.get('dayVolume'),
                            'bid': message.get('bid'),
                            'ask': message.get('ask'),
                            'high': message.get('dayHigh'),
                            'low': message.get('dayLow'),
                            'open': message.get('openPrice'),
                            'previous_close': message.get('previousClose'),
                            'market_hours': message.get('marketHours'),
                            'timestamp': datetime.now().isoformat(),
                            'raw': message  # 保留原始数据
                        }

                # 保持原有功能
                with latest_data_lock:
                    latest_data = message
                with status_lock:
                    global connection_status
                    connection_status = 'connected'
                data_queue.put(message)

            # 订阅初始符号列表
            with subscribed_symbols_lock:
                symbols_to_subscribe = list(subscribed_symbols)

            ws.subscribe(symbols_to_subscribe)
            logging.info(
                f"WebSocket 已订阅 {len(symbols_to_subscribe)} 个符号: {symbols_to_subscribe}")

            # 运行WebSocket监听
            ws.listen(message_handler=on_message)

        except Exception as e:
            logging.error(f"WebSocket错误: {e}")
            with status_lock:
                connection_status = f'error: {str(e)}'
            with ws_instance_lock:
                ws_instance = None
            time.sleep(5)  # 5秒后重连


# ============ 原有接口（保持兼容） ============

@app.route('/api/data', methods=['GET'])
def get_data():
    """HTTP路由 - 返回WebSocket获取的数据，默认返回QQQ的实时数据"""
    with realtime_data_lock:
        qqq_data = realtime_data.get('QQQ')
        if qqq_data:
            return jsonify(qqq_data['raw'])
    return jsonify({'error': 'QQQ 数据尚未获取，请稍后重试'})


@app.route('/api/status', methods=['GET'])
def get_status():
    """获取连接状态"""
    global connection_status
    with status_lock:
        return jsonify({
            'status': connection_status,
            'supported_benchmarks': list(config.SUPPORTED_BENCHMARKS.keys())
        })


# ============ 新增接口 ============

@app.route('/api/benchmarks', methods=['GET'])
def get_benchmarks():
    """获取支持的基准列表"""
    benchmarks = [
        {'symbol': k, 'name': v, 'description': f'追踪 {v}'}
        for k, v in config.SUPPORTED_BENCHMARKS.items()
    ]
    return jsonify({'benchmarks': benchmarks})


@app.route('/api/history/<symbol>', methods=['GET'])
def get_history(symbol):
    """
    获取历史数据
    参数:
    - symbol: 股票/ETF 代码
    - period: 时间范围 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, ytd, max)
    - interval: 数据间隔 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)
    """
    symbol = symbol.upper()
    period = request.args.get('period', '1mo')
    interval = request.args.get('interval', '1d')

    # 检查缓存
    cached = get_cached_data(symbol, period)
    if cached:
        return jsonify({
            'symbol': symbol,
            'period': period,
            'interval': interval,
            'data': cached,
            'cached': True
        })

    # 获取新数据
    data = fetch_historical_data(symbol, period, interval)

    if data is None:
        return jsonify({'error': f'无法获取 {symbol} 的数据'}), 404

    # 缓存数据
    set_cached_data(symbol, period, data)

    return jsonify({
        'symbol': symbol,
        'period': period,
        'interval': interval,
        'data': data,
        'cached': False
    })


@app.route('/api/intraday/<symbol>', methods=['GET'])
def get_intraday(symbol):
    """
    获取指定股票的日内（分钟级）数据
    参数:
      - interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h (默认 5m)
      - period: 1d, 5d (默认 1d)
    """
    try:
        symbol = symbol.upper()
        interval = request.args.get('interval', '5m')
        period = request.args.get('period', '1d')

        # 验证 interval 和 period
        valid_intervals = ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h']
        valid_periods = ['1d', '5d']

        if interval not in valid_intervals:
            return jsonify({'error': f'Invalid interval. Valid options: {", ".join(valid_intervals)}'}), 400
        if period not in valid_periods:
            return jsonify({'error': f'Invalid period for intraday. Valid options: {", ".join(valid_periods)}'}), 400

        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)

        if hist.empty:
            return jsonify({'error': f'No intraday data found for {symbol}'}), 404

        data = []
        for index, row in hist.iterrows():
            data.append({
                'timestamp': index.isoformat(),
                'open': row['Open'],
                'high': row['High'],
                'low': row['Low'],
                'close': row['Close'],
                'volume': row['Volume']
            })

        return jsonify({
            'symbol': symbol,
            'period': period,
            'interval': interval,
            'data': data
        })

    except Exception as e:
        logging.error(f"Error fetching intraday for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/compare', methods=['GET'])
def compare_benchmarks():
    """
    对比多个基准的收益率
    参数:
    - symbols: 逗号分隔的代码列表 (如 QQQ,SPY,DIA)
    - period: 时间范围
    """
    symbols_str = request.args.get('symbols', 'QQQ,SPY')
    period = request.args.get('period', '1mo')

    symbols = [s.strip().upper() for s in symbols_str.split(',')]

    result = {}
    for symbol in symbols:
        # 尝试使用内存缓存
        data = get_cached_data(symbol, period)
        
        if not data:
            data = fetch_historical_data(symbol, period)
            # 如果获取成功，写入缓存
            if data:
                set_cached_data(symbol, period, data)
                
        if data:
            result[symbol] = {
                'data': data,
                'start_price': data[0]['close'] if data else 0,
                'end_price': data[-1]['close'] if data else 0,
                'total_change': data[-1]['change_percent'] if data else 0
            }

    return jsonify({
        'period': period,
        'benchmarks': result
    })


@app.route('/api/quote/<symbol>', methods=['GET'])
def get_quote(symbol):
    """获取当前报价"""
    symbol = symbol.upper()
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        return jsonify({
            'symbol': symbol,
            'name': info.get('shortName', symbol),
            'price': info.get('regularMarketPrice', 0),
            'change': info.get('regularMarketChange', 0),
            'change_percent': info.get('regularMarketChangePercent', 0),
            'volume': info.get('regularMarketVolume', 0),
            'previous_close': info.get('regularMarketPreviousClose', 0),
        })
    except Exception as e:
        logging.error(f"获取 {symbol} 报价失败: {e}")
        return jsonify({'error': str(e)}), 500


# ============ 实时数据接口 ============

@app.route('/api/realtime/<symbol>', methods=['GET'])
def get_realtime(symbol):
    """
    获取单个符号的实时数据
    - 如果符号不在订阅列表中，自动添加订阅
    - 返回 WebSocket 收到的最新实时数据
    """
    symbol = symbol.upper()

    # 检查是否需要添加订阅
    with subscribed_symbols_lock:
        is_subscribed = symbol in subscribed_symbols

    if not is_subscribed:
        add_subscription(symbol)
        # 刚订阅，可能还没有数据
        return jsonify({
            'symbol': symbol,
            'status': 'subscribed',
            'message': f'{symbol} 已添加到订阅列表，请稍后再查询获取数据',
            'data': None
        })

    # 获取已有的实时数据
    with realtime_data_lock:
        data = realtime_data.get(symbol)

    if data:
        return jsonify({
            'symbol': symbol,
            'status': 'ok',
            'data': data
        })
    else:
        return jsonify({
            'symbol': symbol,
            'status': 'waiting',
            'message': f'{symbol} 已订阅但尚未收到数据',
            'data': None
        })


@app.route('/api/realtime', methods=['GET'])
def get_realtime_batch():
    """
    批量获取实时数据
    参数:
    - symbols: 逗号分隔的代码列表 (如 AAPL,MSFT,NVDA)
    返回所有已订阅符号的数据，自动订阅新符号
    """
    symbols_str = request.args.get('symbols', '')

    if not symbols_str:
        # 返回所有已订阅符号的数据
        with realtime_data_lock:
            all_data = dict(realtime_data)
        with subscribed_symbols_lock:
            all_subscribed = list(subscribed_symbols)

        return jsonify({
            'status': 'ok',
            'subscribed_count': len(all_subscribed),
            'data_count': len(all_data),
            'subscribed_symbols': all_subscribed,
            'data': all_data
        })

    # 解析请求的符号列表
    requested_symbols = [s.strip().upper()
                         for s in symbols_str.split(',') if s.strip()]

    result = {}
    newly_subscribed = []

    for symbol in requested_symbols:
        # 检查是否需要添加订阅
        with subscribed_symbols_lock:
            is_subscribed = symbol in subscribed_symbols

        if not is_subscribed:
            add_subscription(symbol)
            newly_subscribed.append(symbol)
            result[symbol] = {
                'status': 'subscribed',
                'message': '刚添加订阅，尚无数据',
                'data': None
            }
        else:
            # 获取实时数据
            with realtime_data_lock:
                data = realtime_data.get(symbol)

            if data:
                result[symbol] = {
                    'status': 'ok',
                    'data': data
                }
            else:
                result[symbol] = {
                    'status': 'waiting',
                    'message': '已订阅但尚未收到数据',
                    'data': None
                }

    return jsonify({
        'status': 'ok',
        'requested_count': len(requested_symbols),
        'newly_subscribed': newly_subscribed,
        'results': result
    })


@app.route('/api/subscriptions', methods=['GET'])
def get_subscriptions():
    """获取当前所有订阅的符号列表"""
    with subscribed_symbols_lock:
        symbols = list(subscribed_symbols)
    with realtime_data_lock:
        data_symbols = list(realtime_data.keys())

    return jsonify({
        'subscribed_symbols': symbols,
        'subscribed_count': len(symbols),
        'symbols_with_data': data_symbols,
        'data_count': len(data_symbols)
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/test', methods=['GET'])
def test_api():
    """测试接口 - 快速验证API功能"""
    results = {
        'timestamp': datetime.now().isoformat(),
        'system': {
            'version': VERSION,
            'commit_time': COMMIT_TIME,
            'environment': os.getenv('FLASK_ENV', 'production')
        },
        'tests': []
    }

    # 测试1: 获取QQQ历史数据
    try:
        data = fetch_historical_data('QQQ', '5d')
        results['tests'].append({
            'name': 'QQQ历史数据',
            'status': 'success' if data else 'failed',
            'data_points': len(data) if data else 0
        })
    except Exception as e:
        results['tests'].append({
            'name': 'QQQ历史数据',
            'status': 'error',
            'error': str(e)
        })

    # 测试2: 获取SPY报价
    try:
        ticker = yf.Ticker('SPY')
        price = ticker.info.get('regularMarketPrice', 0)
        results['tests'].append({
            'name': 'SPY当前报价',
            'status': 'success' if price > 0 else 'failed',
            'price': price
        })

    except Exception as e:
        results['tests'].append({
            'name': 'SPY当前报价',
            'status': 'error',
            'error': str(e)
        })

    # 测试3: 实时数据配置检查
    with subscribed_symbols_lock:
        subs_count = len(subscribed_symbols)

    results['tests'].append({
        'name': '实时订阅配置',
        'status': 'success' if subs_count > 0 else 'warning',
        'subscribed_count': subs_count,
        'config_initial_count': len(config.INITIAL_SYMBOLS)
    })

    return jsonify(results)


if __name__ == '__main__':
    # 启动WebSocket线程获取数据（原有功能）
    ws_thread = threading.Thread(target=websocket_data_handler, daemon=True)
    ws_thread.start()

    logging.info("=" * 50)
    logging.info("Yahoo Finance API 服务启动")
    logging.info("=" * 50)
    logging.info("原有接口:")
    logging.info("  GET /api/data              - WebSocket实时数据")
    logging.info("  GET /api/status            - 连接状态")
    logging.info("新增接口:")
    logging.info("  GET /api/benchmarks        - 获取支持的基准列表")
    logging.info("  GET /api/history/<symbol>  - 获取历史数据")
    logging.info("  GET /api/compare           - 对比多个基准")
    logging.info("  GET /api/quote/<symbol>    - 获取当前报价")
    logging.info("  GET /api/test              - 测试API功能")
    logging.info("  GET /api/health            - 健康检查")
    logging.info("实时数据接口:")
    logging.info("  GET /api/realtime/<symbol> - 获取单个符号实时数据")
    logging.info("  GET /api/realtime?symbols= - 批量获取实时数据")
    logging.info("  GET /api/subscriptions     - 查看当前订阅列表")
    logging.info("=" * 50)
    logging.info("访问 http://localhost:5000/api/test 测试API")
    logging.info("=" * 50)

    # 启动Flask服务器
    import logging as werkzeug_logging
    werkzeug_logging.getLogger('werkzeug').setLevel(logging.INFO)

    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
