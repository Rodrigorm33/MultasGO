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

def executar_sql_arquivo(arquivo_sql):
    """Executa comandos SQL de um arquivo."""
    try:
        # Ler o arquivo SQL
        logging.info(f"Lendo arquivo SQL: {arquivo_sql}")
        with open(arquivo_sql, 'r', encoding='utf-8') as f:
            sql_commands = f.read()
        
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
        
        # Executar os comandos SQL
        logging.info("Executando comandos SQL...")
        cur.execute(sql_commands)
        
        # Commit das alterações
        conn.commit()
        logging.info("Comandos SQL executados com sucesso!")
        
        # Verificar tabelas criadas
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tabelas = [tabela[0] for tabela in cur.fetchall()]
        logging.info(f"Tabelas no banco de dados: {tabelas}")
        
        # Verificar contagem de registros
        for tabela in ['infracoes', 'bdbautos']:
            if tabela in tabelas:
                cur.execute(f"SELECT COUNT(*) FROM {tabela}")
                count = cur.fetchone()[0]
                logging.info(f"Tabela '{tabela}' tem {count} registros.")
        
        # Fechar conexão
        cur.close()
        conn.close()
        
        return True
    
    except Exception as e:
        logging.error(f"Erro ao executar SQL: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arquivo_sql = sys.argv[1]
    else:
        arquivo_sql = "criar_tabelas.sql"
    
    if executar_sql_arquivo(arquivo_sql):
        sys.exit(0)
    else:
        sys.exit(1) 