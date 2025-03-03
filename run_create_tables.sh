#!/bin/bash

# Script para executar o create_tables.py no ambiente do Railway
echo "Iniciando script de criação de tabelas..."

# Verifica se o Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "Python3 não encontrado. Tentando com python..."
    if ! command -v python &> /dev/null; then
        echo "Python não encontrado. Por favor, instale o Python."
        exit 1
    fi
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

# Verifica se o psycopg2 está instalado
$PYTHON_CMD -c "import psycopg2" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Instalando psycopg2..."
    $PYTHON_CMD -m pip install psycopg2-binary
fi

# Executa o script de criação de tabelas
echo "Executando create_tables.py..."
$PYTHON_CMD create_tables.py

# Verifica se a execução foi bem-sucedida
if [ $? -eq 0 ]; then
    echo "Tabelas criadas com sucesso!"
else
    echo "Erro ao criar tabelas. Verifique os logs acima."
    exit 1
fi

echo "Script concluído." 