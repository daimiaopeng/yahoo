#!/bin/bash

# Yahoo Finance Server - 初始化安装脚本

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Yahoo Finance Server 初始化安装 ===${NC}"

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
echo -e "${YELLOW}项目目录: $REPO_DIR${NC}"

cd "$REPO_DIR"

# 检查Python版本
echo -e "${YELLOW}检查Python版本...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: Python3 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✓ $(python3 --version)${NC}"

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}创建Python虚拟环境...${NC}"
    python3 -m venv venv
fi
echo -e "${GREEN}✓ 虚拟环境已就绪${NC}"

# 安装依赖
echo -e "${YELLOW}安装Python依赖...${NC}"
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}✓ 依赖安装完成${NC}"

# 配置systemd服务
echo ""
echo -e "${BLUE}=== 配置systemd服务 ===${NC}"
echo -e "${YELLOW}是否要配置systemd服务？[y/N]${NC}"
read -r response

if [[ "$response" =~ ^([yY])$ ]]; then
    CURRENT_USER=$(whoami)
    
    TMP_SERVICE="/tmp/yahoo.service"
    cat > "$TMP_SERVICE" <<EOF
[Unit]
Description=Yahoo Finance Server
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$REPO_DIR/src
Environment="PATH=$REPO_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$REPO_DIR/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=yahoo-finance

[Install]
WantedBy=multi-user.target
EOF

    sudo cp "$TMP_SERVICE" /etc/systemd/system/yahoo.service
    sudo systemctl daemon-reload
    echo -e "${GREEN}✓ systemd服务已配置${NC}"
    
    echo -e "${YELLOW}是否立即启动服务？[y/N]${NC}"
    read -r start_response
    
    if [[ "$start_response" =~ ^([yY])$ ]]; then
        sudo systemctl start yahoo
        sudo systemctl enable yahoo
        echo -e "${GREEN}✓ 服务已启动${NC}"
    fi
fi

echo ""
echo -e "${GREEN}=== 安装完成 ===${NC}"
echo "测试服务: curl http://localhost:5000/api/health"
echo "查看日志: sudo journalctl -u yahoo -f"
