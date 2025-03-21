FROM python:3.11.9

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

# Comando de inicialização - usando porta 8080 explicitamente
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}