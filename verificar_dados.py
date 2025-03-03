#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psycopg2
import sys
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Credenciais de conexão
DB_HOST = "ballast.proxy.rlwy.net"
DB_PORT = "40799"
DB_NAME = "railway"
DB_USER = "postgres"
DB_PASSWORD = "aRREuAPWWcxirWfoGysVRQHNyCfPHDYk"

def verificar_dados():
    """Verifica os dados na tabela bdbautos."""
    try:
        # Conectar ao banco de dados
        logging.info(f"Conectando ao banco de dados: {DB_HOST}:{DB_PORT}/{DB_NAME}")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        # Criar um cursor
        cur = conn.cursor()
        
        # Verificar tabelas existentes
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tabelas = [tabela[0] for tabela in cur.fetchall()]
        logging.info(f"Tabelas no banco de dados: {tabelas}")
        
        # Verificar colunas da tabela bdbautos
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'bdbautos'")
        colunas = [coluna[0] for coluna in cur.fetchall()]
        logging.info(f"Colunas da tabela 'bdbautos': {colunas}")
        
        # Verificar contagem de registros
        cur.execute("SELECT COUNT(*) FROM bdbautos")
        count = cur.fetchone()[0]
        logging.info(f"Total de registros na tabela 'bdbautos': {count}")
        
        # Mostrar alguns registros
        colunas_str = '", "'.join(colunas)
        cur.execute(f'SELECT "{colunas_str}" FROM bdbautos LIMIT 5')
        registros = cur.fetchall()
        logging.info("Primeiros 5 registros:")
        for i, reg in enumerate(registros):
            logging.info(f"  Registro {i+1}: {reg}")
        
        # Fechar conexão
        cur.close()
        conn.close()
        
        return True
    
    except Exception as e:
        logging.error(f"Erro ao verificar dados: {e}")
        return False

if __name__ == "__main__":
    if verificar_dados():
        sys.exit(0)
    else:
        sys.exit(1) 