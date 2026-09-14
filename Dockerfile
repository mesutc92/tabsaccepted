FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KAP_DB_PATH=/data/kap.db

COPY pyproject.toml README.md requirements.txt ./
COPY src ./src
RUN pip install --no-cache-dir .

VOLUME ["/data"]
CMD ["kap-alert", "watch"]
