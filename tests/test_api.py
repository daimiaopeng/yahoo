"""
Yahoo Finance API 测试脚本
测试所有 API 接口是否正常工作
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"


def print_header(title):
    print("\n" + "=" * 50)
    print(f"  {title}")
    print("=" * 50)


def test_health():
    """测试健康检查接口"""
    print_header("测试 /api/health")
    try:
        resp = requests.get(f"{BASE_URL}/api/health", timeout=5)
        print(f"状态码: {resp.status_code}")
        print(f"响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
        return resp.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_benchmarks():
    """测试基准列表接口"""
    print_header("测试 /api/benchmarks")
    try:
        resp = requests.get(f"{BASE_URL}/api/benchmarks", timeout=5)
        print(f"状态码: {resp.status_code}")
        data = resp.json()
        print(f"支持的基准数量: {len(data.get('benchmarks', []))}")
        for b in data.get('benchmarks', []):
            print(f"  - {b['symbol']}: {b['name']}")
        return resp.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_status():
    """测试状态接口"""
    print_header("测试 /api/status")
    try:
        resp = requests.get(f"{BASE_URL}/api/status", timeout=5)
        print(f"状态码: {resp.status_code}")
        print(f"响应: {json.dumps(resp.json(), indent=2, ensure_ascii=False)}")
        return resp.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_history(symbol="QQQ", period="5d"):
    """测试历史数据接口"""
    print_header(f"测试 /api/history/{symbol}?period={period}")
    try:
        resp = requests.get(
            f"{BASE_URL}/api/history/{symbol}?period={period}", timeout=30)
        print(f"状态码: {resp.status_code}")
        data = resp.json()

        if 'error' in data:
            print(f"错误: {data['error']}")
            return False

        points = data.get('data', [])
        print(f"数据点数量: {len(points)}")
        print(f"是否缓存: {data.get('cached', False)}")

        if points:
            print(f"\n最近数据:")
            for p in points[-3:]:
                print(
                    f"  {p['date']}: 收盘 ${p['close']:.2f}, 涨跌 {p['change_percent']:+.2f}%")

        return resp.status_code == 200 and len(points) > 0
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_quote(symbol="SPY"):
    """测试当前报价接口"""
    print_header(f"测试 /api/quote/{symbol}")
    try:
        resp = requests.get(f"{BASE_URL}/api/quote/{symbol}", timeout=30)
        print(f"状态码: {resp.status_code}")
        data = resp.json()

        if 'error' in data:
            print(f"错误: {data['error']}")
            return False

        print(f"股票: {data.get('name', symbol)}")
        print(f"当前价格: ${data.get('price', 0):.2f}")
        print(
            f"涨跌: {data.get('change', 0):+.2f} ({data.get('change_percent', 0):+.2f}%)")
        print(f"成交量: {data.get('volume', 0):,}")

        return resp.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_compare():
    """测试对比接口"""
    print_header("测试 /api/compare?symbols=QQQ,SPY,DIA")
    try:
        resp = requests.get(
            f"{BASE_URL}/api/compare?symbols=QQQ,SPY,DIA&period=1mo", timeout=60)
        print(f"状态码: {resp.status_code}")
        data = resp.json()

        benchmarks = data.get('benchmarks', {})
        print(f"\n各基准月度表现:")
        for symbol, info in benchmarks.items():
            change = info.get('total_change', 0)
            print(f"  {symbol}: {change:+.2f}%")

        return resp.status_code == 200 and len(benchmarks) > 0
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_cache_functionality():
    """测试缓存功能"""
    print_header("测试数据缓存")
    symbol = "QQQ"
    period = "1mo"

    # 第一次请求
    print("1. 第一次请求 (期望: cached=False)")
    start_time = datetime.now()
    resp1 = requests.get(f"{BASE_URL}/api/history/{symbol}?period={period}")
    duration1 = (datetime.now() - start_time).total_seconds()

    if resp1.status_code != 200:
        print(f"请求失败: {resp1.status_code}")
        return False

    data1 = resp1.json()
    is_cached1 = data1.get('cached', False)
    print(f"   耗时: {duration1:.3f}s, Cached: {is_cached1}")

    # update main.py to actually return 'cached' field if it doesn't already?
    # Current main.py returns cached=True if hit, cached=False if fetch new.

    # 第二次请求
    print("2. 第二次请求 (期望: cached=True)")
    start_time = datetime.now()
    resp2 = requests.get(f"{BASE_URL}/api/history/{symbol}?period={period}")
    duration2 = (datetime.now() - start_time).total_seconds()

    if resp2.status_code != 200:
        return False

    data2 = resp2.json()
    is_cached2 = data2.get('cached', False)
    print(f"   耗时: {duration2:.3f}s, Cached: {is_cached2}")

    # 验证
    # 如果第一次已经是 cached=True (可能因为其他测试跑过), 那只要第二次也是 True 且很快就行
    # 但严格来说，第一次可能是 False 或 True，第二次必须是 True

    if is_cached2 is not True:
        print("❌ 缓存未生效 (第二次请求 cached 字段应为 True)")
        return False

    if duration2 > duration1 and duration1 > 0.5:
        print("⚠️ 警告: 缓存响应比首次请求更慢 (可能是本地网络抖动)")

    return True


def main():
    print("\n" + "🚀" * 20)
    print("  Yahoo Finance API 测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🚀" * 20)

    results = []

    # 运行所有测试
    results.append(("健康检查", test_health()))
    results.append(("基准列表", test_benchmarks()))
    results.append(("连接状态", test_status()))
    results.append(("QQQ历史数据", test_history("QQQ", "5d")))
    results.append(("SPY报价", test_quote("SPY")))
    results.append(("多基准对比", test_compare()))
    results.append(("内部验证接口", test_internal_test_endpoint()))
    results.append(("实时数据缓存", test_realtime_data()))
    results.append(("日内分钟数据", test_intraday_endpoint()))
    results.append(("API数据缓存", test_cache_functionality()))


def test_internal_test_endpoint():
    """测试内部验证接口 /api/test"""
    print_header("测试 /api/test")
    try:
        resp = requests.get(f"{BASE_URL}/api/test", timeout=30)
        print(f"状态码: {resp.status_code}")
        data = resp.json()

        tests = data.get('tests', [])
        print(f"验证项数量: {len(tests)}")
        for t in tests:
            status = "✅" if t['status'] == 'success' else "❌"
            print(f"  - {t['name']}: {status}")

        return resp.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_intraday_endpoint():
    """测试日内数据接口 /api/intraday"""
    print_header("测试 /api/intraday/QQQ")
    try:
        url = f"{BASE_URL}/api/intraday/QQQ?interval=5m&period=1d"
        print(f"请求: {url}")
        resp = requests.get(url, timeout=10)
        print(f"状态码: {resp.status_code}")

        if resp.status_code != 200:
            return False

        data = resp.json()
        points = len(data.get('data', []))
        print(f"获取到的分钟数据点: {points}")
        return points > 0
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_realtime_data():
    """测试实时数据接口 /api/data"""
    print_header("测试 /api/data")
    try:
        # 这个接口返回服务器从 Yahoo WebSocket 接收到的最新数据
        resp = requests.get(f"{BASE_URL}/api/data", timeout=5)
        print(f"状态码: {resp.status_code}")
        print(f"响应类型: {type(resp.json())}")
        # 注意：如果刚启动可能为空，这里只验证接口通不通，不强制要求有数据
        # 只要返回 200 就算通过
        return resp.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False

    # 打印汇总
    print_header("测试结果汇总")
    passed = 0
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{len(results)} 通过")

    import sys
    if passed == len(results):
        print("\n🎉 所有测试通过！API 服务正常运行。")
        sys.exit(0)
    else:
        print("\n⚠️ 部分测试失败，请检查网络连接或服务状态。")
        sys.exit(1)


if __name__ == "__main__":
    main()
