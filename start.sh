#!/bin/bash

# Exibir informações de diagnóstico
echo "Iniciando MultasGO..."
echo "Diretório atual: $(pwd)"
echo "Conteúdo do diretório: $(ls -la)"
echo "Variáveis de ambiente: $(env | grep -v SECRET)"

# Definir a porta padrão se não estiver definida
export PORT=${PORT:-8080}
echo "Porta configurada: $PORT"

# Verificar se o Python está instalado corretamente
echo "Versão do Python: $(python --version)"
echo "Versão do pip: $(pip --version)"
echo "Pacotes instalados: $(pip list)"

# Verificar se o uvicorn está instalado
echo "Verificando uvicorn: $(which uvicorn)"

# Iniciar a aplicação com mais logs
echo "Iniciando a aplicação com uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --log-level debug 