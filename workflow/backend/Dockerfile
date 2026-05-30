# 用于 Railway / Render / Fly 等部署 Echuu workflow 后端
# 构建：在「仓库根」执行 docker build -f echuu-agent/workflow/backend/Dockerfile .
FROM python:3.11-slim

WORKDIR /app

# Copy the whole echuu-agent package source so we can pip install -e
COPY echuu-agent /app/echuu-agent

# Install the echuu package in editable mode (canonical install path).
# This makes `from echuu.live.engine import ...` work in the worker.
RUN pip install --no-cache-dir -e /app/echuu-agent

# Backend app code lives under workflow/backend
WORKDIR /app/echuu-agent/workflow/backend
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
