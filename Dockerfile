# Railway 部署用：Root Directory = echuu-agent 时使用此 Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 复制依赖与代码（与 app.py 中 PROJECT_ROOT 对应）
COPY requirements.txt /app/requirements.txt
COPY public /app/public
COPY workflow /app/workflow

RUN pip install --no-cache-dir -r /app/requirements.txt

# echuu 包在 public/ 下，后端在 workflow/backend
ENV PYTHONPATH=/app/public
WORKDIR /app/workflow/backend
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
