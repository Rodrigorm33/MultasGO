# Use uma imagem base oficial do Python
FROM python:3.12-slim

# Defina o diretório de trabalho
WORKDIR /app

# Copie o arquivo de requisitos e instale as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie o restante do código da aplicação
COPY . .

# Tornar o script de inicialização executável
RUN chmod +x start.sh

# Comando para iniciar a aplicação usando o script
CMD ["./start.sh"]
