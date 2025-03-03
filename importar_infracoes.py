#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import psycopg2
import logging
import csv
from io import StringIO

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Dados da tabela de infrações (formato CSV com separador ";")
DADOS_INFRACOES = """
Código de infração;Infração;Responsável;Valor da multa;Órgão Autuador;Artigos do CTB;Pontos;Gravidade
54870;Estacionar;Condutor;195.23;Municipal/Rodoviário;181 * XI;5.0;Grave
55173;Estacionar;Condutor;195.23;Municipal/Rodoviário;181 * XIV;5.0;Grave
55330;Estacionar;Condutor;195.23;Municipal/Rodoviário;181 * XVI;5.0;Grave
55172;Estacionar;Condutor;195.23;Municipal/Rodoviário;181 * XIV;5.0;Grave
56142;Parar na faixa;Condutor;195.23;Municipal/Rodoviário;182 * V;5.0;Grave
54527;Estacionar;Condutor;195.23;Municipal/Rodoviário;181 * VIII;5.0;Grave
76090;Organizar;PF ou PJ;17608.2;Municipal/Rodoviário;253-A, § 1º;7.0;Gravíssima 60 X
54524;Estacionar;Condutor;195.23;Municipal/Rodoviário;181 * VIII;5.0;Grave
54523;Estacionar;Condutor;195.23;Municipal/Rodoviário;181 * VIII;5.0;Grave
54010;Estacionar;Condutor;195.23;Municipal/Rodoviário;181, III;5.0;Grave
54525;Estacionar;Condutor;195.23;Municipal/Rodoviário;181 * VIII;5.0;Grave
56141;Parar na faixa;Condutor;195.23;Municipal/Rodoviário;182 * V;5.0;Grave
53550;Fazer ou deixar;Condutor;195.23;Municipal/Rodoviário;179 * I;5.0;Grave
54526;Estacionar;Condutor;195.23;Municipal/Rodoviário;181 * VIII;5.0;Grave
54522;Estacionar;Condutor;195.23;Municipal/Rodoviário;181 * VIII;5.0;Grave
54950;Estacionar;Condutor;195.23;Municipal/Rodoviário;181 * XII;5.0;Grave
55680;Estacionar;Condutor;195.23;Municipal/Rodoviário;181 * XIX;5.0;Grave
55171;Estacionar;Condutor;195.23;Municipal/Rodoviário;181 * XIV;5.0;Grave
55414;Estacionar;Condutor;195.23;Municipal/Rodoviário;181 * XVII;5.0;Grave
54440;Estacionar;Condutor;88.38;Municipal/Rodoviário;181 * VII;3.0;Leve
55411;Estacionar;Condutor;195.23;Municipal/Rodoviário;181 * XVII;5.0;Grave
55412;Estacionar;Condutor;195.23;Municipal/Rodoviário;181 * XVII;5.0;Grave
"""

def get_connection():
    """Estabelece conexão com o banco de dados usando variáveis individuais."""
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
        return conn
        
    except Exception as e:
        logging.error(f"Erro durante a conexão ao banco de dados: {e}")
        raise

def criar_tabela_infracoes(conn):
    """Cria a tabela de infrações se não existir."""
    try:
        with conn.cursor() as cur:
            # Verificar se a tabela existe
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'infracoes')")
            tabela_existe = cur.fetchone()[0]
            
            if not tabela_existe:
                logging.info("Criando tabela 'infracoes'...")
                cur.execute("""
                    CREATE TABLE infracoes (
                        id SERIAL PRIMARY KEY,
                        codigo VARCHAR(10) NOT NULL,
                        descricao TEXT NOT NULL,
                        responsavel VARCHAR(50) NOT NULL,
                        valor DECIMAL(10, 2) NOT NULL,
                        orgao_autuador VARCHAR(100) NOT NULL,
                        artigo_ctb VARCHAR(100) NOT NULL,
                        pontos DECIMAL(3, 1) NOT NULL,
                        gravidade VARCHAR(50) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                logging.info("Tabela 'infracoes' criada com sucesso!")
            else:
                # Verificar se a tabela tem registros
                cur.execute("SELECT COUNT(*) FROM infracoes")
                count = cur.fetchone()[0]
                
                if count > 0:
                    logging.info(f"Tabela 'infracoes' já existe e contém {count} registros. Limpando tabela...")
                    cur.execute("TRUNCATE TABLE infracoes RESTART IDENTITY CASCADE")
                    conn.commit()
                    logging.info("Tabela 'infracoes' limpa com sucesso!")
                else:
                    logging.info("Tabela 'infracoes' existe mas está vazia.")
            
            return True
            
    except Exception as e:
        conn.rollback()
        logging.error(f"Erro ao criar tabela 'infracoes': {e}")
        return False

def importar_dados_infracoes(conn):
    """Importa os dados da tabela de infrações."""
    try:
        # Criar a tabela se necessário
        if not criar_tabela_infracoes(conn):
            return False
        
        # Processar os dados CSV
        csv_data = StringIO(DADOS_INFRACOES.strip())
        reader = csv.reader(csv_data, delimiter=';')
        
        # Pular o cabeçalho
        next(reader)
        
        # Inserir os dados
        with conn.cursor() as cur:
            count = 0
            for row in reader:
                if len(row) >= 8:  # Garantir que a linha tem todos os campos necessários
                    codigo = row[0].strip()
                    descricao = row[1].strip()
                    responsavel = row[2].strip()
                    valor = float(row[3].strip().replace(',', '.'))  # Substituir vírgula por ponto
                    orgao_autuador = row[4].strip()
                    artigo_ctb = row[5].strip()
                    pontos = float(row[6].strip().replace(',', '.'))  # Substituir vírgula por ponto
                    gravidade = row[7].strip()
                    
                    cur.execute("""
                        INSERT INTO infracoes (codigo, descricao, responsavel, valor, orgao_autuador, artigo_ctb, pontos, gravidade)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (codigo, descricao, responsavel, valor, orgao_autuador, artigo_ctb, pontos, gravidade))
                    count += 1
            
            conn.commit()
            logging.info(f"{count} registros inseridos na tabela 'infracoes'.")
            return True
            
    except Exception as e:
        conn.rollback()
        logging.error(f"Erro ao importar dados para a tabela 'infracoes': {e}")
        return False

def main():
    """Função principal."""
    try:
        # Estabelecer conexão
        conn = get_connection()
        
        # Importar dados
        if importar_dados_infracoes(conn):
            logging.info("Importação de dados concluída com sucesso!")
        else:
            logging.warning("Importação de dados não foi concluída.")
        
        # Verificar registros
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM infracoes")
            count = cur.fetchone()[0]
            logging.info(f"Total de registros na tabela 'infracoes': {count}")
            
            # Mostrar alguns registros
            cur.execute("SELECT codigo, descricao, valor, pontos, gravidade FROM infracoes LIMIT 5")
            registros = cur.fetchall()
            logging.info("Primeiros 5 registros:")
            for reg in registros:
                logging.info(f"  {reg}")
        
        conn.close()
        return True
        
    except Exception as e:
        logging.error(f"Erro durante a execução: {e}")
        return False

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1) 