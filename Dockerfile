FROM python:3.10-slim
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
ENV PORT=10000
EXPOSE 10000
# 1 worker (Render 512MiB); threads ajudam I/O
CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:${PORT}", "main:app"]
