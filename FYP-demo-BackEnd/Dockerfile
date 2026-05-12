FROM python:3.12-slim-trixie

# 拷贝 uv 官方镜像中的二进制，遵循 uv 文档推荐方案
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000 

WORKDIR /app

# 配置 pip 清华源镜像
# RUN pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

# 先同步依赖（不安装项目本身）以利用层缓存
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --no-cache --no-group dev

# 拷贝其余源代码并安装项目
COPY . .
RUN uv sync --frozen --no-dev --no-cache --no-group dev

EXPOSE 8000

CMD ["/app/.venv/bin/python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
