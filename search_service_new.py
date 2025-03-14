# search_service_new.py
import os
import psycopg2
import re
import logging
from typing import Dict, List, Any, Optional

# Configurar logging
logger = logging.getLogger("MultasGO-SearchService")

def get_connection():
    """Estabelece conexão direta com o banco contornando problemas de codificação"""
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Extrair partes da URL
    if '@' in DATABASE_URL:
        host_part = DATABASE_URL.split('@')[1]
        host = host_part.split('/')[0]
        if ':' in host:
            host = host.split(':')[0]
    else:
        host = 'localhost'
    
    if '/' in DATABASE_URL:
        parts = DATABASE_URL.split('/')
        dbname = parts[-1]
    else:
        dbname = 'postgres'
    
    if '//' in DATABASE_URL and '@' in DATABASE_URL:
        user_pass = DATABASE_URL.split('//')[1].split('@')[0]
        if ':' in user_pass:
            user = user_pass.split(':')[0]
            password = user_pass.split(':')[1]
        else:
            user = user_pass
            password = ''
    else:
        user = 'postgres'
        password = ''
    
    port = '5432'
    if '@' in DATABASE_URL and ':' in DATABASE_URL.split('@')[1]:
        port_part = DATABASE_URL.split('@')[1].split('/')[0]
        if ':' in port_part:
            port = port_part.split(':')[1]
    
    # Conectar com parâmetros extraídos
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    
    return conn

def pesquisar_infracoes(termo: str, limit: int = 10, skip: int = 0) -> Dict[str, Any]:
    """
    Pesquisa infrações no banco de dados
    
    Args:
        termo (str): Termo de busca (código ou descrição)
        limit (int): Limite de resultados
        skip (int): Offset para paginação
        
    Returns:
        Dict com resultados da pesquisa
    """
    logger.info(f"Pesquisando por '{termo}' (limit={limit}, skip={skip})")
    
    try:
        # Validação básica
        if not termo or len(termo.strip()) == 0:
            return {
                "total": 0,
                "resultados": [],
                "mensagem": "Termo de busca vazio"
            }
        
        # Conectar ao banco
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verificar se o termo é um código numérico
        is_codigo = bool(re.match(r'^\d+', termo.strip()))
        
        if is_codigo:
            logger.info(f"Buscando por código: {termo}")
            query = """
            SELECT * FROM bdbautos 
            WHERE "Código de Infração" LIKE %s 
            LIMIT %s OFFSET %s
            """
            cursor.execute(query, [f"%{termo}%", limit, skip])
        else:
            logger.info(f"Buscando por texto: {termo}")
            query = """
            SELECT * FROM bdbautos 
            WHERE "Infração" ILIKE %s 
            OR "Artigos do CTB" ILIKE %s
            OR "Responsável" ILIKE %s
            LIMIT %s OFFSET %s
            """
            param = f"%{termo}%"
            cursor.execute(query, [param, param, param, limit, skip])
        
        # Processar resultados
        resultados = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description]
        
        # Formatar dados
        dados = []
        for row in resultados:
            item = {}
            for i, col in enumerate(colunas):
                if row[i] is not None:
                    item[col] = str(row[i])
                else:
                    item[col] = None
            dados.append(item)
        
        conn.close()
        logger.info(f"Encontrados {len(dados)} resultados")
        
        return {
            "total": len(dados),
            "resultados": dados,
            "colunas": colunas
        }
        
    except Exception as e:
        logger.error(f"Erro na pesquisa: {str(e)}")
        return {
            "total": 0,
            "resultados": [],
            "erro": str(e)
        }