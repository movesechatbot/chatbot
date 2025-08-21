FROM python:3.10-slim

# Instala dependências básicas
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Cria diretório de trabalho
WORKDIR /app

# Copia arquivos
COPY . /app

# Instala libs Python
RUN pip install --no-cache-dir -r requirements.txt

# Expõe a porta 10000
EXPOSE 10000

# Roda a API
CMD ["python", "main.py"]

