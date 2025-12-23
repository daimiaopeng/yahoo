# 快速参考指南 (Quick Reference)

## 初次部署 (First Time Deployment)

```bash
# 1. 克隆代码
git clone https://github.com/daimiaopeng/yahoo.git
cd yahoo

# 2. 运行安装脚本
./setup.sh

# 3. 检查服务状态
sudo systemctl status yahoo
```

## 日常操作 (Daily Operations)

### 查看服务状态
```bash
sudo systemctl status yahoo
```

### 查看实时日志
```bash
# 应用日志
sudo journalctl -u yahoo -f

# 部署日志
tail -f ~/yahoo-deploy.log
```

### 手动部署新版本
```bash
cd /path/to/yahoo
./deploy.sh
```

### 重启服务
```bash
sudo systemctl restart yahoo
```

### 停止服务
```bash
sudo systemctl stop yahoo
```

### 启动服务
```bash
sudo systemctl start yahoo
```

## 测试API (Test API)

### 检查服务状态
```bash
curl http://localhost:5000/api/status
```

### 获取数据
```bash
curl http://localhost:5000/api/data
```

## 自动部署设置 (Auto-Deployment Setup)

### 方法1: Cron定时任务（每5分钟检查一次）
```bash
crontab -e
# 添加以下行：
*/5 * * * * cd /home/runner/work/yahoo/yahoo && ./deploy.sh >> ~/yahoo-deploy.log 2>&1
```

### 查看Cron任务
```bash
crontab -l
```

### 移除Cron任务
```bash
crontab -e
# 删除对应的行
```

## 故障排除 (Troubleshooting)

### 服务无法启动
```bash
# 查看详细错误日志
sudo journalctl -u yahoo -n 100 --no-pager

# 检查配置文件
cat /etc/systemd/system/yahoo.service

# 手动测试运行
cd /home/runner/work/yahoo/yahoo
source venv/bin/activate
python main.py
```

### 端口已被占用
```bash
# 查看5000端口使用情况
sudo netstat -tlnp | grep 5000
# 或
sudo lsof -i :5000

# 杀死占用端口的进程
sudo kill -9 <PID>
```

### 依赖安装问题
```bash
cd /home/runner/work/yahoo/yahoo
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

### 权限问题
```bash
# 给予脚本执行权限
chmod +x setup.sh deploy.sh

# 检查文件所有者
ls -la
```

## 性能监控 (Performance Monitoring)

### 查看进程资源使用
```bash
# CPU和内存使用
top -p $(pgrep -f "python main.py")

# 或使用htop
htop -p $(pgrep -f "python main.py")
```

### 查看网络连接
```bash
sudo netstat -anp | grep 5000
```

## 备份与恢复 (Backup & Recovery)

### 备份日志
```bash
cp ./yfinance_server.log ./yfinance_server.log.backup.$(date +%Y%m%d)
```

### 回滚到之前的版本
```bash
cd /home/runner/work/yahoo/yahoo
git log --oneline -10  # 查看最近的提交
git checkout <commit-hash>  # 回滚到指定版本
./deploy.sh  # 重新部署
```

## 安全建议 (Security Tips)

### 设置防火墙
```bash
# Ubuntu/Debian
sudo ufw allow 5000/tcp
sudo ufw enable

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

### 仅允许特定IP访问
```bash
# Ubuntu/Debian
sudo ufw allow from <IP地址> to any port 5000

# CentOS/RHEL
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="<IP地址>" port port="5000" protocol="tcp" accept'
sudo firewall-cmd --reload
```

## 环境变量 (Environment Variables)

如需配置环境变量，编辑服务文件：
```bash
sudo nano /etc/systemd/system/yahoo.service
```

在 `[Service]` 部分添加：
```ini
Environment="VARIABLE_NAME=value"
```

然后重新加载并重启：
```bash
sudo systemctl daemon-reload
sudo systemctl restart yahoo
```
