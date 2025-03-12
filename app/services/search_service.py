from sqlalchemy.orm import Session
from sqlalchemy import text
from rapidfuzz import fuzz, process
from typing import Dict, List, Any
import traceback

from app.core.config import settings
from app.core.logger import logger
from app.models.infracao import Infracao

def diagnostico_banco(db: Session):
    """
    Função de diagnóstico para listar os primeiros 10 registros do banco de dados.
    """
    try:
        sql_query = """
        SELECT * FROM bdbautos 
        LIMIT 10
        """
        
        result = db.execute(text(sql_query))
        
        # Obter os nomes das colunas
        colunas = result.keys()
        
        logger.info(f"Diagnóstico de banco - colunas: {[col for col in colunas]}")
        
        # Coletar e logar os primeiros registros
        registros = []
        for row in result:
            registro = {}
            for i, col in enumerate(colunas):
                col_name = str(col)
                if hasattr(col, 'name'):
                    col_name = col.name
                if i < len(row):
                    registro[col_name] = row[i]
            registros.append(registro)
        
        logger.info(f"Diagnóstico de banco - primeiros registros: {registros}")
        
        return registros
    except Exception as e:
        logger.error(f"Erro no diagnóstico de banco: {e}")
        return []

def pesquisar_infracoes(db: Session, query: str, limit: int = 10, skip: int = 0) -> Dict[str, Any]:
    """
    Pesquisa infrações por código ou descrição com suporte a busca aproximada (fuzzy search).
    """
    query = query.strip()
    resultados = []
    total = 0
    sugestao = None
    mensagem = None
    
    try:
        # Executar diagnóstico primeiro para verificar a conexão com o banco
        diagnostico = diagnostico_banco(db)
        logger.info(f"Resultado do diagnóstico: encontrados {len(diagnostico)} registros de exemplo")
        
        # Se o termo de pesquisa for numérico, buscar por código exato ou parcial
        is_numeric = query.isdigit()
        
        if is_numeric:
            # Busca pelo código exato ou parcial
            logger.info(f"Realizando busca numérica para: {query}")
            
            sql_query = """
            SELECT * FROM bdbautos 
            WHERE CAST("Código de Infração" AS TEXT) LIKE :codigo_search
            ORDER BY "Código de Infração" ASC
            LIMIT :limit OFFSET :skip
            """
            
            codigo_search = f"%{query}%"
            logger.info(f"Executando consulta SQL para código: {sql_query} com parâmetro: {codigo_search}")
            
            result = db.execute(
                text(sql_query), 
                {"codigo_search": codigo_search, "limit": limit, "skip": skip}
            )
        else:
            # Busca por texto em vários campos
            logger.info(f"Realizando busca textual para: {query}")
            
            sql_query = """
            SELECT * FROM bdbautos 
            WHERE "Infração" ILIKE :texto_search
               OR "Responsável" ILIKE :texto_search
               OR "Órgão Autuador" ILIKE :texto_search
               OR "Artigos do CTB" ILIKE :texto_search
               OR "gravidade" ILIKE :texto_search
            ORDER BY "Código de Infração" ASC
            LIMIT :limit OFFSET :skip
            """
            
            texto_search = f"%{query}%"
            logger.info(f"Executando consulta SQL para texto: {sql_query} com parâmetro: {texto_search}")
            
            result = db.execute(
                text(sql_query), 
                {"texto_search": texto_search, "limit": limit, "skip": skip}
            )
        
        # Obter os nomes das colunas
        colunas = result.keys()
        
        # Coletar resultados em uma lista
        rows = list(result)
        logger.info(f"Número de resultados na busca: {len(rows)}")
        
        # Processar resultados
        resultados_encontrados = []
        for row in rows:
            try:
                # Logar a linha completa para debug
                logger.info(f"Processando linha: {row}")
                
                # Criar um dicionário mapeando nomes de colunas para valores
                row_dict = {}
                for i, col in enumerate(colunas):
                    col_name = str(col)
                    if hasattr(col, 'name'):
                        col_name = col.name
                    if i < len(row):
                        row_dict[col_name] = row[i]
                
                # Logar o dicionário para debug
                logger.info(f"Row dict: {row_dict}")
                
                # Criar objeto Infracao com valores padrão para evitar erros de validação
                try:
                    infracao = Infracao(
                        codigo=str(row_dict.get("Código de Infração", "")),
                        descricao=str(row_dict.get("Infração", "")),
                        responsavel=str(row_dict.get("Responsável", "")),
                        valor_multa=float(row_dict.get("Valor da Multa", 0.0)),
                        orgao_autuador=str(row_dict.get("Órgão Autuador", "")),
                        artigos_ctb=str(row_dict.get("Artigos do CTB", "")),
                        pontos=int(float(str(row_dict.get("pontos", 0)))),
                        gravidade=str(row_dict.get("gravidade", ""))
                    )
                    resultados_encontrados.append(infracao)
                    logger.info(f"Objeto Infracao criado com sucesso: {infracao}")
                except Exception as e:
                    logger.error(f"Erro ao criar objeto Infracao: {e}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
            except Exception as e:
                logger.error(f"Erro ao processar resultado: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Se encontrou resultados, retorna
        if resultados_encontrados:
            # Contar total de resultados
            if is_numeric:
                count_sql = """
                SELECT COUNT(*) FROM bdbautos 
                WHERE CAST("Código de Infração" AS TEXT) LIKE :codigo_search
                """
                total_result = db.execute(text(count_sql), {"codigo_search": codigo_search})
            else:
                count_sql = """
                SELECT COUNT(*) FROM bdbautos 
                WHERE "Infração" ILIKE :texto_search
                   OR "Responsável" ILIKE :texto_search
                   OR "Órgão Autuador" ILIKE :texto_search
                   OR "Artigos do CTB" ILIKE :texto_search
                   OR "gravidade" ILIKE :texto_search
                """
                total_result = db.execute(text(count_sql), {"texto_search": texto_search})
                
            for row in total_result:
                total = row[0]
                break
                
            return {
                "resultados": resultados_encontrados,
                "total": total,
                "mensagem": None,
                "sugestao": None
            }
        
        # Se chegou aqui, não encontrou nenhum resultado
        logger.info("Nenhum resultado encontrado nas buscas")
        
        # Tentar com uma busca mais simples como última tentativa
        sql_query = """
        SELECT * FROM bdbautos 
        LIMIT 5
        """
        logger.info(f"Tentando busca simples: {sql_query}")
        
        result = db.execute(text(sql_query))
        sample_rows = list(result)
        
        if sample_rows:
            sugestao = "Tente um termo mais genérico como 'Estacionar' ou um número como '54'"
            logger.info(f"Banco tem dados, sugerindo termo mais genérico: {sugestao}")
            
        return {
            "resultados": [],
            "total": 0,
            "mensagem": "Nenhum resultado encontrado.",
            "sugestao": sugestao
        }
        
    except Exception as e:
        logger.error(f"Erro ao pesquisar infrações: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "resultados": [],
            "total": 0,
            "mensagem": f"Erro ao realizar a pesquisa: {str(e)}",
            "sugestao": None
        }