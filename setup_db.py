#!/usr/bin/env python
# -*- coding: ascii -*-

"""
Script to create tables for MultasGO in PostgreSQL database.
"""

import os
import sys
import psycopg2
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def main():
    """Main function to create tables."""
    try:
        # Get database connection
        logging.info("Connecting to database...")
        
        # Use DATABASE_URL if available
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            logging.info("Using DATABASE_URL")
            conn = psycopg2.connect(database_url)
        else:
            # Use individual variables
            logging.info("Using PG* variables")
            conn = psycopg2.connect(
                host=os.environ.get("PGHOST"),
                port=os.environ.get("PGPORT"),
                user=os.environ.get("PGUSER"),
                password=os.environ.get("PGPASSWORD"),
                dbname=os.environ.get("PGDATABASE")
            )
        
        logging.info("Connection established successfully!")
        
        # Create tables
        with conn.cursor() as cur:
            # Check existing tables
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            existing_tables = [table[0] for table in cur.fetchall()]
            logging.info(f"Existing tables: {existing_tables}")
            
            # Create infracoes table
            if 'infracoes' not in existing_tables:
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
                
                # Insert sample data
                logging.info("Inserting sample data into 'infracoes' table...")
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
                logging.info("Table 'infracoes' already exists.")
            
            # Create autos table
            if 'autos' not in existing_tables:
                logging.info("Creating 'autos' table...")
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
                
                # Create indexes
                logging.info("Creating indexes for 'autos' table...")
                cur.execute("CREATE INDEX idx_autos_placa ON autos(placa)")
                cur.execute("CREATE INDEX idx_autos_data_infracao ON autos(data_infracao)")
                cur.execute("CREATE INDEX idx_autos_status ON autos(status)")
            else:
                logging.info("Table 'autos' already exists.")
            
            # Commit changes
            conn.commit()
            logging.info("Tables created successfully!")
        
        # Close connection
        conn.close()
        logging.info("Process completed successfully!")
        
    except Exception as e:
        logging.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 