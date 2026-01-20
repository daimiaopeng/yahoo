#!/bin/bash

# Yahoo Finance Server - 自动部署脚本

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 获取项目目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="yahoo"

echo -e "${GREEN}=== Yahoo Finance Server 自动部署 ===${NC}"
echo "时间: $(date)"
echo "项目目录: $REPO_DIR"

cd "$REPO_DIR"

# 保存当前commit
OLD_COMMIT=$(git rev-parse HEAD)
echo "当前版本: ${OLD_COMMIT:0:8}"

# 拉取最新代码
echo -e "${YELLOW}从GitHub拉取最新代码...${NC}"
git fetch origin
git pull origin main

NEW_COMMIT=$(git rev-parse HEAD)
echo "最新版本: ${NEW_COMMIT:0:8}"

# 检查是否有更新
if [ "$OLD_COMMIT" = "$NEW_COMMIT" ]; then
    echo -e "${GREEN}没有新的更新${NC}"
    exit 0
fi

echo -e "${GREEN}检测到新版本，开始部署...${NC}"

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 更新依赖
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}更新Python依赖...${NC}"
    pip install -r requirements.txt -q
fi

# 重启服务
echo -e "${YELLOW}重启服务...${NC}"
if systemctl is-active --quiet "$SERVICE_NAME"; then
    sudo systemctl restart "$SERVICE_NAME"
else
    sudo systemctl start "$SERVICE_NAME"
fi

# 检查服务状态
sleep 2
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${GREEN}✓ 部署成功！${NC}"
else
    echo -e "${RED}✗ 部署失败！${NC}"
    exit 1
fi

echo -e "${GREEN}=== 部署完成 ===${NC}"
