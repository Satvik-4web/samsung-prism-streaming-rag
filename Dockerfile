# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

FROM python:3.11-slim AS runner

WORKDIR /app
# Copy installed dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy app code
COPY . .

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
