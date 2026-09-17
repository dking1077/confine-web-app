FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install requirements FIRST
RUN pip install --no-cache-dir -r requirements.txt

# Then force redis to the correct version LAST (overrides any downgrade)
RUN pip install --no-cache-dir --force-reinstall "redis>=8.0.0"

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]

