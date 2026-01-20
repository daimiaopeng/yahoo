# Yahoo Finance Server - 最小化Docker镜像
# 使用Alpine Linux，镜像大小约100MB

# ===== 构建阶段 =====
FROM python:3.11-alpine AS builder

WORKDIR /build

# 安装构建依赖
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev

# 复制依赖文件
COPY requirements.txt .

# 安装依赖到独立目录
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ===== 生产阶段 =====
FROM python:3.11-alpine

WORKDIR /app

# 安装运行时依赖
RUN apk add --no-cache libffi

# 创建非root用户
RUN adduser -D -s /bin/sh appuser

# 从builder复制已安装的包
COPY --from=builder /install /usr/local

# 复制应用代码
COPY --chown=appuser:appuser src/ ./

# 创建数据目录并设置权限
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# 切换用户
USER appuser

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost:5000/api/health || exit 1

# 启动
CMD ["python", "main.py"]
