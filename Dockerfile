# ==============================================================================
# ShadowLens Enterprise Oracle MCP Microservice
# 基于 Python 3.11-slim 构建，纯 Thin Mode 运行，完全免装 Oracle Instant Client
# ==============================================================================
FROM python:3.11-slim

# 设置时区与环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# 安装基础依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝应用代码与配置
COPY src/ ./src/
COPY config/ ./config/

# 暴露内网 MCP SSE 端口
EXPOSE 8000

# 默认启动内网 SSE 微服务
ENTRYPOINT ["python", "-m", "src.server"]
CMD ["--transport", "sse", "--host", "0.0.0.0", "--port", "8000"]
