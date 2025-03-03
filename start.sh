#!/bin/bash

# Exibir informações de diagnóstico
echo "Iniciando MultasGO..."
echo "Diretório atual: $(pwd)"
echo "Conteúdo do diretório: $(ls -la)"
echo "Variáveis de ambiente disponíveis: $(env | grep -v SECRET | grep -v PASSWORD | cut -d= -f1 | sort)"

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

# Iniciar a aplicação com mais logs
echo "Iniciando a aplicação com uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level debug 