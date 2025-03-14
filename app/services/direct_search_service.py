import psycopg2
import os
import re
from app.core.logger import logger
from typing import Dict, List, Any

def conectar_banco():
    """Estabelece conexão direta com o banco de dados"""
    try:
        DATABASE_URL = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco de dados: {str(e)}")
        raise

def pesquisar_infracoes(query: str, limit: int = 10, skip: int = 0) -> Dict[str, Any]:
    """
    Pesquisa infrações no banco de dados usando conexão direta com psycopg2
    
    Args:
        query (str): Termo de busca (código ou descrição)
        limit (int): Número máximo de resultados
        skip (int): Número de resultados para pular (paginação)
        
    Returns:
        Dict com resultados da pesquisa
    """
    logger.info(f"Pesquisando por '{query}' (limit={limit}, skip={skip})")
    
    try:
        # Validação básica
        if not query or len(query.strip()) < 2:
            return {
                "resultados": [],
                "total": 0,
                "mensagem": "O termo de pesquisa deve ter pelo menos 2 caracteres",
                "sugestao": None
            }
        
        # Conectar ao banco
        conn = conectar_banco()
        cursor = conn.cursor()
        
        # Diagnóstico do banco de dados para depuração
        cursor.execute("SELECT * FROM bdbautos LIMIT 10")
        colunas_diagnostico = [desc[0] for desc in cursor.description]
        registros_diagnostico = cursor.fetchall()
        
        logger.info(f"Diagnóstico de banco - colunas: {colunas_diagnostico}")
        
        # Converter os primeiros registros para dicionários para depuração
        registros_dict = []
        for row in registros_diagnostico:
            row_dict = {}
            for i, col in enumerate(colunas_diagnostico):
                row_dict[col] = row[i]
            registros_dict.append(row_dict)
        
        logger.info(f"Diagnóstico de banco - primeiros registros: {registros_dict}")
        logger.info(f"Diagnóstico do banco: encontrados {len(registros_diagnostico)} registros de exemplo")
        
        # Verificar se o termo é um código numérico
        is_codigo = bool(re.match(r'^\d+', query.strip()))
        
        # Resultados da busca
        resultados = []
        
        # Primeiro, buscar por correspondência exata para códigos
        if is_codigo:
            try:
                logger.info(f"Buscando por código exato: {query}")
                cursor.execute("""
                    SELECT * FROM bdbautos 
                    WHERE "Código de Infração"::text = %s 
                    LIMIT %s OFFSET %s
                """, [query.strip(), limit, skip])
                resultados = cursor.fetchall()
            except Exception as e:
                logger.error(f"Erro ao buscar código exato: {str(e)}")
                # Continuar com outras estratégias de busca
            
            # Se não encontrou resultados exatos, buscar por correspondência parcial
            if not resultados:
                try:
                    logger.info(f"Buscando por código parcial: {query}")
                    cursor.execute("""
                        SELECT * FROM bdbautos 
                        WHERE "Código de Infração"::text LIKE %s 
                        LIMIT %s OFFSET %s
                    """, [f"%{query.strip()}%", limit, skip])
                    resultados = cursor.fetchall()
                except Exception as e:
                    logger.error(f"Erro ao buscar código parcial: {str(e)}")
                    # Continuar com outras estratégias de busca
        
        # Se ainda não encontrou resultados ou não é um código, buscar por texto
        if not resultados or not is_codigo:
            try:
                # Buscar em múltiplos campos por texto
                logger.info(f"Buscando por texto: {query}")
                cursor.execute("""
                    SELECT * FROM bdbautos 
                    WHERE "Infração" ILIKE %s 
                    OR "Artigos do CTB" ILIKE %s
                    OR "Responsável" ILIKE %s
                    LIMIT %s OFFSET %s
                """, [f"%{query.strip()}%", f"%{query.strip()}%", f"%{query.strip()}%", limit, skip])
                resultados_texto = cursor.fetchall()
                
                # Adicionar resultados de texto apenas se já não temos resultados suficientes
                if len(resultados) < limit:
                    # Filtrar para não duplicar resultados
                    if resultados:
                        codigos_existentes = {str(row[0]) for row in resultados}  # Convertendo para string para segurança
                        resultados_texto = [row for row in resultados_texto if str(row[0]) not in codigos_existentes]
                    
                    # Adicionar resultados de texto até atingir o limite
                    resultados.extend(resultados_texto[:limit - len(resultados)])
            except Exception as e:
                logger.error(f"Erro ao buscar texto: {str(e)}")
        
        # Obter nomes das colunas para todos os resultados
        colunas = colunas_diagnostico  # Usar as colunas já obtidas no diagnóstico
        
        # Formatar dados para retorno
        dados = []
        for row in resultados:
            item = {}
            for i, col in enumerate(colunas):
                if i < len(row) and row[i] is not None:
                    item[col] = str(row[i])
                else:
                    item[col] = None
            dados.append(item)
        
        # Verificar se encontrou resultados
        sugestao = None
        if not dados:
            try:
                # Buscar sugestões baseadas em infrações existentes
                # Correção: Usando TABLESAMPLE em vez de ORDER BY random()
                cursor.execute("""
                    SELECT "Infração", "Código de Infração" 
                    FROM bdbautos TABLESAMPLE BERNOULLI(10)
                    LIMIT 3
                """)
                sugestoes = cursor.fetchall()
                if sugestoes:
                    exemplos = ", ".join([s[0] for s in sugestoes if s[0]])
                    codigo_exemplo = sugestoes[0][1] if sugestoes[0][1] else "7579"
                    sugestao = f"Tente buscar por: {exemplos} ou um número como {codigo_exemplo}"
            except Exception as e:
                logger.error(f"Erro ao obter sugestões: {str(e)}")
                # Fallback para sugestões fixas se o método TABLESAMPLE falhar
                sugestao = "Tente buscar por: Estacionar, Parar na faixa, Fazer ou deixar ou um número como 54870"
        
        conn.close()
        logger.info(f"Pesquisa por '{query}' concluída. Total de resultados: {len(dados)}")
        
        resposta = {
            "resultados": dados,
            "total": len(dados)
        }
        
        if sugestao:
            resposta["sugestao"] = sugestao
            logger.info(f"Sugestão para '{query}': {sugestao}")
            
        return resposta
        
    except Exception as e:
        logger.error(f"Erro na pesquisa por '{query}': {str(e)}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        
        # Resposta de erro com sugestões fixas
        return {
            "resultados": [],
            "total": 0,
            "erro": str(e),
            "mensagem": "Ocorreu um erro ao processar sua pesquisa.",
            "sugestao": "Tente buscar por: Estacionar, Parar na faixa ou um número como 54870"
        }