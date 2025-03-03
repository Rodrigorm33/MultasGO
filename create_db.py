#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script simplificado para criar as tabelas no banco de dados PostgreSQL do MultasGO.
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

def main():
    """Funcao principal para criar as tabelas."""
    try:
        # Obter a conexao com o banco de dados
        logging.info("Conectando ao banco de dados...")
        
        # Usar DATABASE_URL se disponivel
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            logging.info("Usando DATABASE_URL")
            conn = psycopg2.connect(database_url)
        else:
            # Usar variaveis individuais
            logging.info("Usando variaveis PG*")
            conn = psycopg2.connect(
                host=os.environ.get("PGHOST"),
                port=os.environ.get("PGPORT"),
                user=os.environ.get("PGUSER"),
                password=os.environ.get("PGPASSWORD"),
                dbname=os.environ.get("PGDATABASE")
            )
        
        logging.info("Conexao estabelecida com sucesso!")
        
        # Criar as tabelas
        with conn.cursor() as cur:
            # Verificar tabelas existentes
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            existing_tables = [table[0] for table in cur.fetchall()]
            logging.info(f"Tabelas existentes: {existing_tables}")
            
            # Criar tabela infracoes
            if 'infracoes' not in existing_tables:
                logging.info("Criando tabela 'infracoes'...")
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
                
                # Inserir dados de exemplo
                logging.info("Inserindo dados de exemplo na tabela 'infracoes'...")
                cur.execute("""
                    INSERT INTO infracoes (codigo, descricao, valor, pontos) VALUES
                    ('A01', 'Estacionar em local proibido', 293.47, 5),
                    ('A02', 'Avancar sinal vermelho', 293.47, 7),
                    ('A03', 'Dirigir sem cinto de seguranca', 293.47, 5),
                    ('A04', 'Excesso de velocidade ate 20%', 130.16, 4),
                    ('A05', 'Excesso de velocidade entre 20% e 50%', 195.23, 5),
                    ('A06', 'Excesso de velocidade acima de 50%', 880.41, 7),
                    ('A07', 'Dirigir sob influencia de alcool', 2934.70, 7),
                    ('A08', 'Dirigir sem habilitacao', 880.41, 7),
                    ('A09', 'Usar celular ao dirigir', 293.47, 5),
                    ('A10', 'Parar sobre a faixa de pedestres', 293.47, 5)
                """)
            else:
                logging.info("Tabela 'infracoes' ja existe.")
            
            # Criar tabela autos
            if 'autos' not in existing_tables:
                logging.info("Criando tabela 'autos'...")
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
                
                # Criar indices
                logging.info("Criando indices para a tabela 'autos'...")
                cur.execute("CREATE INDEX idx_autos_placa ON autos(placa)")
                cur.execute("CREATE INDEX idx_autos_data_infracao ON autos(data_infracao)")
                cur.execute("CREATE INDEX idx_autos_status ON autos(status)")
            else:
                logging.info("Tabela 'autos' ja existe.")
            
            # Commit das alteracoes
            conn.commit()
            logging.info("Tabelas criadas com sucesso!")
        
        # Fechar conexao
        conn.close()
        logging.info("Processo concluido com sucesso!")
        
    except Exception as e:
        logging.error(f"Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 