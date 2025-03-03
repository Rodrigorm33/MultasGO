# Use uma imagem base oficial do Python
FROM python:3.12-slim

# Defina o diretório de trabalho
WORKDIR /app

# Instalar ferramentas de diagnóstico e PostgreSQL client
RUN apt-get update && apt-get install -y curl procps net-tools postgresql-client && apt-get clean

# Copie o arquivo de requisitos e instale as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante do código da aplicação
COPY . .

# Tornar o script de inicialização executável
RUN chmod +x start.sh

# Definir variável de ambiente Railway
ENV RAILWAY_ENVIRONMENT=production

# Definir a porta padrão
ENV PORT=8080
EXPOSE 8080

# Iniciar o uvicorn diretamente com a porta fixa
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
