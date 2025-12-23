# Yahoo Finance Server

基于Flask和yfinance的实时股票数据服务器。

## 功能特性

- 通过WebSocket实时获取股票数据（当前监控QQQ）
- 提供RESTful API接口
- 自动重连机制
- 日志记录
- 支持自动部署和更新

## 快速开始

### 本地开发

1. 克隆仓库
```bash
git clone https://github.com/daimiaopeng/yahoo.git
cd yahoo
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 运行服务器
```bash
python main.py
```

服务器将在 `http://localhost:5000` 上运行。

### 服务器部署

使用自动安装脚本进行快速部署：

```bash
./setup.sh
```

该脚本将自动：
- 创建Python虚拟环境
- 安装依赖
- 配置systemd服务
- 设置自动部署（可选）

详细部署说明请查看 [DEPLOYMENT.md](DEPLOYMENT.md)

## API接口

### 获取实时数据
```
GET /api/data
```

返回最新的WebSocket数据。

### 获取连接状态
```
GET /api/status
```

返回当前连接状态：
```json
{
  "status": "connected"
}
```

## 自动部署

项目包含自动部署功能，可以：
- 定期检查GitHub更新
- 自动拉取最新代码
- 自动重启服务

使用cron设置定时检查（每5分钟）：
```bash
crontab -e
# 添加：
*/5 * * * * cd /path/to/yahoo && ./deploy.sh >> ~/yahoo-deploy.log 2>&1
```

## 文件说明

- `main.py` - 主程序
- `requirements.txt` - Python依赖
- `setup.sh` - 自动安装脚本
- `deploy.sh` - 自动部署脚本
- `yahoo.service` - systemd服务配置
- `DEPLOYMENT.md` - 详细部署文档

## 许可证

见 [LICENSE](LICENSE) 文件