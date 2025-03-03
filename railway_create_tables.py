#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para criar as tabelas necessárias no banco de dados PostgreSQL do MultasGO no Railway.
Este script deve ser executado com o comando 'railway run python railway_create_tables.py'.
"""

import os
import sys
import psycopg2
from psycopg2 import sql
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("railway_create_tables")

def get_connection():
    """Estabelece conexão com o banco de dados usando variáveis de ambiente do Railway."""
    try:
        # No Railway, as variáveis de ambiente já estarão disponíveis
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            logger.info("Conectando usando DATABASE_URL")
            return psycopg2.connect(database_url)
        
        # Se não tiver DATABASE_URL, tenta usar variáveis individuais
        logger.info("Conectando usando variáveis individuais PGHOST, PGUSER, etc.")
        return psycopg2.connect(
            host=os.environ.get("PGHOST"),
            port=os.environ.get("PGPORT"),
            user=os.environ.get("PGUSER"),
            password=os.environ.get("PGPASSWORD"),
            dbname=os.environ.get("PGDATABASE")
        )
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}")
        raise

def create_tables(conn):
    """Cria as tabelas necessárias se elas não existirem."""
    try:
        with conn.cursor() as cur:
            # Verifica se as tabelas já existem
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            existing_tables = [table[0] for table in cur.fetchall()]
            logger.info(f"Tabelas existentes: {existing_tables}")
            
            # Cria tabela de infrações se não existir
            if 'infracoes' not in existing_tables:
                logger.info("Criando tabela 'infracoes'...")
                cur.execute("""
                    CREATE TABLE infracoes (
                        id SERIAL PRIMARY KEY,
                        codigo VARCHAR(10) NOT NULL,
                        descricao TEXT NOT NULL,
                        valor DECIMAL(10, 2) NOT NULL,
                        pontos INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Insere alguns dados de exemplo
                logger.info("Inserindo dados de exemplo na tabela 'infracoes'...")
                cur.execute("""
                    INSERT INTO infracoes (codigo, descricao, valor, pontos) VALUES
                    ('A01', 'Estacionar em local proibido', 293.47, 5),
                    ('A02', 'Avançar sinal vermelho', 293.47, 7),
                    ('A03', 'Dirigir sem cinto de segurança', 293.47, 5),
                    ('A04', 'Excesso de velocidade até 20%', 130.16, 4),
                    ('A05', 'Excesso de velocidade entre 20% e 50%', 195.23, 5),
                    ('A06', 'Excesso de velocidade acima de 50%', 880.41, 7),
                    ('A07', 'Dirigir sob influência de álcool', 2934.70, 7),
                    ('A08', 'Dirigir sem habilitação', 880.41, 7),
                    ('A09', 'Usar celular ao dirigir', 293.47, 5),
                    ('A10', 'Parar sobre a faixa de pedestres', 293.47, 5)
                """)
            else:
                logger.info("Tabela 'infracoes' já existe.")
            
            # Cria tabela de autos de infração se não existir
            if 'autos' not in existing_tables:
                logger.info("Criando tabela 'autos'...")
                cur.execute("""
                    CREATE TABLE autos (
                        id SERIAL PRIMARY KEY,
                        placa VARCHAR(8) NOT NULL,
                        data_infracao TIMESTAMP NOT NULL,
                        local_infracao TEXT NOT NULL,
                        infracao_id INTEGER REFERENCES infracoes(id),
                        agente VARCHAR(100) NOT NULL,
                        observacoes TEXT,
                        status VARCHAR(20) DEFAULT 'pendente',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            else:
                logger.info("Tabela 'autos' já existe.")
            
            conn.commit()
            logger.info("Tabelas criadas com sucesso!")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao criar tabelas: {e}")
        raise

def main():
    """Função principal que executa a criação das tabelas."""
    try:
        logger.info("Iniciando criação de tabelas no Railway...")
        conn = get_connection()
        create_tables(conn)
        conn.close()
        logger.info("Processo concluído com sucesso!")
    except Exception as e:
        logger.error(f"Erro durante a execução: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 