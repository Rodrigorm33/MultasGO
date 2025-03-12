from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
import traceback

from app.db.database import get_db
from app.models.infracao import Infracao
from app.schemas.infracao import InfracaoResponse, InfracaoPesquisaResponse
from app.services.search_service import pesquisar_infracoes
from app.core.logger import logger

router = APIRouter()

@router.get("/", response_model=List[InfracaoResponse])
def listar_infracoes(
    skip: int = Query(0, description="Número de registros para pular (paginação)"),
    limit: int = Query(100, description="Número máximo de registros para retornar"),
    db: Session = Depends(get_db)
):
    """
    Retorna uma lista de infrações de trânsito.
    
    - **skip**: Número de registros para pular (paginação)
    - **limit**: Número máximo de registros para retornar
    """
    try:
        logger.info(f"Listando infrações com skip={skip}, limit={limit}")
        
        # Usar SQL direto em vez de ORM para evitar problemas com tipos de dados
        consulta_sql = f"SELECT * FROM bdbautos LIMIT {limit} OFFSET {skip}"
        logger.debug(f"Executando consulta SQL: {consulta_sql}")
        
        result = db.execute(text(consulta_sql))
        
        # Obter os nomes das colunas
        colunas = result.keys()
        logger.debug(f"Colunas encontradas: {[col for col in colunas]}")
        
        # Processar os resultados
        infracoes = []
        for row in result:
            try:
                # Criar objeto Infracao
                infracao = Infracao()
                
                # Verificar se row é um dicionário ou uma tupla
                if hasattr(row, 'items'):  # É um dicionário ou objeto semelhante
                    infracao.codigo = row["Código de Infração"]
                    infracao.descricao = row["Infração"]
                    infracao.responsavel = row["Responsável"]
                    infracao.valor_multa = row["Valor da Multa"]
                    infracao.orgao_autuador = row["Órgão Autuador"]
                    infracao.artigos_ctb = row["Artigos do CTB"]
                    infracao.pontos = row["pontos"]
                    infracao.gravidade = row["gravidade"]
                else:  # É uma tupla ou lista
                    # Criar um dicionário mapeando nomes de colunas para valores
                    row_dict = {}
                    for i, col in enumerate(colunas):
                        col_name = str(col)  # Garantir que o nome da coluna seja uma string
                        if hasattr(col, 'name'):
                            col_name = col.name
                        if i < len(row):
                            row_dict[col_name] = row[i]
                    
                    logger.debug(f"Row dict: {row_dict}")
                    
                    infracao.codigo = row_dict.get("Código de Infração", "")
                    infracao.descricao = row_dict.get("Infração", "")
                    infracao.responsavel = row_dict.get("Responsável", "")
                    infracao.valor_multa = row_dict.get("Valor da Multa", 0.0)
                    infracao.orgao_autuador = row_dict.get("Órgão Autuador", "")
                    infracao.artigos_ctb = row_dict.get("Artigos do CTB", "")
                    infracao.pontos = row_dict.get("pontos", 0)
                    infracao.gravidade = row_dict.get("gravidade", "")
                
                infracoes.append(infracao)
            except Exception as e:
                logger.error(f"Erro ao processar resultado: {e}")
                logger.error(f"Detalhes da linha: {row}")
                # Continuar com a próxima linha
        
        logger.info(f"Listagem de infrações: {len(infracoes)} registros retornados")
        
        if not infracoes:
            logger.warning("Nenhuma infração encontrada")
            return []
            
        return infracoes
    except Exception as e:
        error_detail = str(e)
        stack_trace = traceback.format_exc()
        logger.error(f"Erro ao listar infrações: {error_detail}")
        logger.error(f"Stack trace: {stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro ao listar infrações",
                "error": error_detail,
                "type": type(e).__name__
            }
        )

@router.get("/pesquisa", response_model=InfracaoPesquisaResponse)
def pesquisar(
    query: str = Query(..., description="Termo de pesquisa (código ou descrição da infração)"),
    skip: int = Query(0, description="Número de registros para pular (paginação)"),
    limit: int = Query(10, description="Número máximo de registros para retornar"),
    db: Session = Depends(get_db)
):
    """
    Pesquisa infrações por código ou descrição.
    
    - **query**: Termo de pesquisa (código ou descrição da infração)
    - **skip**: Número de registros para pular (paginação)
    - **limit**: Número máximo de registros para retornar
    
    A pesquisa suporta busca exata por código e busca fuzzy por descrição,
    permitindo encontrar resultados mesmo com erros de digitação.
    """
    try:
        logger.info(f"Iniciando pesquisa com termo: '{query}', skip={skip}, limit={limit}")
        
        if not query or len(query.strip()) < 2:
            logger.warning(f"Termo de pesquisa muito curto: '{query}'")
            return {
                "resultados": [],
                "total": 0,
                "mensagem": "O termo de pesquisa deve ter pelo menos 2 caracteres",
                "sugestao": None
            }
            
        resultados = pesquisar_infracoes(db, query, limit, skip)
        
        logger.info(f"Pesquisa concluída. Total de resultados: {resultados.get('total', 0)}")
        if resultados.get('sugestao'):
            logger.info(f"Sugestão encontrada: '{resultados['sugestao']}'")
            
        return resultados
    except Exception as e:
        error_detail = str(e)
        stack_trace = traceback.format_exc()
        logger.error(f"Erro ao pesquisar infrações: {error_detail}")
        logger.error(f"Stack trace: {stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erro ao pesquisar infrações",
                "error": error_detail,
                "type": type(e).__name__,
                "query": query
            }
        )

@router.get("/{codigo}", response_model=InfracaoResponse)
def obter_infracao(codigo: str, db: Session = Depends(get_db)):
    """
    Retorna uma infração específica pelo código.
    
    - **codigo**: Código da infração
    """
    try:
        logger.info(f"Buscando infração com código: '{codigo}'")
        
        # Validar o código
        if not codigo or len(codigo.strip()) < 3:
            logger.warning(f"Código inválido: '{codigo}'")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Código de infração inválido: {codigo}. O código deve ter pelo menos 3 caracteres."
            )
        
        # Usar SQL direto em vez de ORM para evitar problemas com tipos de dados
        # Usar parâmetros para evitar injeção de SQL
        consulta_sql = "SELECT * FROM bdbautos WHERE \"Código de Infração\" = :codigo LIMIT 1"
        logger.debug(f"Executando consulta SQL: {consulta_sql}")
        
        result = db.execute(text(consulta_sql), {"codigo": codigo})
        
        # Obter os nomes das colunas
        colunas = result.keys()
        
        # Processar o resultado
        infracao = None
        for row in result:
            try:
                # Criar objeto Infracao
                infracao = Infracao()
                
                # Verificar se row é um dicionário ou uma tupla
                if hasattr(row, 'items'):  # É um dicionário ou objeto semelhante
                    infracao.codigo = row["Código de Infração"]
                    infracao.descricao = row["Infração"]
                    infracao.responsavel = row["Responsável"]
                    infracao.valor_multa = row["Valor da Multa"]
                    infracao.orgao_autuador = row["Órgão Autuador"]
                    infracao.artigos_ctb = row["Artigos do CTB"]
                    infracao.pontos = row["pontos"]
                    infracao.gravidade = row["gravidade"]
                else:  # É uma tupla ou lista
                    # Criar um dicionário mapeando nomes de colunas para valores
                    row_dict = {}
                    for i, col in enumerate(colunas):
                        col_name = str(col)  # Garantir que o nome da coluna seja uma string
                        if hasattr(col, 'name'):
                            col_name = col.name
                        if i < len(row):
                            row_dict[col_name] = row[i]
                    
                    logger.debug(f"Row dict: {row_dict}")
                    
                    infracao.codigo = row_dict.get("Código de Infração", "")
                    infracao.descricao = row_dict.get("Infração", "")
                    infracao.responsavel = row_dict.get("Responsável", "")
                    infracao.valor_multa = row_dict.get("Valor da Multa", 0.0)
                    infracao.orgao_autuador = row_dict.get("Órgão Autuador", "")
                    infracao.artigos_ctb = row_dict.get("Artigos do CTB", "")
                    infracao.pontos = row_dict.get("pontos", 0)
                    infracao.gravidade = row_dict.get("gravidade", "")
                
                # Encontramos a primeira infração, podemos sair do loop
                break
            except Exception as e:
                logger.error(f"Erro ao processar resultado: {e}")
                logger.error(f"Detalhes da linha: {row}")
                # Continuar com a próxima linha
        
        if not infracao:
            logger.warning(f"Infração com código '{codigo}' não encontrada")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Infração com código {codigo} não encontrada"
            )
        
        logger.info(f"Infração com código '{codigo}' encontrada")
        return infracao
    except HTTPException:
        raise
    except Exception as e:
        error_detail = str(e)
        stack_trace = traceback.format_exc()
        logger.error(f"Erro ao obter infração com código '{codigo}': {error_detail}")
        logger.error(f"Stack trace: {stack_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": f"Erro ao obter infração com código {codigo}",
                "error": error_detail,
                "type": type(e).__name__
            }
        ) 