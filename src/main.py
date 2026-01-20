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


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response


# 支持的基准指数
SUPPORTED_BENCHMARKS = {
    'QQQ': 'QQQ',       # 纳斯达克100 ETF
    'SPY': 'SPY',       # 标普500 ETF
    'DIA': 'DIA',       # 道琼斯工业 ETF
    'IWM': 'IWM',       # 罗素2000 ETF
    'VTI': 'VTI',       # 全美股市 ETF
}

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
    try:
        # 1. 获取本地最新日期
        latest_date = database.get_latest_date(symbol)

        # 2. 决定拉取策略
        if latest_date:
            # 增量更新：从 latest_date 的下一天开始
            # yfinance 的 start 是包含的，所以如果直接用 latest_date 会重复一天，但 save_daily_data 处理了重复
            # 也可以简单地拉取 '1mo' 或更短，只要覆盖 new range
            # 最稳妥是指定 start date
            start_date = (datetime.strptime(latest_date, '%Y-%m-%d') +
                          timedelta(days=0)).strftime('%Y-%m-%d')
            logging.info(f"Incremental update for {symbol} from {start_date}")
            # 使用 yf.download 可能比 ticker.history 更适合指定日期，但 ticker.history(start=...) 也行
            ticker = yf.Ticker(symbol)
            # 只有当今天不是 latest_date 才拉取
            if start_date != datetime.now().strftime('%Y-%m-%d'):
                new_data = ticker.history(start=start_date, interval='1d')
                database.save_daily_data(symbol, new_data)
        else:
            # 全量拉取
            logging.info(f"Full fetch for {symbol}")
            ticker = yf.Ticker(symbol)
            new_data = ticker.history(period='max', interval='1d')
            database.save_daily_data(symbol, new_data)

        # 3. 从数据库查询所需数据
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


def websocket_data_handler():
    """通过WebSocket获取yfinance数据（原有功能）"""
    global latest_data, connection_status
    while True:
        try:
            with status_lock:
                connection_status = 'connecting'

            # 创建WebSocket对象获取实时数据
            ws = yf.WebSocket(verbose=False)

            # 设置消息处理回调
            def on_message(message):
                print(f"收到数据: {message}")
                global latest_data
                with latest_data_lock:
                    latest_data = message
                with status_lock:
                    global connection_status
                    connection_status = 'connected'
                data_queue.put(message)

            ws.subscribe(['qqq'])

            # 运行WebSocket监听
            ws.listen(message_handler=on_message)

        except Exception as e:
            logging.error(f"WebSocket错误: {e}")
            with status_lock:
                connection_status = f'error: {str(e)}'
            time.sleep(5)  # 5秒后重连


# ============ 原有接口（保持兼容） ============

@app.route('/api/data', methods=['GET'])
def get_data():
    """HTTP路由 - 原封不动返回WebSocket获取的数据"""
    global latest_data
    with latest_data_lock:
        if latest_data is not None:
            return latest_data
    return {}


@app.route('/api/status', methods=['GET'])
def get_status():
    """获取连接状态"""
    global connection_status
    with status_lock:
        return jsonify({
            'status': connection_status,
            'supported_benchmarks': list(SUPPORTED_BENCHMARKS.keys())
        })


# ============ 新增接口 ============

@app.route('/api/benchmarks', methods=['GET'])
def get_benchmarks():
    """获取支持的基准列表"""
    benchmarks = [
        {'symbol': 'QQQ', 'name': '纳斯达克100 ETF', 'description': '追踪纳斯达克100指数'},
        {'symbol': 'SPY', 'name': '标普500 ETF', 'description': '追踪标普500指数'},
        {'symbol': 'DIA', 'name': '道琼斯ETF', 'description': '追踪道琼斯工业平均指数'},
        {'symbol': 'IWM', 'name': '罗素2000 ETF', 'description': '追踪小盘股指数'},
        {'symbol': 'VTI', 'name': '全美股市ETF', 'description': '追踪整体美股市场'},
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
        data = fetch_historical_data(symbol, period)
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
    logging.info("=" * 50)
    logging.info("访问 http://localhost:5000/api/test 测试API")
    logging.info("=" * 50)

    # 启动Flask服务器
    import logging as werkzeug_logging
    werkzeug_logging.getLogger('werkzeug').setLevel(logging.ERROR)

    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
