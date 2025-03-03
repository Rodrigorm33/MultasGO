#!/bin/bash

# Exibir informações de diagnóstico
echo "Iniciando MultasGO..."

# Definir a porta padrão se não estiver definida
export PORT=${PORT:-8080}

# Validar se PORT é um número
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    echo "PORT inválida ($PORT), usando 8080"
    export PORT=8080
fi

echo "Porta configurada: $PORT"

# Iniciar o servidor diretamente com uvicorn (mais simples e direto)
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --timeout-keep-alive 5 \
    --log-level info