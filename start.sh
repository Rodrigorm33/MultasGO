#!/bin/bash

echo "Iniciando MultasGO..."

# Definir a porta padrão se não estiver definida ou se não for um número válido
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    export PORT=8080
    echo "Porta configurada para o padrão: $PORT"
else
    echo "Porta configurada: $PORT"
fi

# Iniciar o uvicorn com a aplicação
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT