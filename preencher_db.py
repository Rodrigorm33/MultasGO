#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script to populate the database tables for MultasGO.
Execute with: railway run python preencher_db.py
"""

import os
import sys
import psycopg2
import random
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Infraction data
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
    ("A10", "Parar sobre a faixa de pedestres", 293.47, 5)
]

# Sample license plates
PLACAS = [
    "ABC1234", "DEF5678", "GHI9012", "JKL3456", "MNO7890",
    "PQR1234", "STU5678", "VWX9012", "YZA3456", "BCD7890"
]

# Sample locations
LOCAIS = [
    "Avenida Paulista, 1000", 
    "Rua Augusta, 500", 
    "Avenida Reboucas, 750", 
    "Rua Oscar Freire, 200", 
    "Avenida Brigadeiro Faria Lima, 1500"
]

# Sample agents
AGENTES = [
    "Carlos Silva", 
    "Ana Oliveira", 
    "Roberto Santos", 
    "Juliana Costa", 
    "Marcos Pereira"
]

# Sample observations
OBSERVACOES = [
    "Veiculo estacionado em local proibido",
    "Condutor sem cinto de seguranca",
    "Veiculo em alta velocidade",
    "Ultrapassagem em local proibido",
    "Condutor utilizando celular",
    None  # Some entries may not have observations
]

# Possible statuses
STATUS = ["pendente", "pago", "cancelado", "em recurso"]

def get_connection():
    """Establish connection to the database using individual environment variables."""
    try:
        # Use only individual variables to avoid encoding issues
        logging.info("Connecting using PG* variables")
        host = os.environ.get("PGHOST", "postgres.railway.internal")
        port = os.environ.get("PGPORT", "5432")
        user = os.environ.get("PGUSER", "postgres")
        password = os.environ.get("PGPASSWORD", "")
        dbname = os.environ.get("PGDATABASE", "railway")
        
        logging.info(f"Connecting to: host={host}, port={port}, dbname={dbname}, user={user}")
        
        return psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname
        )
    except Exception as e:
        logging.error(f"Error connecting to database: {e}")
        raise

def generate_random_date():
    """Generate a random date within the last 90 days."""
    random_days = random.randint(0, 90)
    random_date = datetime.now() - timedelta(days=random_days)
    return random_date.strftime("%Y-%m-%d %H:%M:%S")

def setup_infracoes(conn):
    """Set up the infracoes table."""
    try:
        with conn.cursor() as cur:
            # Check if table exists
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'infracoes')")
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                logging.info("Creating 'infracoes' table...")
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
                logging.info("Table 'infracoes' created successfully!")
            
            # Check if table has records
            cur.execute("SELECT COUNT(*) FROM infracoes")
            count = cur.fetchone()[0]
            
            if count == 0:
                # Insert records
                logging.info(f"Inserting {len(INFRACOES)} records into 'infracoes' table...")
                
                for codigo, descricao, valor, pontos in INFRACOES:
                    cur.execute("""
                        INSERT INTO infracoes (codigo, descricao, valor, pontos)
                        VALUES (%s, %s, %s, %s)
                    """, (codigo, descricao, valor, pontos))
                
                conn.commit()
                logging.info(f"{len(INFRACOES)} records inserted successfully!")
            else:
                logging.info(f"Table 'infracoes' already has {count} records. Skipping insertion.")
            
    except Exception as e:
        conn.rollback()
        logging.error(f"Error setting up 'infracoes' table: {e}")
        raise

def setup_bdbautos(conn, num_records=20):
    """Set up the bdbautos table."""
    try:
        with conn.cursor() as cur:
            # Check if table exists
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'bdbautos')")
            table_exists = cur.fetchone()[0]
            
            if not table_exists:
                logging.info("Creating 'bdbautos' table...")
                cur.execute("""
                    CREATE TABLE bdbautos (
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
                
                # Create indexes
                logging.info("Creating indexes for 'bdbautos' table...")
                cur.execute("CREATE INDEX idx_bdbautos_placa ON bdbautos(placa)")
                cur.execute("CREATE INDEX idx_bdbautos_data_infracao ON bdbautos(data_infracao)")
                cur.execute("CREATE INDEX idx_bdbautos_status ON bdbautos(status)")
                
                logging.info("Table 'bdbautos' created successfully!")
            
            # Check if table has records
            cur.execute("SELECT COUNT(*) FROM bdbautos")
            count = cur.fetchone()[0]
            
            if count == 0:
                # Get infraction IDs
                cur.execute("SELECT id FROM infracoes")
                infracoes_ids = [row[0] for row in cur.fetchall()]
                
                if not infracoes_ids:
                    logging.error("No infractions found. Please populate 'infracoes' table first.")
                    return
                
                # Insert records
                logging.info(f"Inserting {num_records} records into 'bdbautos' table...")
                
                for _ in range(num_records):
                    placa = random.choice(PLACAS)
                    data_infracao = generate_random_date()
                    local_infracao = random.choice(LOCAIS)
                    infracao_id = random.choice(infracoes_ids)
                    agente = random.choice(AGENTES)
                    observacoes = random.choice(OBSERVACOES)
                    status = random.choice(STATUS)
                    
                    cur.execute("""
                        INSERT INTO bdbautos (placa, data_infracao, local_infracao, infracao_id, agente, observacoes, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (placa, data_infracao, local_infracao, infracao_id, agente, observacoes, status))
                
                conn.commit()
                logging.info(f"{num_records} records inserted successfully!")
            else:
                logging.info(f"Table 'bdbautos' already has {count} records. Skipping insertion.")
            
    except Exception as e:
        conn.rollback()
        logging.error(f"Error setting up 'bdbautos' table: {e}")
        raise

def main():
    """Main function."""
    try:
        logging.info("Starting database setup...")
        conn = get_connection()
        
        # Set up tables
        setup_infracoes(conn)
        setup_bdbautos(conn, 20)  # Insert 20 records
        
        # Check tables
        with conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [table[0] for table in cur.fetchall()]
            logging.info(f"Tables in database: {tables}")
            
            for table in ['infracoes', 'bdbautos']:
                if table in tables:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cur.fetchone()[0]
                    logging.info(f"Table '{table}' has {count} records.")
        
        conn.close()
        logging.info("Database setup completed successfully!")
        
    except Exception as e:
        logging.error(f"Error during execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 