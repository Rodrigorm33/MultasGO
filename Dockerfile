# Use uma imagem base oficial do Python
FROM python:3.12-slim

# Defina o diretório de trabalho
WORKDIR /app

# Copie o arquivo de requisitos e instale as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante do código da aplicação
COPY . .

# Definir variável de ambiente Railway
ENV RAILWAY_ENVIRONMENT=production

# Definir a porta padrão
ENV PORT=8080

# Comando para iniciar a aplicação diretamente com uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "${PORT}", "--log-level", "debug"]
