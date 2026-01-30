# 测试 yfinance WebSocket 订阅 200 个热门符号
import yfinance as yf
import time
import threading

# 200个盘前盘后活跃的热门符号（包括主要ETF、科技股、热门个股）
SYMBOLS_200 = [
    # 主要ETF (盘前盘后活跃)
    'SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'VOO', 'TQQQ', 'SQQQ', 'SPXU', 'SPXL',
    'XLF', 'XLE', 'XLK', 'XLV', 'XLI', 'XLP', 'XLU', 'XLB', 'XLY', 'XLRE',
    'GLD', 'SLV', 'USO', 'UNG', 'TLT', 'HYG', 'LQD', 'JNK', 'AGG', 'BND',
    'EEM', 'EFA', 'VWO', 'VEA', 'IEMG', 'FXI', 'KWEB', 'MCHI', 'EWJ', 'EWT',
    'ARKK', 'ARKG', 'ARKW', 'ARKF', 'ARKQ', 'SMH', 'SOXX', 'XBI', 'IBB', 'XOP',

    # 科技巨头 (盘前盘后最活跃)
    'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'NVDA', 'TSLA', 'AMD', 'INTC',
    'AVGO', 'QCOM', 'TXN', 'MU', 'AMAT', 'LRCX', 'KLAC', 'MRVL', 'NXPI', 'ON',
    'CRM', 'ORCL', 'SAP', 'ADBE', 'NOW', 'INTU', 'WDAY', 'TEAM', 'ZS', 'CRWD',
    'SNOW', 'DDOG', 'PLTR', 'NET', 'MDB', 'ZM', 'DOCU', 'OKTA', 'TWLO', 'SQ',

    # 热门消费和通信
    'NFLX', 'DIS', 'CMCSA', 'WBD', 'PARA', 'ROKU', 'SPOT', 'LYFT', 'UBER', 'DASH',
    'ABNB', 'BKNG', 'EXPE', 'MAR', 'HLT', 'LVS', 'MGM', 'WYNN', 'DKNG', 'PENN',
    'SBUX', 'MCD', 'CMG', 'DPZ', 'YUM', 'QSR', 'WEN', 'WING', 'SHAK', 'CAVA',

    # 电动车和新能源
    'RIVN', 'LCID', 'NIO', 'XPEV', 'LI', 'F', 'GM', 'STLA', 'HMC', 'TM',
    'ENPH', 'SEDG', 'FSLR', 'RUN', 'PLUG', 'BE', 'CHPT', 'BLNK', 'QS', 'LCID',

    # 金融和支付
    'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'SCHW', 'BLK', 'AXP', 'COF',
    'V', 'MA', 'PYPL', 'SQ', 'COIN', 'HOOD', 'AFRM', 'SOFI', 'UPST', 'NU',

    # 医药和生物科技
    'JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'UNH', 'CVS', 'CI', 'HUM', 'ANTM',
    'MRNA', 'BNTX', 'REGN', 'VRTX', 'GILD', 'BIIB', 'AMGN', 'BMY', 'AZN', 'NVO',

    # 零售和电商
    'WMT', 'TGT', 'COST', 'HD', 'LOW', 'AMZN', 'EBAY', 'ETSY', 'SHOP', 'W',
    'NKE', 'LULU', 'GPS', 'ANF', 'URBN', 'RVLV', 'BIRD', 'FIGS', 'ONON', 'DECK',

    # 能源和材料
    'XOM', 'CVX', 'COP', 'OXY', 'SLB', 'HAL', 'BKR', 'MPC', 'VLO', 'PSX',
    'FCX', 'NEM', 'GOLD', 'AA', 'CLF', 'X', 'NUE', 'STLD', 'RS', 'ATI',
]

# 尝试导入 src.config (假设运行路径正确) 或直接定义
try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    import config
    CONFIG_SYMBOLS = config.INITIAL_SYMBOLS
except ImportError:
    print("Warning: Could not import config, using hardcoded list only.")
    CONFIG_SYMBOLS = []

# 合并配置中的符号
SYMBOLS_200.extend(CONFIG_SYMBOLS)
# 去重
SYMBOLS_200 = list(dict.fromkeys(SYMBOLS_200))[:200]


def test_200_symbols():
    """直接订阅200个热门符号测试"""
    received_symbols = set()
    message_count = 0
    test_complete = threading.Event()

    print(f"准备订阅 {len(SYMBOLS_200)} 个热门符号...")
    print(f"符号列表前20个: {SYMBOLS_200[:20]}")

    def on_message(message):
        nonlocal message_count
        message_count += 1
        symbol = message.get('id', 'N/A')
        price = message.get('price', 'N/A')

        if 'id' in message:
            received_symbols.add(message['id'])

        print(
            f"[{message_count}] 符号: {symbol}, 价格: {price}, 已收到不同符号数: {len(received_symbols)}")

    try:
        ws = yf.WebSocket(verbose=True)

        print(f"\n开始订阅 {len(SYMBOLS_200)} 个符号...")
        ws.subscribe(SYMBOLS_200)
        print("订阅请求已发送！")
        print("按 Ctrl+C 手动停止测试...\n")

        # 直接在主线程监听，Ctrl+C 会触发 KeyboardInterrupt
        try:
            ws.listen(message_handler=on_message)
        except KeyboardInterrupt:
            print("\n\n用户手动停止测试...")

        # 关闭连接
        ws.close()

        print(f"\n{'='*60}")
        print(f"测试结果:")
        print(f"{'='*60}")
        print(f"订阅符号数: {len(SYMBOLS_200)}")
        print(f"收到消息数: {message_count}")
        print(f"收到不同符号数: {len(received_symbols)}")
        print(f"收到数据的符号: {sorted(received_symbols)}")

        if len(received_symbols) < len(SYMBOLS_200):
            missing = set(SYMBOLS_200) - received_symbols
            print(f"\n⚠️ 缺失符号 ({len(missing)}个): {sorted(missing)[:20]}... ")
        else:
            print(f"\n✓ 成功收到所有 {len(SYMBOLS_200)} 个符号的数据!")

    except Exception as e:
        print(f"测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("="*60)
    print("测试 yfinance WebSocket 订阅 200 个热门符号")
    print("="*60)
    print("包含: ETF、科技股、电动车、中概股等盘前盘后活跃标的")

    test_200_symbols()

    print("\n测试完成!")
