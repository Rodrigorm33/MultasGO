#!/usr/bin/env python

"""
Simple script to create tables in PostgreSQL database on Railway.
"""

import os
import sys
import psycopg2

def main():
    """Main function to create tables."""
    print("Creating tables in PostgreSQL database...")
    
    # SQL commands to create tables
    sql_commands = [
        # Create infracoes table
        """
        CREATE TABLE IF NOT EXISTS infracoes (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(10) NOT NULL,
            descricao TEXT NOT NULL,
            valor DECIMAL(10, 2) NOT NULL,
            pontos INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        # Check if infracoes table is empty and insert data
        """
        DO $$
        BEGIN
            IF (SELECT COUNT(*) FROM infracoes) = 0 THEN
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
                ('A10', 'Parar sobre a faixa de pedestres', 293.47, 5);
            END IF;
        END $$
        """,
        
        # Create autos table
        """
        CREATE TABLE IF NOT EXISTS autos (
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
        """,
        
        # Create indexes
        "CREATE INDEX IF NOT EXISTS idx_autos_placa ON autos(placa)",
        "CREATE INDEX IF NOT EXISTS idx_autos_data_infracao ON autos(data_infracao)",
        "CREATE INDEX IF NOT EXISTS idx_autos_status ON autos(status)"
    ]
    
    try:
        # Connect to the database
        print("Connecting to database...")
        
        # Use DATABASE_URL if available
        database_url = os.environ.get("DATABASE_URL")
        if database_url:
            print("Using DATABASE_URL")
            conn = psycopg2.connect(database_url)
        else:
            # Use individual variables
            print("Using PG* variables")
            conn = psycopg2.connect(
                host=os.environ.get("PGHOST"),
                port=os.environ.get("PGPORT"),
                user=os.environ.get("PGUSER"),
                password=os.environ.get("PGPASSWORD"),
                dbname=os.environ.get("PGDATABASE")
            )
        
        print("Connection established successfully!")
        
        # Create tables
        with conn.cursor() as cur:
            # Execute each SQL command
            for command in sql_commands:
                print(f"Executing: {command[:50]}...")
                cur.execute(command)
            
            # Commit changes
            conn.commit()
            
            # Check existing tables
            print("Checking tables...")
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [table[0] for table in cur.fetchall()]
            print(f"Tables in database: {tables}")
            
            # Count records
            print("Counting records...")
            cur.execute("SELECT COUNT(*) FROM infracoes")
            infracoes_count = cur.fetchone()[0]
            print(f"Records in infracoes table: {infracoes_count}")
            
            cur.execute("SELECT COUNT(*) FROM autos")
            autos_count = cur.fetchone()[0]
            print(f"Records in autos table: {autos_count}")
        
        # Close connection
        conn.close()
        print("Tables created successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 