FROM python:3.11-slim

WORKDIR /app/env

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV ENABLE_WEB_INTERFACE=true
ENV PYTHONPATH="/app/env:$PYTHONPATH"

CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]