#!/bin/bash

echo "Iniciando MultasGO..."

# Usar valor da PORT ou 8000 como padrão
export PORT=${PORT:-8000}

echo "Porta configurada: $PORT"

# Usar exec para substituir o shell pelo processo uvicorn
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}