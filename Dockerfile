FROM python:3.9-slim

WORKDIR /app

# Instalar dependências do sistema para o pacote psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primeiro para aproveitar o cache das camadas do Docker
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código
COPY . .

# Script de inicialização com solução para a expansão da variável PORT
CMD echo "Esperando o banco de dados inicializar..." && \
    sleep 10 && \
    echo "Iniciando aplicação..." && \
    if [ -z "$PORT" ]; then \
      export PORT=8000; \
    fi && \
    uvicorn app.main:app --host 0.0.0.0 --port $PORT