#!/bin/bash

# Script para configurar o banco de dados no Railway
# Este script executa os scripts Python para testar a conexão e criar as tabelas

echo "===== MultasGO - Configuração do Banco de Dados ====="
echo "Iniciando configuração do banco de dados no Railway..."

# Verificar se o Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "ERRO: Python 3 não está instalado!"
    exit 1
fi

# Verificar se o psycopg2 está instalado
echo "Verificando dependências..."
python3 -c "import psycopg2" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Instalando psycopg2..."
    pip install psycopg2-binary
fi

# Testar a conexão com o banco de dados
echo -e "\n===== Testando conexão com o banco de dados ====="
python3 test_db_connection.py
if [ $? -ne 0 ]; then
    echo "ERRO: Falha ao conectar ao banco de dados!"
    echo "Verifique se as variáveis de ambiente estão configuradas corretamente."
    exit 1
fi

# Criar as tabelas no banco de dados
echo -e "\n===== Criando tabelas no banco de dados ====="
python3 create_tables.py
if [ $? -ne 0 ]; then
    echo "ERRO: Falha ao criar as tabelas no banco de dados!"
    exit 1
fi

# Verificar se as tabelas foram criadas corretamente
echo -e "\n===== Verificando tabelas criadas ====="
python3 test_db_connection.py

echo -e "\n===== Configuração do banco de dados concluída! ====="
echo "O banco de dados MultasGO foi configurado com sucesso no Railway."
echo "Agora você pode iniciar a aplicação." 