# FROM python:3.10-slim
# RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
# WORKDIR /app
# COPY . /app
# RUN pip install --no-cache-dir -r requirements.txt
# ENV PORT=10000
# EXPOSE 10000
# # 1 worker (Render 512MiB); threads ajudam I/O
# CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:${PORT}", "main:app"]

FROM python:3.11-slim

# deps básicas
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# opcional: pré-baixar o modelo p/ evitar cold start
RUN python - <<'PY'
from sentence_transformers import SentenceTransformer
SentenceTransformer("intfloat/multilingual-e5-small")
PY

# copia o resto
COPY . /app

# boas práticas p/ CPU e HF cache
ENV PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

# Render define PORT em runtime; respeita se vier, senão 10000
ENV PORT=10000
EXPOSE 10000

# use sh -c pra expandir ${PORT}; e aponta p/ app:app
CMD ["sh","-c","gunicorn app:app --workers=1 --threads=4 --timeout 90 -b 0.0.0.0:${PORT}"]

