# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Predictable, unbuffered Python; Flask CLI target for migrations.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    FLASK_CONFIG=production

WORKDIR /app

# Install dependencies first to leverage Docker layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source.
COPY . .

# Run as an unprivileged user and ensure the instance dir is writable.
RUN chmod +x docker-entrypoint.sh \
    && adduser --disabled-password --gecos "" appuser \
    && mkdir -p instance \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Entry point applies DB migrations, then starts the WSGI server.
ENTRYPOINT ["./docker-entrypoint.sh"]
