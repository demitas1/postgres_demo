FROM python:3.11-slim

# ユーザーを作成
RUN useradd -m -u 1000 -s /bin/bash myuser

# 作業ディレクトリの所有者を変更
WORKDIR /app
RUN chown -R myuser:myuser /app

# ユーザーを切り替え
USER myuser

# 共通依存関係をインストール
COPY docker/python_dev/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 環境変数設定（コンテナ用デフォルト値）
# DB関係は .env + docker compose で設定するものを使う。ここでは設定しない
#ENV POSTGRES_HOST=db
#ENV POSTGRES_PORT=5432
#ENV POSTGRES_NAME=mydatabase
#ENV POSTGRES_USER=postgres
#ENV POSTGRES_PASSWORD=mysecretpassword

ENV PYTHONPATH=/app/src

CMD ["tail", "-f", "/dev/null"]
