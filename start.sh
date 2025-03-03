#!/bin/bash

# Exibir informações de diagnóstico
echo "Iniciando MultasGO (versão de diagnóstico)..."
echo "Diretório atual: $(pwd)"
echo "Conteúdo do diretório: $(ls -la)"
echo "Variáveis de ambiente disponíveis: $(env | grep -v SECRET | grep -v PASSWORD | cut -d= -f1 | sort)"

# Definir a porta padrão se não estiver definida
if [ -z "$PORT" ]; then
    export PORT=8080
fi

# Converter $PORT para inteiro e validar
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    echo "PORT não é um número válido, usando porta padrão 8080"
    export PORT=8080
fi

echo "Porta configurada: $PORT"

# Iniciar o gunicorn com configurações otimizadas para o Railway
exec gunicorn app.main:app \
    --bind 0.0.0.0:${PORT} \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120 \
    --keep-alive 5 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --graceful-timeout 30 \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --preload