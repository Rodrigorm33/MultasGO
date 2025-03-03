#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para preencher a tabela infracoes com dados de exemplo.
Execute com: railway run python preencher_infracoes.py
"""

import os
import sys
import psycopg2
import logging

# Configuracao de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Dados de infrações
INFRACOES = [
    ("A01", "Estacionar em local proibido", 293.47, 5),
    ("A02", "Avancar sinal vermelho", 293.47, 7),
    ("A03", "Dirigir sem cinto de seguranca", 293.47, 5),
    ("A04", "Excesso de velocidade ate 20%", 130.16, 4),
    ("A05", "Excesso de velocidade entre 20% e 50%", 195.23, 5),
    ("A06", "Excesso de velocidade acima de 50%", 880.41, 7),
    ("A07", "Dirigir sob influencia de alcool", 2934.70, 7),
    ("A08", "Dirigir sem habilitacao", 880.41, 7),
    ("A09", "Usar celular ao dirigir", 293.47, 5),
    ("A10", "Parar sobre a faixa de pedestres", 293.47, 5),
    ("B01", "Transitar na contramao", 880.41, 7),
    ("B02", "Transitar em local proibido", 293.47, 5),
    ("B03", "Fazer conversao proibida", 293.47, 5),
    ("B04", "Nao dar preferencia ao pedestre", 293.47, 7),
    ("B05", "Transitar com veiculo em mau estado", 195.23, 5)
]

def get_connection():
    """Estabelece conexão com o banco de dados usando variáveis de ambiente."""
    try:
        # Usar DATABASE_URL se disponível
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            logging.info("Conectando usando DATABASE_URL")
            return psycopg2.connect(database_url)
        
        # Usar variáveis individuais
        logging.info("Conectando usando variáveis PG*")
        return psycopg2.connect(
            host=os.environ.get("PGHOST"),
            port=os.environ.get("PGPORT"),
            user=os.environ.get("PGUSER"),
            password=os.environ.get("PGPASSWORD"),
            dbname=os.environ.get("PGDATABASE")
        )
    except Exception as e:
        logging.error(f"Erro ao conectar ao banco de dados: {e}")
        raise

def preencher_tabela(conn):
    """Preenche a tabela infracoes com dados de exemplo."""
    try:
        with conn.cursor() as cur:
            # Verificar se a tabela existe
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'infracoes')")
            tabela_existe = cur.fetchone()[0]
            
            if not tabela_existe:
                logging.info("A tabela 'infracoes' não existe. Criando tabela...")
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
                logging.info("Tabela 'infracoes' criada com sucesso!")
            
            # Verificar se já existem registros
            cur.execute("SELECT COUNT(*) FROM infracoes")
            count = cur.fetchone()[0]
            
            if count > 0:
                logging.info(f"A tabela 'infracoes' já contém {count} registros.")
                resposta = input("Deseja limpar a tabela e inserir novos registros? (s/n): ").lower()
                if resposta == 's':
                    cur.execute("TRUNCATE TABLE infracoes RESTART IDENTITY CASCADE")
                    logging.info("Tabela 'infracoes' limpa com sucesso!")
                else:
                    logging.info("Mantendo registros existentes.")
                    return
            
            # Inserir registros
            logging.info(f"Inserindo {len(INFRACOES)} registros na tabela 'infracoes'...")
            
            for codigo, descricao, valor, pontos in INFRACOES:
                cur.execute("""
                    INSERT INTO infracoes (codigo, descricao, valor, pontos)
                    VALUES (%s, %s, %s, %s)
                """, (codigo, descricao, valor, pontos))
            
            conn.commit()
            logging.info(f"{len(INFRACOES)} registros inseridos com sucesso!")
            
            # Contar registros após a inserção
            cur.execute("SELECT COUNT(*) FROM infracoes")
            novo_count = cur.fetchone()[0]
            logging.info(f"Total de registros na tabela 'infracoes': {novo_count}")
            
    except Exception as e:
        conn.rollback()
        logging.error(f"Erro ao preencher a tabela: {e}")
        raise

def main():
    """Função principal."""
    try:
        logging.info("Iniciando preenchimento da tabela 'infracoes'...")
        conn = get_connection()
        preencher_tabela(conn)
        conn.close()
        logging.info("Processo concluído com sucesso!")
        
    except Exception as e:
        logging.error(f"Erro durante a execução: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 