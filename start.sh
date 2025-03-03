#!/bin/bash

# Exibir informações de diagnóstico
echo "Iniciando MultasGO (versão de diagnóstico)..."
echo "Diretório atual: $(pwd)"
echo "Conteúdo do diretório: $(ls -la)"
echo "Variáveis de ambiente disponíveis: $(env | grep -v SECRET | grep -v PASSWORD | cut -d= -f1 | sort)"

# Verificar DATABASE_URL
if [ -n "$DATABASE_URL" ]; then
    echo "DATABASE_URL encontrada: $(echo $DATABASE_URL | sed 's/postgresql:\/\/[^:]*:[^@]*@/postgresql:\/\/USER:PASSWORD@/')"
    
    # Verificar se a URL é válida
    if [[ "$DATABASE_URL" != postgresql://* ]]; then
        echo "ERRO: DATABASE_URL inválida! Não começa com postgresql://"
        unset DATABASE_URL
    else
        # Extrair parâmetros diretamente da DATABASE_URL
        export PGUSER=$(echo $DATABASE_URL | sed -e 's/.*:\/\/\([^:]*\):.*/\1/')
        export PGPASSWORD=$(echo $DATABASE_URL | sed -e 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/')
        export PGHOST=$(echo $DATABASE_URL | sed -e 's/.*@\([^:]*\):.*/\1/')
        export PGPORT=$(echo $DATABASE_URL | sed -e 's/.*:\([0-9]*\)\/.*/\1/')
        export PGDATABASE=$(echo $DATABASE_URL | sed -e 's/.*\/\([^?]*\).*/\1/')
        
        echo "Parâmetros extraídos da DATABASE_URL:"
        echo "  PGUSER: $PGUSER"
        echo "  PGHOST: $PGHOST"
        echo "  PGPORT: $PGPORT"
        echo "  PGDATABASE: $PGDATABASE"
        echo "  PGPASSWORD: (valor oculto)"
    fi
else
    echo "AVISO: DATABASE_URL não encontrada!"
fi

# Verificar variáveis de banco de dados
echo "Verificando variáveis de banco de dados:"
echo "PGUSER existe: $(if [ -n "$PGUSER" ]; then echo "SIM - $PGUSER"; else echo "NÃO"; fi)"
echo "PGHOST existe: $(if [ -n "$PGHOST" ]; then echo "SIM - $PGHOST"; else echo "NÃO"; fi)"
echo "PGPORT existe: $(if [ -n "$PGPORT" ]; then echo "SIM - $PGPORT"; else echo "NÃO"; fi)"
echo "PGDATABASE existe: $(if [ -n "$PGDATABASE" ]; then echo "SIM - $PGDATABASE"; else echo "NÃO"; fi)"
echo "POSTGRES_USER existe: $(if [ -n "$POSTGRES_USER" ]; then echo "SIM - $POSTGRES_USER"; else echo "NÃO"; fi)"
echo "POSTGRES_PASSWORD existe: $(if [ -n "$POSTGRES_PASSWORD" ]; then echo "SIM - (valor oculto)"; else echo "NÃO"; fi)"
echo "POSTGRES_DB existe: $(if [ -n "$POSTGRES_DB" ]; then echo "SIM - $POSTGRES_DB"; else echo "NÃO"; fi)"

# Definir a porta padrão se não estiver definida
export PORT=${PORT:-8080}
echo "Porta configurada: $PORT"

# Verificar se o Python está instalado corretamente
echo "Versão do Python: $(python --version)"
echo "Versão do pip: $(pip --version)"
echo "Pacotes instalados: $(pip list | head -20)"

# Verificar se o uvicorn está instalado
echo "Verificando uvicorn: $(which uvicorn)"

# Definir variável de ambiente Railway se não estiver definida
if [ -z "$RAILWAY_ENVIRONMENT" ]; then
    echo "Definindo RAILWAY_ENVIRONMENT=production"
    export RAILWAY_ENVIRONMENT=production
fi

# Se não tiver PGUSER, tente usar POSTGRES_USER
if [ -z "$PGUSER" ] && [ -n "$POSTGRES_USER" ]; then
    echo "Usando POSTGRES_USER como PGUSER"
    export PGUSER=$POSTGRES_USER
fi

# Se não tiver PGPASSWORD, tente usar POSTGRES_PASSWORD
if [ -z "$PGPASSWORD" ] && [ -n "$POSTGRES_PASSWORD" ]; then
    echo "Usando POSTGRES_PASSWORD como PGPASSWORD"
    export PGPASSWORD=$POSTGRES_PASSWORD
fi

# Se não tiver PGDATABASE, tente usar POSTGRES_DB
if [ -z "$PGDATABASE" ] && [ -n "$POSTGRES_DB" ]; then
    echo "Usando POSTGRES_DB como PGDATABASE"
    export PGDATABASE=$POSTGRES_DB
fi

# Definir valores padrão para conexão com o banco de dados
if [ -z "$PGHOST" ]; then
    echo "PGHOST não definido, usando postgres.railway.internal"
    export PGHOST="postgres.railway.internal"
fi

if [ -z "$PGPORT" ]; then
    echo "PGPORT não definido, usando 5432"
    export PGPORT="5432"
fi

if [ -z "$PGUSER" ]; then
    echo "PGUSER não definido, usando postgres"
    export PGUSER="postgres"
fi

if [ -z "$PGDATABASE" ]; then
    echo "PGDATABASE não definido, usando railway"
    export PGDATABASE="railway"
fi

# Verificar se temos PGPASSWORD
if [ -z "$PGPASSWORD" ]; then
    echo "AVISO: PGPASSWORD não está definido!"
    # Tentar usar um valor padrão do Railway
    export PGPASSWORD="FbFuyWYNXEEGPwdBUsvrUvhrtqaKGSOs"
    echo "Usando senha padrão para tentativa de conexão"
fi

# Reconstruir DATABASE_URL a partir das variáveis PG_* se não existir ou for inválida
if [ -z "$DATABASE_URL" ] || [[ "$DATABASE_URL" != postgresql://* ]]; then
    export DATABASE_URL="postgresql://$PGUSER:$PGPASSWORD@$PGHOST:$PGPORT/$PGDATABASE"
    echo "DATABASE_URL reconstruído: postgresql://$PGUSER:***@$PGHOST:$PGPORT/$PGDATABASE"
fi

# Garantir que a DATABASE_URL tenha os parâmetros corretos
if [[ "$DATABASE_URL" != *"?"* && "$DATABASE_URL" != *"&"* ]]; then
    export DATABASE_URL="${DATABASE_URL}?connect_timeout=10&application_name=multasgo&keepalives=1&keepalives_idle=5&keepalives_interval=2&keepalives_count=3"
    echo "Parâmetros adicionados à DATABASE_URL"
fi

# Exibir a DATABASE_URL final (com senha mascarada)
echo "DATABASE_URL final: $(echo $DATABASE_URL | sed 's/postgresql:\/\/[^:]*:[^@]*@/postgresql:\/\/USER:PASSWORD@/')"

# Testar conexão com o banco de dados usando psql
echo "Testando conexão com o banco de dados..."
echo "Tentando conectar ao banco: $PGHOST:$PGPORT/$PGDATABASE como $PGUSER"

# Verificar se pg_isready está disponível
if command -v pg_isready &> /dev/null; then
    pg_isready -h $PGHOST -p $PGPORT -U $PGUSER
    if [ $? -eq 0 ]; then
        echo "Conexão com o banco de dados bem-sucedida (pg_isready)!"
    else
        echo "ERRO: Falha na conexão com o banco de dados (pg_isready)!"
    fi
else
    echo "pg_isready não disponível, tentando psql..."
fi

# Tentar conexão com psql
if command -v psql &> /dev/null; then
    PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE -c "SELECT 1" &> /dev/null
    if [ $? -eq 0 ]; then
        echo "Conexão com o banco de dados bem-sucedida (psql)!"
    else
        echo "ERRO: Falha na conexão com o banco de dados (psql)!"
    fi
else
    echo "psql não disponível, tentando conexão via Python..."
fi

# Tentar conexão via Python
echo "Testando conexão via Python..."
python -c "
import os
import sys
import psycopg2
try:
    conn = psycopg2.connect(
        host=os.environ.get('PGHOST'),
        port=os.environ.get('PGPORT'),
        user=os.environ.get('PGUSER'),
        password=os.environ.get('PGPASSWORD'),
        dbname=os.environ.get('PGDATABASE')
    )
    cursor = conn.cursor()
    cursor.execute('SELECT 1')
    print('Conexão com o banco de dados bem-sucedida via Python!')
    
    # Verificar se a tabela autos existe
    cursor.execute(\"\"\"
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'autos'
        )
    \"\"\")
    if cursor.fetchone()[0]:
        print('Tabela autos encontrada!')
        cursor.execute('SELECT COUNT(*) FROM autos')
        count = cursor.fetchone()[0]
        print(f'Total de registros na tabela autos: {count}')
    else:
        print('Tabela autos NÃO encontrada!')
    
    conn.close()
except Exception as e:
    print(f'ERRO ao conectar via Python: {e}')
    # Não sair com erro para permitir que a aplicação continue
    print('A aplicação continuará mesmo com erro na conexão com o banco de dados.')
"

# Criar tabelas se necessário
echo "Verificando e criando tabelas se necessário..."
python -m app.scripts.create_tables || echo "Erro ao criar tabelas, mas a aplicação continuará."

# Iniciar a aplicação completa
echo "Iniciando a aplicação completa com uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --log-level debug 