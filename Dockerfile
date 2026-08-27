# Railway 部署用：连 echuu-agent 仓库、Root 为空时使用
FROM python:3.11-slim

WORKDIR /app

# 复制依赖与代码（当前 REST/WS 入口在 echuu-web/backend）
COPY requirements.txt /app/requirements.txt
COPY echuu /app/echuu
COPY workflow /app/workflow
COPY echuu-web /app/echuu-web

RUN pip install --no-cache-dir -r /app/requirements.txt

# main.py 需能 import /app/echuu
ENV PYTHONPATH=/app
WORKDIR /app/echuu-web/backend
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
