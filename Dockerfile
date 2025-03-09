FROM python:3.9-slim

# Declarar argumentos para variáveis de ambiente do Railway
ARG PORT
ARG RAILWAY_ENVIRONMENT

WORKDIR /app

# Instalar dependências do sistema para o pacote psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primeiro para aproveitar o cache das camadas do Docker
COPY requirements.txt .

# Usar cache mount para pip (melhora o tempo de build)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código
COPY . .

# Comando para iniciar a aplicação
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "${PORT:-8000}"]