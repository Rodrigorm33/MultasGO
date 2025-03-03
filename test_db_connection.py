#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para testar a conexão com o banco de dados PostgreSQL do MultasGO.
Este script verifica se a conexão está funcionando e lista as tabelas existentes.
"""

import os
import sys
import psycopg2
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("test_db_connection")

def get_connection_string():
    """Obtém a string de conexão do banco de dados a partir das variáveis de ambiente."""
    # Tenta usar DATABASE_URL primeiro
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        logger.info("Usando DATABASE_URL para conexão")
        return database_url
    
    # Se não tiver DATABASE_URL, tenta construir a partir das variáveis individuais
    host = os.environ.get("PGHOST")
    port = os.environ.get("PGPORT")
    user = os.environ.get("PGUSER")
    password = os.environ.get("PGPASSWORD")
    dbname = os.environ.get("PGDATABASE")
    
    if all([host, port, user, password, dbname]):
        conn_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        logger.info("Usando variáveis individuais para conexão")
        return conn_string
    
    logger.error("Não foi possível obter uma string de conexão válida")
    return None

def test_connection():
    """Testa a conexão com o banco de dados e lista as tabelas existentes."""
    conn_string = get_connection_string()
    if not conn_string:
        logger.error("String de conexão não encontrada. Verifique as variáveis de ambiente.")
        sys.exit(1)
    
    # Oculta a senha na string de conexão para exibição
    masked_conn_string = conn_string.replace("://", "://[usuario]:[senha]@", 1).split("@", 1)[0] + "@" + conn_string.split("@", 1)[1]
    logger.info(f"Tentando conectar usando: {masked_conn_string}")
    
    try:
        # Tenta estabelecer a conexão
        conn = psycopg2.connect(conn_string)
        logger.info("Conexão estabelecida com sucesso!")
        
        # Verifica as tabelas existentes
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [table[0] for table in cur.fetchall()]
            
            if tables:
                logger.info(f"Tabelas encontradas no banco de dados: {', '.join(tables)}")
                
                # Verifica se as tabelas necessárias existem
                required_tables = ['infracoes', 'autos']
                missing_tables = [table for table in required_tables if table not in tables]
                
                if missing_tables:
                    logger.warning(f"Tabelas necessárias não encontradas: {', '.join(missing_tables)}")
                    logger.info("Execute o script create_tables.py para criar as tabelas necessárias.")
                else:
                    logger.info("Todas as tabelas necessárias estão presentes!")
                    
                    # Verifica se há dados na tabela de infrações
                    cur.execute("SELECT COUNT(*) FROM infracoes")
                    count = cur.fetchone()[0]
                    logger.info(f"A tabela 'infracoes' contém {count} registros.")
                    
                    if count > 0:
                        # Mostra algumas infrações de exemplo
                        cur.execute("SELECT codigo, descricao, valor FROM infracoes LIMIT 5")
                        logger.info("Exemplos de infrações:")
                        for row in cur.fetchall():
                            logger.info(f"  - {row[0]}: {row[1]} (R$ {row[2]})")
            else:
                logger.warning("Nenhuma tabela encontrada no banco de dados.")
                logger.info("Execute o script create_tables.py para criar as tabelas necessárias.")
        
        # Fecha a conexão
        conn.close()
        logger.info("Teste de conexão concluído com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_connection() 