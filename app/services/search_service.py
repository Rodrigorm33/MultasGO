from sqlalchemy.orm import Session
from sqlalchemy import text
from rapidfuzz import fuzz, process
from typing import Dict, List, Any
import traceback

from app.core.config import settings
from app.core.logger import logger
from app.models.infracao import Infracao

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
        # Busca exata por código
        codigo_search = f"%{query}%"
        
        # Converter o campo "Código de Infração" para texto antes de usar LIKE
        sql_query = """
        SELECT * FROM bdbautos 
        WHERE CAST("Código de Infração" AS TEXT) LIKE :codigo_search
        ORDER BY "Código de Infração" ASC
        LIMIT :limit OFFSET :skip
        """
        
        logger.info(f"Executando consulta SQL para código: {sql_query} com parâmetro: {codigo_search}")
        
        result = db.execute(
            text(sql_query), 
            {"codigo_search": codigo_search, "limit": limit, "skip": skip}
        )
        
        # Obter os nomes das colunas
        colunas = result.keys()
        
        # Processar resultados
        resultados_codigo = []
        for row in result:
            try:
                # Criar um dicionário mapeando nomes de colunas para valores
                row_dict = {}
                for i, col in enumerate(colunas):
                    col_name = str(col)
                    if hasattr(col, 'name'):
                        col_name = col.name
                    if i < len(row):
                        row_dict[col_name] = row[i]
                
                # Criar objeto Infracao manualmente para lidar com possíveis tipos de dados incompatíveis
                infracao = Infracao(
                    codigo=str(row_dict.get("Código de Infração", "")),
                    descricao=str(row_dict.get("Infração", "")),
                    responsavel=str(row_dict.get("Responsável", "")),
                    valor_multa=float(row_dict.get("Valor da Multa", 0.0)),
                    orgao_autuador=str(row_dict.get("Órgão Autuador", "")),
                    artigos_ctb=str(row_dict.get("Artigos do CTB", "")),
                    pontos=int(row_dict.get("pontos", 0)),
                    gravidade=str(row_dict.get("gravidade", ""))
                )
                
                resultados_codigo.append(infracao)
            except Exception as e:
                logger.error(f"Erro ao processar resultado: {e}")
                logger.error(f"Detalhes do erro: {traceback.format_exc()}")
        
        # Se encontrou resultados pela busca de código, retorna
        if resultados_codigo:
            # Contar total de resultados para código
            count_sql = """
            SELECT COUNT(*) FROM bdbautos 
            WHERE CAST("Código de Infração" AS TEXT) LIKE :codigo_search
            """
            total_result = db.execute(text(count_sql), {"codigo_search": codigo_search})
            for row in total_result:
                total = row[0]
                break
                
            return {
                "resultados": resultados_codigo,
                "total": total,
                "mensagem": None,
                "sugestao": None
            }
        
        # Se não encontrou por código, busca por descrição
        descricao_search = f"%{query}%"
        sql_query = """
        SELECT * FROM bdbautos 
        WHERE "Infração" ILIKE :descricao_search
        ORDER BY "Infração" ASC
        LIMIT :limit OFFSET :skip
        """
        
        logger.info(f"Executando consulta SQL para descrição: {sql_query} com parâmetro: {descricao_search}")
        
        result = db.execute(
            text(sql_query), 
            {"descricao_search": descricao_search, "limit": limit, "skip": skip}
        )
        
        # Processar resultados
        resultados_descricao = []
        for row in result:
            try:
                # Criar um dicionário mapeando nomes de colunas para valores
                row_dict = {}
                for i, col in enumerate(colunas):
                    col_name = str(col)
                    if hasattr(col, 'name'):
                        col_name = col.name
                    if i < len(row):
                        row_dict[col_name] = row[i]
                
                # Criar objeto Infracao manualmente
                infracao = Infracao(
                    codigo=str(row_dict.get("Código de Infração", "")),
                    descricao=str(row_dict.get("Infração", "")),
                    responsavel=str(row_dict.get("Responsável", "")),
                    valor_multa=float(row_dict.get("Valor da Multa", 0.0)),
                    orgao_autuador=str(row_dict.get("Órgão Autuador", "")),
                    artigos_ctb=str(row_dict.get("Artigos do CTB", "")),
                    pontos=int(row_dict.get("pontos", 0)),
                    gravidade=str(row_dict.get("gravidade", ""))
                )
                
                resultados_descricao.append(infracao)
            except Exception as e:
                logger.error(f"Erro ao processar resultado: {e}")
                logger.error(f"Detalhes do erro: {traceback.format_exc()}")
        
        if resultados_descricao:
            # Contar total de resultados para descrição
            count_sql = """
            SELECT COUNT(*) FROM bdbautos 
            WHERE "Infração" ILIKE :descricao_search
            """
            total_result = db.execute(text(count_sql), {"descricao_search": descricao_search})
            for row in total_result:
                total = row[0]
                break
                
            return {
                "resultados": resultados_descricao,
                "total": total,
                "mensagem": None,
                "sugestao": None
            }
        
        # Se não encontrou resultados, realizar busca fuzzy
        sql_query = """
        SELECT "Infração" FROM bdbautos
        LIMIT 1000
        """
        logger.info(f"Executando consulta SQL para busca fuzzy: {sql_query}")
        
        result = db.execute(text(sql_query))
        
        descricoes = []
        for row in result:
            descricoes.append(row[0])
        
        logger.info(f"Número de descrições para busca fuzzy: {len(descricoes)}")
        
        # Realizar busca fuzzy com a biblioteca RapidFuzz
        if descricoes:
            fuzzy_threshold = settings.FUZZY_SEARCH_THRESHOLD
            matches = process.extract(query, descricoes, scorer=fuzz.token_sort_ratio, limit=1)
            
            if matches and matches[0][1] >= fuzzy_threshold:
                sugestao = matches[0][0]
                logger.info(f"Sugestão fuzzy encontrada: {sugestao} com score {matches[0][1]}")
                
                # Buscar resultados com a sugestão
                sugestao_search = f"%{sugestao}%"
                sql_query = """
                SELECT * FROM bdbautos 
                WHERE "Infração" ILIKE :descricao_search
                ORDER BY "Infração" ASC
                LIMIT :limit OFFSET :skip
                """
                
                result = db.execute(
                    text(sql_query), 
                    {"descricao_search": sugestao_search, "limit": limit, "skip": skip}
                )
                
                # Processar resultados
                resultados_sugestao = []
                for row in result:
                    try:
                        # Criar um dicionário mapeando nomes de colunas para valores
                        row_dict = {}
                        for i, col in enumerate(colunas):
                            col_name = str(col)
                            if hasattr(col, 'name'):
                                col_name = col.name
                            if i < len(row):
                                row_dict[col_name] = row[i]
                        
                        # Criar objeto Infracao manualmente
                        infracao = Infracao(
                            codigo=str(row_dict.get("Código de Infração", "")),
                            descricao=str(row_dict.get("Infração", "")),
                            responsavel=str(row_dict.get("Responsável", "")),
                            valor_multa=float(row_dict.get("Valor da Multa", 0.0)),
                            orgao_autuador=str(row_dict.get("Órgão Autuador", "")),
                            artigos_ctb=str(row_dict.get("Artigos do CTB", "")),
                            pontos=int(row_dict.get("pontos", 0)),
                            gravidade=str(row_dict.get("gravidade", ""))
                        )
                        
                        resultados_sugestao.append(infracao)
                    except Exception as e:
                        logger.error(f"Erro ao processar resultado: {e}")
                        logger.error(f"Detalhes do erro: {traceback.format_exc()}")
                
                # Retornar resultados encontrados com a sugestão
                if resultados_sugestao:
                    # Contar total de resultados para sugestão
                    count_sql = """
                    SELECT COUNT(*) FROM bdbautos 
                    WHERE "Infração" ILIKE :descricao_search
                    """
                    total_result = db.execute(text(count_sql), {"descricao_search": sugestao_search})
                    for row in total_result:
                        total = row[0]
                        break
                        
                    return {
                        "resultados": resultados_sugestao,
                        "total": total,
                        "mensagem": f"Mostrando resultados para '{sugestao}'.",
                        "sugestao": sugestao
                    }
        
        # Se chegou aqui, não encontrou nenhum resultado
        logger.info("Nenhum resultado encontrado em nenhuma das buscas")
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