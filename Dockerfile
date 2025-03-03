# Use uma imagem base oficial do Python
FROM python:3.12-slim

# Defina o diretório de trabalho
WORKDIR /app

# Instalar ferramentas de diagnóstico e PostgreSQL client
RUN apt-get update && apt-get install -y curl && apt-get clean

# Copie o arquivo de requisitos e instale as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante do código da aplicação
COPY . .

# Definir a porta padrão (será sobrescrita pelo Railway)
ENV PORT=8080
EXPOSE 8080

# Configurar variáveis de ambiente para melhor performance
ENV PYTHONUNBUFFERED=1

# Usar o comando uvicorn para iniciar a aplicação
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
