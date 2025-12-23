# Yahoo Finance Server - 部署文档

本文档说明如何在服务器上部署Yahoo Finance Server，并实现自动检查GitHub更新、构建和运行新版本。

## 系统要求

- Linux 服务器 (Ubuntu/Debian/CentOS)
- Python 3.8+
- Git
- systemd (用于服务管理)
- sudo 权限

## 部署步骤

### 1. 克隆代码仓库

```bash
cd /home/runner/work/yahoo
git clone https://github.com/daimiaopeng/yahoo.git
cd yahoo
```

### 2. 创建Python虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置systemd服务

将服务文件复制到systemd目录：

```bash
sudo cp yahoo.service /etc/systemd/system/
```

**注意**: 如果你的用户名不是 `runner` 或项目路径不同，需要编辑 `/etc/systemd/system/yahoo.service` 文件，修改以下内容：

- `User=runner` - 改为你的用户名
- `WorkingDirectory=/home/runner/work/yahoo/yahoo` - 改为你的项目路径
- `Environment="PATH=..."` - 改为你的虚拟环境路径
- `ExecStart=/home/runner/work/yahoo/yahoo/venv/bin/python main.py` - 改为你的Python路径

重新加载systemd配置：

```bash
sudo systemctl daemon-reload
```

### 5. 启动服务

```bash
sudo systemctl start yahoo
sudo systemctl enable yahoo  # 设置开机自启
```

查看服务状态：

```bash
sudo systemctl status yahoo
```

查看日志：

```bash
sudo journalctl -u yahoo -f
```

### 6. 设置自动部署

为了实现自动检查GitHub更新并部署，有两种方法：

#### 方法1: 使用cron定时任务 (推荐用于小型项目)

给部署脚本添加执行权限：

```bash
chmod +x deploy.sh
```

添加cron任务，每5分钟检查一次更新：

```bash
crontab -e
```

添加以下行：

```bash
*/5 * * * * cd /home/runner/work/yahoo/yahoo && ./deploy.sh >> /var/log/yahoo-deploy.log 2>&1
```

查看部署日志：

```bash
tail -f /var/log/yahoo-deploy.log
```

#### 方法2: 使用GitHub Webhooks (推荐用于生产环境)

如果你希望在每次push代码时立即部署，可以使用GitHub Webhooks：

1. 在服务器上安装webhook接收器，例如 `webhook` 或 `adnanh/webhook`
2. 配置webhook监听端口
3. 在GitHub仓库设置中添加webhook URL
4. 当收到webhook请求时执行 `deploy.sh`

详细的webhook配置超出本文档范围，请参考GitHub Webhooks文档。

### 7. 手动部署

如果需要手动部署新版本：

```bash
cd /home/runner/work/yahoo/yahoo
./deploy.sh
```

## 服务管理命令

启动服务：
```bash
sudo systemctl start yahoo
```

停止服务：
```bash
sudo systemctl stop yahoo
```

重启服务：
```bash
sudo systemctl restart yahoo
```

查看状态：
```bash
sudo systemctl status yahoo
```

查看日志：
```bash
sudo journalctl -u yahoo -f
```

禁用开机自启：
```bash
sudo systemctl disable yahoo
```

## 访问API

服务默认运行在 5000 端口：

- 获取数据: `http://你的服务器IP:5000/api/data`
- 获取状态: `http://你的服务器IP:5000/api/status`

## 防火墙配置

如果需要从外部访问，需要开放5000端口：

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 5000/tcp

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

## 故障排除

### 服务启动失败

1. 检查日志：
```bash
sudo journalctl -u yahoo -n 50
```

2. 检查Python虚拟环境路径是否正确
3. 检查依赖是否安装完整：
```bash
source venv/bin/activate
pip list
```

### 自动部署不工作

1. 检查cron任务是否正确：
```bash
crontab -l
```

2. 检查部署日志：
```bash
tail -f /var/log/yahoo-deploy.log
```

3. 手动运行部署脚本测试：
```bash
./deploy.sh
```

### 无法访问API

1. 检查服务是否运行：
```bash
sudo systemctl status yahoo
```

2. 检查端口是否监听：
```bash
sudo netstat -tlnp | grep 5000
```

3. 检查防火墙设置

## 安全建议

1. 不要在生产环境使用 `0.0.0.0` 监听所有IP，建议只监听内网IP
2. 使用反向代理 (如Nginx) 并配置HTTPS
3. 定期更新依赖包
4. 限制API访问频率
5. 考虑使用环境变量管理敏感配置

## 更新日志

项目的日志文件位置：
- 应用日志: `./yfinance_server.log`
- 系统日志: `sudo journalctl -u yahoo`
- 部署日志: `/var/log/yahoo-deploy.log`
