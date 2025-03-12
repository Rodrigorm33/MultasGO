# Código completo para app/services/search_service.py
from sqlalchemy.orm import Session
from sqlalchemy import text
from rapidfuzz import fuzz, process
from typing import Dict, List, Any

from app.core.config import settings
from app.core.logger import logger
from app.models.infracao import Infracao

def pesquisar_infracoes(db: Session, query: str, limit: int = 10, skip: int = 0) -> Dict[str, Any]:
    """
    Pesquisa infrações por código ou descrição com suporte a busca aproximada (fuzzy search).
    
    Args:
        db: Sessão do banco de dados
        query: Termo de pesquisa (código ou descrição)
        limit: Número máximo de resultados a retornar
        skip: Número de resultados para pular (para paginação)
        
    Returns:
        Dict com resultados da pesquisa, contagem total e possível sugestão
    """
    query = query.strip()
    resultados = []
    total = 0
    sugestao = None
    mensagem = None
    
    try:
        # Busca exata por código
        codigo_search = f"%{query}%"
        
        # Usar SQL direto com parâmetros para evitar injeção de SQL
        sql_query = """
        SELECT * FROM bdbautos 
        WHERE "Código de Infração" LIKE :codigo_search
        ORDER BY "Código de Infração" ASC
        LIMIT :limit OFFSET :skip
        """
        
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
                # Criar objeto Infracao
                infracao = Infracao()
                
                # Criar um dicionário mapeando nomes de colunas para valores
                row_dict = {}
                for i, col in enumerate(colunas):
                    col_name = str(col)
                    if hasattr(col, 'name'):
                        col_name = col.name
                    if i < len(row):
                        row_dict[col_name] = row[i]
                
                infracao.codigo = row_dict.get("Código de Infração", "")
                infracao.descricao = row_dict.get("Infração", "")
                infracao.responsavel = row_dict.get("Responsável", "")
                infracao.valor_multa = row_dict.get("Valor da Multa", 0.0)
                infracao.orgao_autuador = row_dict.get("Órgão Autuador", "")
                infracao.artigos_ctb = row_dict.get("Artigos do CTB", "")
                infracao.pontos = row_dict.get("pontos", 0)
                infracao.gravidade = row_dict.get("gravidade", "")
                
                resultados_codigo.append(infracao)
            except Exception as e:
                logger.error(f"Erro ao processar resultado: {e}")
        
        # Se encontrou resultados pela busca de código, retorna
        if resultados_codigo:
            # Contar total de resultados para código
            count_sql = """
            SELECT COUNT(*) FROM bdbautos 
            WHERE "Código de Infração" LIKE :codigo_search
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
        
        result = db.execute(
            text(sql_query), 
            {"descricao_search": descricao_search, "limit": limit, "skip": skip}
        )
        
        # Processar resultados
        resultados_descricao = []
        for row in result:
            try:
                # Criar objeto Infracao
                infracao = Infracao()
                
                # Criar um dicionário mapeando nomes de colunas para valores
                row_dict = {}
                for i, col in enumerate(colunas):
                    col_name = str(col)
                    if hasattr(col, 'name'):
                        col_name = col.name
                    if i < len(row):
                        row_dict[col_name] = row[i]
                
                infracao.codigo = row_dict.get("Código de Infração", "")
                infracao.descricao = row_dict.get("Infração", "")
                infracao.responsavel = row_dict.get("Responsável", "")
                infracao.valor_multa = row_dict.get("Valor da Multa", 0.0)
                infracao.orgao_autuador = row_dict.get("Órgão Autuador", "")
                infracao.artigos_ctb = row_dict.get("Artigos do CTB", "")
                infracao.pontos = row_dict.get("pontos", 0)
                infracao.gravidade = row_dict.get("gravidade", "")
                
                resultados_descricao.append(infracao)
            except Exception as e:
                logger.error(f"Erro ao processar resultado: {e}")
        
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
        # Primeiro, buscar todas as descrições para comparação
        sql_query = """
        SELECT "Infração" FROM bdbautos
        LIMIT 1000
        """
        result = db.execute(text(sql_query))
        
        descricoes = []
        for row in result:
            descricoes.append(row[0])
        
        # Realizar busca fuzzy com a biblioteca RapidFuzz
        if descricoes:
            fuzzy_threshold = settings.FUZZY_SEARCH_THRESHOLD
            matches = process.extract(query, descricoes, scorer=fuzz.token_sort_ratio, limit=1)
            
            if matches and matches[0][1] >= fuzzy_threshold:
                sugestao = matches[0][0]
                
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
                        # Criar objeto Infracao
                        infracao = Infracao()
                        
                        # Criar um dicionário mapeando nomes de colunas para valores
                        row_dict = {}
                        for i, col in enumerate(colunas):
                            col_name = str(col)
                            if hasattr(col, 'name'):
                                col_name = col.name
                            if i < len(row):
                                row_dict[col_name] = row[i]
                        
                        infracao.codigo = row_dict.get("Código de Infração", "")
                        infracao.descricao = row_dict.get("Infração", "")
                        infracao.responsavel = row_dict.get("Responsável", "")
                        infracao.valor_multa = row_dict.get("Valor da Multa", 0.0)
                        infracao.orgao_autuador = row_dict.get("Órgão Autuador", "")
                        infracao.artigos_ctb = row_dict.get("Artigos do CTB", "")
                        infracao.pontos = row_dict.get("pontos", 0)
                        infracao.gravidade = row_dict.get("gravidade", "")
                        
                        resultados_sugestao.append(infracao)
                    except Exception as e:
                        logger.error(f"Erro ao processar resultado: {e}")
                
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
        return {
            "resultados": [],
            "total": 0,
            "mensagem": "Nenhum resultado encontrado.",
            "sugestao": sugestao
        }
        
    except Exception as e:
        logger.error(f"Erro ao pesquisar infrações: {e}")
        return {
            "resultados": [],
            "total": 0,
            "mensagem": f"Erro ao realizar a pesquisa: {str(e)}",
            "sugestao": None
        }