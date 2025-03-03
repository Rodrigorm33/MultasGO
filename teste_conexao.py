#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import psycopg2
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def testar_conexao():
    """Testa a conexão com o banco de dados usando variáveis individuais."""
    try:
        # Obter variáveis de ambiente
        host = os.environ.get("PGHOST", "postgres.railway.internal")
        port = os.environ.get("PGPORT", "5432")
        user = os.environ.get("PGUSER", "postgres")
        password = os.environ.get("PGPASSWORD", "")
        dbname = os.environ.get("PGDATABASE", "railway")
        
        logging.info(f"Tentando conectar a: host={host}, port={port}, dbname={dbname}, user={user}")
        
        # Conectar ao banco de dados
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname
        )
        
        logging.info("Conexão estabelecida com sucesso!")
        
        # Verificar tabelas existentes
        with conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tabelas = [tabela[0] for tabela in cur.fetchall()]
            logging.info(f"Tabelas no banco de dados: {tabelas}")
            
            # Criar tabela infracoes se não existir
            if 'infracoes' not in tabelas:
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
                conn.commit()
                logging.info("Tabela 'infracoes' criada com sucesso!")
                
                # Inserir dados de exemplo
                logging.info("Inserindo dados de exemplo na tabela 'infracoes'...")
                cur.execute("""
                    INSERT INTO infracoes (codigo, descricao, valor, pontos)
                    VALUES 
                        ('A01', 'Estacionar em local proibido', 293.47, 5),
                        ('A02', 'Avancar sinal vermelho', 293.47, 7),
                        ('A03', 'Dirigir sem cinto de seguranca', 293.47, 5)
                """)
                conn.commit()
                logging.info("Dados inseridos com sucesso!")
            
            # Criar tabela bdbautos se não existir
            if 'bdbautos' not in tabelas:
                logging.info("Criando tabela 'bdbautos'...")
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
                conn.commit()
                logging.info("Tabela 'bdbautos' criada com sucesso!")
                
                # Criar índices
                logging.info("Criando índices para a tabela 'bdbautos'...")
                cur.execute("CREATE INDEX idx_bdbautos_placa ON bdbautos(placa)")
                cur.execute("CREATE INDEX idx_bdbautos_data_infracao ON bdbautos(data_infracao)")
                cur.execute("CREATE INDEX idx_bdbautos_status ON bdbautos(status)")
                conn.commit()
                logging.info("Índices criados com sucesso!")
                
                # Inserir dados de exemplo
                logging.info("Inserindo dados de exemplo na tabela 'bdbautos'...")
                cur.execute("""
                    INSERT INTO bdbautos (placa, data_infracao, local_infracao, infracao_id, agente, observacoes, status)
                    VALUES 
                        ('ABC1234', '2025-02-15 10:30:00', 'Avenida Paulista, 1000', 1, 'Carlos Silva', 'Veiculo estacionado em local proibido', 'pendente'),
                        ('DEF5678', '2025-02-20 15:45:00', 'Rua Augusta, 500', 2, 'Ana Oliveira', 'Condutor sem cinto de seguranca', 'pago')
                """)
                conn.commit()
                logging.info("Dados inseridos com sucesso!")
        
        # Verificar contagem de registros
        with conn.cursor() as cur:
            for tabela in ['infracoes', 'bdbautos']:
                if tabela in tabelas:
                    cur.execute(f"SELECT COUNT(*) FROM {tabela}")
                    count = cur.fetchone()[0]
                    logging.info(f"Tabela '{tabela}' tem {count} registros.")
        
        conn.close()
        logging.info("Teste de conexão e configuração do banco de dados concluído com sucesso!")
        return True
        
    except Exception as e:
        logging.error(f"Erro durante a conexão ou configuração do banco de dados: {e}")
        return False

if __name__ == "__main__":
    if testar_conexao():
        sys.exit(0)
    else:
        sys.exit(1) 