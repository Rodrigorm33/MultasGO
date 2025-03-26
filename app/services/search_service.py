from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List, Any, Optional, Tuple
import re
from unidecode import unidecode

from app.core.logger import logger

def normalizar_texto(texto: str) -> str:
    """Normaliza o texto removendo acentos e caracteres especiais."""
    if not texto:
        return ""
    texto = texto.lower()
    texto = unidecode(texto)
    texto = re.sub(r'[^a-z0-9\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def verificar_abuso(query: str) -> bool:
    """
    Verifica se a consulta parece ser abusiva/maliciosa.
    
    Args:
        query: Termo de pesquisa a ser verificado
        
    Returns:
        bool: True se a consulta parecer abusiva, False caso contrário
    """
    # Verificar tamanho da consulta
    if len(query) > 100:
        return True
    
    # Verificar padrões suspeitos
    padroes_suspeitos = [
        r'select\s+|insert\s+|update\s+|delete\s+|drop\s+|alter\s+|union\s+',  # SQL Injection
        r'<script|javascript:|alert\(|onerror=|onclick=|onload=',              # XSS
        r'\.\.\/|\\\.\.|\/etc\/passwd|\/bin\/bash|cmd\.exe',                  # Path Traversal
    ]
    
    for padrao in padroes_suspeitos:
        if re.search(padrao, query, re.IGNORECASE):
            return True
    
    return False

def executar_consulta_infracoes(
    db: Session, 
    where_clause: str, 
    params: Dict[str, Any], 
    limit: int = 10, 
    skip: int = 0
) -> Any:
    """
    Função base para executar consultas de infrações com colunas padronizadas.
    
    Args:
        db: Sessão do banco de dados
        where_clause: Cláusula WHERE da consulta SQL (sem a palavra "WHERE")
        params: Parâmetros para a consulta SQL
        limit: Limite de resultados
        skip: Número de resultados para pular (offset)
        
    Returns:
        Resultado da execução da consulta SQL
    """
    sql = f"""
    SELECT 
        "Código de Infração" as codigo,
        "Infração" as descricao,
        "Responsável" as responsavel,
        "Valor da Multa" as valor_multa,
        "Órgão Autuador" as orgao_autuador,
        "Artigos do CTB" as artigos_ctb,
        pontos,
        gravidade
    FROM bdbautos 
    WHERE {where_clause}
    ORDER BY "Código de Infração"
    LIMIT :limit OFFSET :skip
    """
    
    query_params = {**params, "limit": limit, "skip": skip}
    return db.execute(text(sql), query_params)

def processar_resultados(result: Any) -> Tuple[List[Dict[str, Any]], int]:
    """
    Processa os resultados da consulta SQL, formatando e validando os valores.
    
    Args:
        result: Resultado da consulta SQL
        
    Returns:
        Tupla contendo lista de resultados formatados e o total de resultados
    """
    resultados = []
    for row in result:
        # Tratar valor_multa como float
        try:
            valor_multa = float(row.valor_multa) if row.valor_multa else 0.0
        except (ValueError, TypeError):
            valor_multa = 0.0
            
        # Tratar pontos como int
        try:
            pontos = int(float(row.pontos)) if row.pontos else 0
        except (ValueError, TypeError):
            pontos = 0
            
        # Normalizar gravidade
        gravidade = str(row.gravidade).strip() if row.gravidade else "Não informada"
        if gravidade.lower() in ["nan", "none", "null", "undefined"]:
            gravidade = "Não informada"
            
        resultados.append({
            "codigo": str(row.codigo) if row.codigo else "",
            "descricao": str(row.descricao) if row.descricao else "",
            "responsavel": str(row.responsavel) if row.responsavel else "",
            "valor_multa": valor_multa,
            "orgao_autuador": str(row.orgao_autuador) if row.orgao_autuador else "",
            "artigos_ctb": str(row.artigos_ctb) if row.artigos_ctb else "",
            "pontos": pontos,
            "gravidade": gravidade
        })
        
    return resultados, len(resultados)

def validar_consulta(query: str) -> Optional[Dict[str, Any]]:
    """
    Valida o termo de pesquisa antes de executar a consulta.
    Retorna uma mensagem de erro se a consulta for inválida.
    
    Args:
        query: Termo de pesquisa a ser validado
        
    Returns:
        Dicionário com mensagem de erro se inválido, None se válido
    """
    # Validação de tamanho mínimo
    if not query or len(query.strip()) < 2:
        return {
            "resultados": [],
            "total": 0,
            "mensagem": "O termo de pesquisa deve ter pelo menos 2 caracteres"
        }
    
    # Verificação de abuso/segurança
    if verificar_abuso(query):
        return {
            "resultados": [],
            "total": 0,
            "mensagem": "Consulta inválida. Por favor, use termos relacionados a infrações de trânsito."
        }
    
    return None

def pesquisar_infracoes(query: str, limit: int = 10, skip: int = 0, db: Session = None) -> Dict[str, Any]:
    try:
        # Guardar o termo de pesquisa original para mensagens
        query_original = query
        
        # Registrar a consulta original para fins de log
        logger.info(f"Executando pesquisa com termo original: '{query_original}', limit: {limit}, skip: {skip}")
        
        # Remover hífens da consulta para padronização
        query = query.replace('-', '')
        
        # Registrar se houve alteração
        if query != query_original:
            logger.info(f"Termo de pesquisa normalizado: '{query_original}' -> '{query}'")
        
        # Validar consulta (usando o termo sem hífens)
        erro_validacao = validar_consulta(query)
        if erro_validacao:
            return erro_validacao
        
        # Normalizar o termo de busca
        query_normalizada = normalizar_texto(query)
        logger.info(f"Termo normalizado para busca: '{query_normalizada}'")
        
        # Executar consulta apropriada baseada no tipo de pesquisa
        if query.isdigit():
            # Busca por código
            result = executar_consulta_infracoes(
                db, 
                "CAST(\"Código de Infração\" AS TEXT) LIKE :codigo_parcial",
                {"codigo_parcial": f"%{query}%"},
                limit,
                skip
            )
        else:
            # Busca por texto - Abordagem mais simples e direta
            result = executar_consulta_infracoes(
                db, 
                "\"Infração\" ILIKE :query_parcial",
                {"query_parcial": f"%{query}%"},  # Usar o termo original, não o normalizado
                limit,
                skip
            )
        
        # Processar resultados da consulta
        resultados, total = processar_resultados(result)
        
        # Retornar resposta formatada - Usando o termo original na mensagem
        if total > 0:
            return {
                "resultados": resultados,
                "total": total,
                "mensagem": None
            }
        else:
            return {
                "resultados": [],
                "total": 0,
                "mensagem": f"Nenhuma infração encontrada para '{query_original}'. Verifique o termo e tente novamente."
            }
            
    except Exception as e:
        # Log detalhado do erro para depuração
        logger.error(f"Erro ao pesquisar infrações: {str(e)}")
        logger.error(f"Detalhe do erro: {type(e).__name__}")
        
        # Retornar mensagem amigável para o usuário
        return {
            "resultados": [],
            "total": 0,
            "mensagem": "Ocorreu um erro ao processar sua pesquisa."
        }