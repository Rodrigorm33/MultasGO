#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para preencher a tabela bdbautos com dados de exemplo.
Execute com: railway run python preencher_bdbautos.py
"""

import os
import sys
import psycopg2
import random
from datetime import datetime, timedelta
import logging

# Configuracao de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Lista de placas de exemplo
PLACAS = [
    "ABC1234", "DEF5678", "GHI9012", "JKL3456", "MNO7890",
    "PQR1234", "STU5678", "VWX9012", "YZA3456", "BCD7890",
    "EFG1234", "HIJ5678", "KLM9012", "NOP3456", "QRS7890"
]

# Lista de locais de exemplo
LOCAIS = [
    "Avenida Paulista, 1000", 
    "Rua Augusta, 500", 
    "Avenida Rebouças, 750", 
    "Rua Oscar Freire, 200", 
    "Avenida Brigadeiro Faria Lima, 1500",
    "Rua da Consolação, 800", 
    "Avenida Santo Amaro, 600", 
    "Rua Haddock Lobo, 350", 
    "Avenida Nove de Julho, 1200", 
    "Rua Pamplona, 450"
]

# Lista de agentes de exemplo
AGENTES = [
    "Carlos Silva", 
    "Ana Oliveira", 
    "Roberto Santos", 
    "Juliana Costa", 
    "Marcos Pereira",
    "Patricia Lima", 
    "Fernando Souza", 
    "Camila Rodrigues", 
    "Ricardo Almeida", 
    "Luciana Ferreira"
]

# Lista de observações de exemplo
OBSERVACOES = [
    "Veículo estacionado em local proibido",
    "Condutor sem cinto de segurança",
    "Veículo em alta velocidade",
    "Ultrapassagem em local proibido",
    "Condutor utilizando celular",
    "Veículo com farol apagado",
    "Condutor sem habilitação",
    "Veículo com documentação vencida",
    "Condutor avançou sinal vermelho",
    "Veículo em faixa exclusiva de ônibus",
    None  # Algumas entradas podem não ter observações
]

# Status possíveis
STATUS = ["pendente", "pago", "cancelado", "em recurso"]

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

def gerar_data_aleatoria():
    """Gera uma data aleatória nos últimos 90 dias."""
    dias_aleatorios = random.randint(0, 90)
    data_aleatoria = datetime.now() - timedelta(days=dias_aleatorios)
    return data_aleatoria.strftime("%Y-%m-%d %H:%M:%S")

def preencher_tabela(conn, num_registros=20):
    """Preenche a tabela bdbautos com dados de exemplo."""
    try:
        with conn.cursor() as cur:
            # Verificar se a tabela existe
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'bdbautos')")
            tabela_existe = cur.fetchone()[0]
            
            if not tabela_existe:
                logging.error("A tabela 'bdbautos' não existe. Crie a tabela antes de executar este script.")
                return
            
            # Verificar se já existem registros
            cur.execute("SELECT COUNT(*) FROM bdbautos")
            count = cur.fetchone()[0]
            
            if count > 0:
                logging.info(f"A tabela 'bdbautos' já contém {count} registros.")
                resposta = input("Deseja adicionar mais registros? (s/n): ").lower()
                if resposta != 's':
                    logging.info("Operação cancelada pelo usuário.")
                    return
            
            # Obter IDs das infrações disponíveis
            cur.execute("SELECT id FROM infracoes")
            infracoes_ids = [row[0] for row in cur.fetchall()]
            
            if not infracoes_ids:
                logging.error("Não há infrações cadastradas. Cadastre infrações antes de preencher a tabela 'bdbautos'.")
                return
            
            # Inserir registros
            logging.info(f"Inserindo {num_registros} registros na tabela 'bdbautos'...")
            
            for _ in range(num_registros):
                placa = random.choice(PLACAS)
                data_infracao = gerar_data_aleatoria()
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
            logging.info(f"{num_registros} registros inseridos com sucesso!")
            
            # Contar registros após a inserção
            cur.execute("SELECT COUNT(*) FROM bdbautos")
            novo_count = cur.fetchone()[0]
            logging.info(f"Total de registros na tabela 'bdbautos': {novo_count}")
            
    except Exception as e:
        conn.rollback()
        logging.error(f"Erro ao preencher a tabela: {e}")
        raise

def main():
    """Função principal."""
    try:
        logging.info("Iniciando preenchimento da tabela 'bdbautos'...")
        conn = get_connection()
        
        # Número de registros a serem inseridos
        num_registros = 20
        if len(sys.argv) > 1:
            try:
                num_registros = int(sys.argv[1])
            except ValueError:
                logging.warning(f"Valor inválido para número de registros: {sys.argv[1]}. Usando o valor padrão: 20")
        
        preencher_tabela(conn, num_registros)
        conn.close()
        logging.info("Processo concluído com sucesso!")
        
    except Exception as e:
        logging.error(f"Erro durante a execução: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 