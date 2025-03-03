#!/bin/bash

# Exibir informações de diagnóstico
echo "Iniciando MultasGO..."
echo "Diretório atual: $(pwd)"
echo "Conteúdo do diretório: $(ls -la)"
echo "Variáveis de ambiente: $(env | grep -v SECRET)"
echo "Porta: ${PORT:-8080}"

# Iniciar a aplicação
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} 