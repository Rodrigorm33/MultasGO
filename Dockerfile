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

# Definir variável de ambiente Railway
ENV RAILWAY_ENVIRONMENT=production

# Definir a porta padrão
ENV PORT=8080

# Comando para iniciar a aplicação com logs detalhados e teste de conexão com o banco
CMD echo "Iniciando aplicação..." && \
    echo "Diretório atual: $(pwd)" && \
    echo "Conteúdo do diretório: $(ls -la)" && \
    echo "Variáveis de ambiente: $(env | grep -v SECRET | grep -v PASSWORD)" && \
    echo "Verificando rede: $(netstat -tulpn)" && \
    echo "Versão do Python: $(python --version)" && \
    echo "Versão do pip: $(pip --version)" && \
    echo "Pacotes instalados: $(pip list)" && \
    echo "Testando conexão com o banco de dados..." && \
    export PGPASSWORD=$(echo $DATABASE_URL | sed -e 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/') && \
    export PGUSER=$(echo $DATABASE_URL | sed -e 's/.*:\/\/\([^:]*\):.*/\1/') && \
    export PGHOST=$(echo $DATABASE_URL | sed -e 's/.*@\([^:]*\):.*/\1/') && \
    export PGPORT=$(echo $DATABASE_URL | sed -e 's/.*:\([0-9]*\)\/.*/\1/') && \
    export PGDATABASE=$(echo $DATABASE_URL | sed -e 's/.*\/\(.*\)/\1/') && \
    echo "Tentando conectar ao banco: $PGHOST:$PGPORT/$PGDATABASE como $PGUSER" && \
    pg_isready -h $PGHOST -p $PGPORT -U $PGUSER && \
    echo "Conexão com o banco de dados bem-sucedida!" || echo "ERRO: Falha na conexão com o banco de dados!" && \
    echo "Iniciando uvicorn..." && \
    uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level debug
