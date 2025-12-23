from flask import Flask, jsonify
import threading
import yfinance as yf
from queue import Queue
from datetime import datetime
import time
import sys
import os
import logging

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

# 存储最新的数据和连接状态
latest_data = None
latest_data_lock = threading.Lock()
connection_status = 'disconnected'
status_lock = threading.Lock()

# 数据队列
data_queue = Queue()

def websocket_data_handler():
    """通过WebSocket获取yfinance数据"""
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
            'status': connection_status
        })

if __name__ == '__main__':
    # 启动WebSocket线程获取数据
    ws_thread = threading.Thread(target=websocket_data_handler, daemon=True)
    ws_thread.start()
    
    logging.info("服务器启动成功，监听端口 5000")
    logging.info("访问 http://localhost:5000/api/data 获取数据")
    logging.info("访问 http://localhost:5000/api/status 获取状态")
    
    # 启动Flask服务器，关闭Werkzeug日志
    import logging as werkzeug_logging
    werkzeug_logging.getLogger('werkzeug').setLevel(logging.ERROR)
    
    # 后台运行模式
    app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
