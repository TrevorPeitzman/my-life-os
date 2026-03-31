FROM python:3.12-slim

# Prevent apt from prompting for timezone or mail server config during build
ENV DEBIAN_FRONTEND=noninteractive

# Install system deps: cron daemon + tzdata for correct timezone handling
RUN apt-get update && apt-get install -y --no-install-recommends \
        cron \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY scripts/ ./scripts/

# Bake crontab for the cron service variant
# The backend CMD overrides this; only the cron service uses crond
RUN echo "0 7 * * * cd /app && python scripts/morning_push.py >> /var/log/cron.log 2>&1" > /etc/cron.d/life-os && \
    echo "0 20 * * * cd /app && python scripts/evening_push.py >> /var/log/cron.log 2>&1" >> /etc/cron.d/life-os && \
    chmod 0644 /etc/cron.d/life-os && \
    crontab /etc/cron.d/life-os && \
    touch /var/log/cron.log

# Default: run the API server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
