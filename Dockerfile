# 多阶段构建 - 前端
FROM node:18-alpine AS frontend-build
WORKDIR /app/frontend
COPY package*.json ./
COPY src/frontend/index.html ./
COPY src/frontend/src ./src/
COPY src/frontend/vite.config.js ./
RUN npm ci
RUN npm run build

# 后端运行环境
FROM python:3.11-slim
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY src/backend/ ./src/backend/

# 复制前端构建产物
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf

# 复制启动脚本
COPY deploy/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 80 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
