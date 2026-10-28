FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=9132
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /data /app/instance && useradd --create-home appuser && chown -R appuser:appuser /app /data
USER appuser
ENV AIMLD_DATABASE_PATH=/data/aimld.sqlite3
EXPOSE 9132
CMD ["sh", "-c", "gunicorn --workers 2 --threads 4 --bind 0.0.0.0:${PORT:-9132} 'aimld.app:app'"]
