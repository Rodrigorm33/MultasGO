# Use uma imagem base oficial do Python
FROM python:3.12-slim

# Defina o diretório de trabalho
WORKDIR /app

# Instalar ferramentas de diagnóstico e PostgreSQL client
RUN apt-get update && apt-get install -y curl procps net-tools postgresql-client && apt-get clean

# Instalar gunicorn explicitamente junto com outras dependências
RUN pip install --no-cache-dir gunicorn uvicorn

# Copie o arquivo de requisitos e instale as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante do código da aplicação
COPY . .

# Tornar o script de inicialização executável
RUN chmod +x start.sh

# Definir variável de ambiente Railway
ENV RAILWAY_ENVIRONMENT=production

# Definir a porta padrão (será sobrescrita pelo Railway)
ENV PORT=8080
EXPOSE 8080

# Configurar variáveis de ambiente para melhor performance
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV GUNICORN_CMD_ARGS="--timeout=120 --keep-alive=5"

# Garantir que o script start.sh use LF ao invés de CRLF
RUN sed -i 's/\r$//' start.sh

# Adicionar healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Usar o script start.sh como ponto de entrada
ENTRYPOINT ["/bin/bash", "start.sh"]
