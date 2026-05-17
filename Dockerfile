FROM python:3.11-alpine

# Install CA certificates and timezone data for API calls + date handling
RUN apk add --no-cache ca-certificates tzdata && \
    cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone

WORKDIR /app
COPY backend/requirements.txt .

# Install build deps for packages with C extensions, then clean up
RUN apk add --no-cache --virtual .build-deps gcc musl-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn && \
    apk del .build-deps

COPY backend/ .

# Verify the app can at least be imported (catches import-time errors early)
RUN python -c "from main import app; print('App import OK')"

CMD ["gunicorn", "main:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:80", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-"]
