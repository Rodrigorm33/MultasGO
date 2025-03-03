#!/bin/bash

# Exibir informações de diagnóstico
echo "Iniciando MultasGO (versão de diagnóstico)..."
echo "Diretório atual: $(pwd)"
echo "Conteúdo do diretório: $(ls -la)"
echo "Variáveis de ambiente disponíveis: $(env | grep -v SECRET | grep -v PASSWORD | cut -d= -f1 | sort)"

# Definir a porta padrão se não estiver definida ou se não for um número válido
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
    export PORT=8080
    echo "Porta configurada para o padrão: $PORT"
else
    echo "Porta configurada: $PORT"
fi

# Iniciar o uvicorn com a aplicação
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT 