#!/bin/bash

# Yahoo Finance Server - 自动部署脚本
# 此脚本用于从GitHub拉取最新代码并重启服务

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
REPO_DIR="/home/runner/work/yahoo/yahoo"
SERVICE_NAME="yahoo"
VENV_DIR="venv"

echo -e "${GREEN}=== Yahoo Finance Server 自动部署 ===${NC}"
echo "时间: $(date)"

# 切换到项目目录
cd "$REPO_DIR" || exit 1
echo -e "${YELLOW}项目目录: $REPO_DIR${NC}"

# 保存当前的commit hash
OLD_COMMIT=$(git rev-parse HEAD)
echo "当前版本: $OLD_COMMIT"

# 从GitHub拉取最新代码
echo -e "${YELLOW}从GitHub拉取最新代码...${NC}"
git fetch origin
git pull origin main

# 获取新的commit hash
NEW_COMMIT=$(git rev-parse HEAD)
echo "最新版本: $NEW_COMMIT"

# 检查是否有更新
if [ "$OLD_COMMIT" = "$NEW_COMMIT" ]; then
    echo -e "${GREEN}没有新的更新${NC}"
    exit 0
fi

echo -e "${GREEN}检测到新版本，开始部署...${NC}"

# 激活虚拟环境（如果存在）
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}激活虚拟环境...${NC}"
    source "$VENV_DIR/bin/activate"
fi

# 更新依赖
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}更新Python依赖...${NC}"
    pip install -r requirements.txt --upgrade
fi

# 重启服务
echo -e "${YELLOW}重启服务...${NC}"
if systemctl is-active --quiet "$SERVICE_NAME"; then
    sudo systemctl restart "$SERVICE_NAME"
    echo -e "${GREEN}服务已重启${NC}"
else
    echo -e "${YELLOW}服务未运行，启动服务...${NC}"
    sudo systemctl start "$SERVICE_NAME"
    echo -e "${GREEN}服务已启动${NC}"
fi

# 检查服务状态
sleep 2
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${GREEN}✓ 部署成功！服务正在运行${NC}"
    sudo systemctl status "$SERVICE_NAME" --no-pager -l
else
    echo -e "${RED}✗ 部署失败！服务未能启动${NC}"
    sudo systemctl status "$SERVICE_NAME" --no-pager -l
    exit 1
fi

echo -e "${GREEN}=== 部署完成 ===${NC}"
