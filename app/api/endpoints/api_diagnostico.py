from fastapi import APIRouter, Query
from typing import Dict, Any, List
import psycopg2
import re
import os
from app.core.logger import logger
from app.services.importar_service import importar_csv_para_banco

router = APIRouter(prefix="/diagnostico", tags=["Diagnóstico"])

@router.get("/saude")
def verificar_saude() -> Dict[str, Any]:
    """Verifica a saúde da conexão com o banco de dados"""
    try:
        # Usar a mesma conexão que a aplicação já utiliza
        DATABASE_URL = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Testar consulta simples
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        # Verificar tabelas disponíveis
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = [table[0] for table in cursor.fetchall()]
        
        conn.close()
        
        return {
            "status": "ok",
            "database": "conectado",
            "tabelas": tables
        }
    except Exception as e:
        logger.error(f"Erro na verificação de saúde: {str(e)}")
        return {
            "status": "erro",
            "mensagem": str(e)
        }

@router.get("/importar")
def importar_dados() -> Dict[str, Any]:
    """Importa dados do arquivo CSV para o banco de dados"""
    try:
        success, message = importar_csv_para_banco()
        
        if success:
            return {
                "status": "sucesso",
                "mensagem": message
            }
        else:
            return {
                "status": "erro",
                "mensagem": message
            }
    except Exception as e:
        logger.error(f"Erro na importação: {str(e)}")
        return {
            "status": "erro",
            "mensagem": f"Erro inesperado: {str(e)}"
        }

@router.get("/busca-teste")
def buscar_teste(
    termo: str = Query(..., description="Termo para pesquisa"),
    limite: int = Query(10, description="Número máximo de resultados")
) -> Dict[str, Any]:
    """Testa a funcionalidade de busca de infrações"""
    try:
        # Usar a mesma conexão que a aplicação já utiliza
        DATABASE_URL = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Verificar se o termo é um código numérico
        is_codigo = bool(re.match(r'^\d+', termo))
        
        # Executar consulta conforme o tipo de termo
        if is_codigo:
            logger.info(f"Buscando por código: {termo}")
            query = """
            SELECT * FROM bdbautos 
            WHERE "Código de Infração" LIKE %s 
            LIMIT %s
            """
            cursor.execute(query, [f"%{termo}%", limite])
        else:
            logger.info(f"Buscando por texto: {termo}")
            query = """
            SELECT * FROM bdbautos 
            WHERE "Infração" ILIKE %s 
            OR "Artigos do CTB" ILIKE %s
            LIMIT %s
            """
            param = f"%{termo}%"
            cursor.execute(query, [param, param, limite])
        
        # Processar resultados
        resultados = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description]
        
        # Formatar dados
        dados = []
        for row in resultados:
            item = {}
            for i, col in enumerate(colunas):
                item[col] = str(row[i]) if row[i] is not None else None
            dados.append(item)
        
        conn.close()
        
        return {
            "status": "sucesso",
            "total": len(dados),
            "resultados": dados[:3]  # Limitar a exibição para não sobrecarregar a resposta
        }
        
    except Exception as e:
        logger.error(f"Erro na busca de teste: {str(e)}")
        return {
            "status": "erro",
            "mensagem": str(e)
        }