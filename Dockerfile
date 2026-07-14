FROM python:3.12-slim

# Prevents .pyc files and enables unbuffered logs (visible in `docker logs` immediately)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so this layer is cached unless requirements.txt changes
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 120 --retries 10 -r requirements.txt

COPY . .

# Directories for the SQLite DB and evidence files (mounted as volumes in compose)
RUN mkdir -p /app/data /app/evidence_store

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
