# Railway 部署用：连 echuu-agent 仓库、Root 为空时使用
FROM python:3.11-slim

WORKDIR /app

# 复制依赖与代码（仓库根即 echuu-agent，echuu 包在 ./echuu，后端在 ./workflow/backend）
COPY requirements.txt /app/requirements.txt
COPY echuu /app/echuu
COPY workflow /app/workflow

RUN pip install --no-cache-dir -r /app/requirements.txt

# app.py 中 PROJECT_ROOT = 仓库根，需能 import echuu
ENV PYTHONPATH=/app
WORKDIR /app/workflow/backend
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
