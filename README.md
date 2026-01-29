# Yahoo Finance Server

基于 Flask 和 yfinance 的股票数据服务器。

## 🚀 快速开始

```bash
# 本地运行
pip install -r requirements.txt
cd src && python main.py

# Docker运行
docker compose -f deploy/docker-compose.yml up -d --build
```

## 📁 项目结构

```text
├── src/                    # 源代码
│   ├── main.py             # Flask API主程序
│   └── database.py         # 数据库操作
├── deploy/                 # 部署配置
│   ├── Dockerfile          # Docker镜像
│   ├── docker-compose.yml  # Docker Compose
│   ├── yahoo.service       # systemd服务
│   └── ansible/            # Ansible远程部署
├── scripts/                # 脚本
│   ├── setup.sh            # 安装脚本
│   └── deploy.sh           # 部署脚本
├── tests/                  # 测试
├── .github/workflows/      # CI/CD
└── requirements.txt        # Python依赖
```

## 📡 API 接口

### API 文档 (根路径)

`GET /`

返回服务信息和完整 API 文档，包含所有端点的详细说明。

```json
{
  "service": "Yahoo Finance API",
  "version": "e4d2a1b",
  "commit_time": "2026-01-20 14:30:00 +0800",
  "status": "running",
  "timestamp": "2026-01-20T14:35:00.123456",
  "endpoints": [
    {
      "path": "/api/history/<symbol>",
      "method": "GET",
      "description": "获取指定股票/ETF 的历史数据",
      "params": [
        {"name": "period", "type": "string", "required": false, "default": "1mo", "description": "时间范围", "options": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"]},
        {"name": "interval", "type": "string", "required": false, "default": "1d", "description": "数据间隔", "options": ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"]}
      ],
      "example": "/api/history/QQQ?period=1mo&interval=1d",
      "response_example": {"symbol": "QQQ", "period": "1mo", "interval": "1d", "cached": false, "data": [{"date": "2026-01-01", "open": 450.0, "close": 453.0}]}
    }
  ]
}
```

> 完整文档请访问 `GET /` 端点查看所有 9 个 API 的详细说明。

### 历史K线数据

`GET /api/history/<symbol>?period=5d`

```json
{
  "symbol": "QQQ",
  "data": [
    {"date": "2026-01-15", "open": 520.5, "high": 525.3, "low": 518.2, "close": 524.1, "volume": 45230000}
  ],
  "cached": true
}
```

### 日内分时数据

`GET /api/intraday/<symbol>?interval=5m`

```json
{
  "symbol": "QQQ",
  "data": [
    {"datetime": "2026-01-20 09:30:00", "open": 525.0, "high": 526.2, "low": 524.5, "close": 525.8, "volume": 1250000}
  ]
}
```

### 实时报价

`GET /api/quote/<symbol>`

```json
{
  "symbol": "SPY",
  "price": 598.25,
  "change": 3.45,
  "changePercent": 0.58,
  "volume": 52340000
}
```

### 多基准对比

`GET /api/compare?symbols=QQQ,SPY&period=1mo`

```json
{
  "period": "1mo",
  "data": {
    "QQQ": {"return": 5.23, "startPrice": 498.5, "endPrice": 524.5},
    "SPY": {"return": 3.12, "startPrice": 580.2, "endPrice": 598.3}
  }
}
```

### 其他接口

| 接口 | 说明 |
|------|------|
| `GET /api/benchmarks` | 基准列表 |
| `GET /api/health` | 健康检查 |
| `GET /api/status` | 连接状态 |

## 🔧 CI/CD

### GitHub Secrets

| Secret | 说明 | 必需 |
|--------|------|------|
| `DOCKERHUB_USERNAME` | Docker Hub用户名 | Docker推送 |
| `DOCKERHUB_TOKEN` | Docker Hub Token | Docker推送 |
| `SERVER_HOST` | 服务器IP | Ansible部署 |
| `SERVER_USER` | SSH用户名 | Ansible部署 |
| `SSH_PRIVATE_KEY` | SSH私钥 | Ansible部署 |

配置了对应 Secrets 后自动执行，未配置则跳过。

## 📦 Ansible部署

```bash
cd deploy/ansible

# 首次安装
ansible-playbook playbooks/setup.yml --ask-become-pass

# 从Docker Hub部署
ansible-playbook playbooks/deploy.yml -e use_dockerhub=true

# 检查状态
ansible-playbook playbooks/status.yml
```

## 📝 许可证

见 [LICENSE](LICENSE)