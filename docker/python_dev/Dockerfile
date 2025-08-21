FROM python:3.11-slim

WORKDIR /app

# 共通依存関係をインストール
COPY docker/python_dev/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 環境変数設定（コンテナ用デフォルト値）
ENV DB_HOST=db
ENV DB_PORT=5432
ENV DB_NAME=mydatabase
ENV DB_USER=postgres
ENV DB_PASSWORD=mysecretpassword
ENV PYTHONPATH=/app/src

CMD ["tail", "-f", "/dev/null"]
