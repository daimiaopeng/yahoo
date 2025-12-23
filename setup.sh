#!/bin/bash

# Yahoo Finance Server - 初始化安装脚本
# 此脚本帮助快速设置服务器环境

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Yahoo Finance Server 初始化安装 ===${NC}"
echo ""

# 获取当前目录
REPO_DIR=$(pwd)
echo -e "${YELLOW}项目目录: $REPO_DIR${NC}"

# 检查Python版本
echo -e "${YELLOW}检查Python版本...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: Python3 未安装${NC}"
    echo "请先安装Python3: sudo apt-get install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ $PYTHON_VERSION${NC}"

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}创建Python虚拟环境...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ 虚拟环境已创建${NC}"
else
    echo -e "${GREEN}✓ 虚拟环境已存在${NC}"
fi

# 激活虚拟环境并安装依赖
echo -e "${YELLOW}安装Python依赖...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ 依赖安装完成${NC}"

# 给脚本添加执行权限
echo -e "${YELLOW}设置脚本执行权限...${NC}"
chmod +x deploy.sh
echo -e "${GREEN}✓ deploy.sh 已设置为可执行${NC}"

# 配置systemd服务
echo ""
echo -e "${BLUE}=== 配置systemd服务 ===${NC}"
echo -e "${YELLOW}是否要配置systemd服务？(需要sudo权限) [y/N]${NC}"
read -r response

if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    # 获取当前用户
    CURRENT_USER=$(whoami)
    
    # 创建临时服务文件
    TMP_SERVICE="/tmp/yahoo.service"
    cat > "$TMP_SERVICE" << EOF
[Unit]
Description=Yahoo Finance Server
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$REPO_DIR
Environment="PATH=$REPO_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$REPO_DIR/venv/bin/python main.py
Restart=always
RestartSec=10

# 日志配置
StandardOutput=journal
StandardError=journal
SyslogIdentifier=yahoo-finance

[Install]
WantedBy=multi-user.target
EOF

    echo -e "${YELLOW}复制服务文件到systemd目录...${NC}"
    sudo cp "$TMP_SERVICE" /etc/systemd/system/yahoo.service
    
    echo -e "${YELLOW}重新加载systemd配置...${NC}"
    sudo systemctl daemon-reload
    
    echo -e "${GREEN}✓ systemd服务已配置${NC}"
    
    echo -e "${YELLOW}是否立即启动服务？[y/N]${NC}"
    read -r start_response
    
    if [[ "$start_response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        sudo systemctl start yahoo
        sudo systemctl enable yahoo
        echo -e "${GREEN}✓ 服务已启动并设置为开机自启${NC}"
        
        sleep 2
        echo ""
        echo -e "${BLUE}服务状态:${NC}"
        sudo systemctl status yahoo --no-pager -l
    fi
fi

# 配置自动部署
echo ""
echo -e "${BLUE}=== 配置自动部署 ===${NC}"
echo -e "${YELLOW}是否要设置cron定时任务自动检查GitHub更新？[y/N]${NC}"
read -r cron_response

if [[ "$cron_response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    CRON_JOB="*/5 * * * * cd $REPO_DIR && ./deploy.sh >> /var/log/yahoo-deploy.log 2>&1"
    
    # 检查cron任务是否已存在
    if crontab -l 2>/dev/null | grep -q "deploy.sh"; then
        echo -e "${YELLOW}cron任务已存在${NC}"
    else
        # 添加cron任务
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        echo -e "${GREEN}✓ cron任务已添加（每5分钟检查一次更新）${NC}"
    fi
    
    echo -e "${YELLOW}查看当前的cron任务:${NC}"
    crontab -l | grep deploy.sh || true
fi

echo ""
echo -e "${GREEN}=== 安装完成 ===${NC}"
echo ""
echo -e "${BLUE}下一步:${NC}"
echo "1. 测试服务: curl http://localhost:5000/api/status"
echo "2. 查看日志: sudo journalctl -u yahoo -f"
echo "3. 查看部署日志: tail -f /var/log/yahoo-deploy.log"
echo ""
echo -e "${BLUE}更多信息请查看 DEPLOYMENT.md${NC}"
