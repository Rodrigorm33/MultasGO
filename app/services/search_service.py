from sqlalchemy.orm import Session
from sqlalchemy import text, select
from rapidfuzz import fuzz, process
from typing import Dict, List, Any, Set, Optional
import traceback
import random
import re
import unicodedata
from unidecode import unidecode

from app.core.config import settings
from app.core.logger import logger
from app.models.infracao import Infracao, InfracaoBase as BDBAutos

def normalizar_texto(texto: str) -> str:
    """
    Normaliza um texto para busca, removendo acentos, convertendo para minúsculas,
    removendo hífens de códigos e tratando caracteres especiais.
    
    Args:
        texto: Texto a ser normalizado
        
    Returns:
        Texto normalizado
    """
    if not texto:
        return ""
    
    # Converter para string caso não seja
    texto = str(texto)
    
    # Converter para minúsculas
    texto = texto.lower()
    
    # Remover acentos
    texto = unidecode(texto)
    
    # Se o texto parece ser um código (contém números e hífen), remover o hífen
    if any(c.isdigit() for c in texto) and '-' in texto:
        texto = texto.replace('-', '')
    else:
        # Para textos normais, substituir hífen por espaço para melhorar a busca
        texto = texto.replace('-', ' ')
    
    # Substituir caracteres especiais por espaço
    texto = re.sub(r'[^\w\s]', ' ', texto)
    
    # Substituir múltiplos espaços por um único
    texto = re.sub(r'\s+', ' ', texto)
    
    # Remover espaços no início e fim
    texto = texto.strip()
    
    return texto

def sugerir_correcao_ortografica(query: str, db: Session) -> Optional[str]:
    """
    Sugere correções para o termo de busca quando nenhum resultado é encontrado.
    Utiliza várias técnicas:
    1. Remoção de acentos
    2. Correção de erros comuns
    3. Sugestão de termos similares
    4. Sugestões baseadas em categorias
    """
    try:
        # 1. Tentar buscar sem acentos
        query_sem_acentos = normalizar_texto(query)
        if query_sem_acentos != query:
            sql_sem_acentos = """
            SELECT * FROM bdbautos 
            WHERE unaccent(LOWER("Infração")) LIKE unaccent(LOWER(:query))
            LIMIT 1
            """
            
            result = db.execute(text(sql_sem_acentos), {"query": f"%{query}%"})
            if list(result):
                return f"Você quis dizer '{query_sem_acentos}'?"
        
        # 2. Verificar erros comuns de digitação
        erros_comuns = {
            "transito": "trânsito",
            "codigo": "código",
            "infração": "infração",
            "veiculo": "veículo",
            "alcool": "álcool",
            "velocidade maxima": "velocidade máxima",
            "nao": "não",
            "permissao": "permissão",
            "documentacao": "documentação",
            "atencao": "atenção",
            "direcao": "direção",
            "conducao": "condução",
            "obrigatorio": "obrigatório",
            "passageiro": "passageiro",
            "seguranca": "segurança",
            "transporte": "transporte",
            "minima": "mínima",
            "transitar": "transitar",
            "proibido": "proibido",
            "area": "área",
            "xinelo": "chinelo",
            "xapeu": "chapéu",
            "xave": "chave",
            "xegar": "chegar"
        }
        
        query_lower = query.lower()
        for erro, correcao in erros_comuns.items():
            if erro in query_lower:
                # Verificar se a correção retorna resultados
                sql_correcao = """
                SELECT * FROM bdbautos 
                WHERE LOWER("Infração") LIKE LOWER(:correcao)
                LIMIT 1
                """
                
                result = db.execute(
                    text(sql_correcao), 
                    {"correcao": f"%{correcao}%"}
                )
                
                if list(result):
                    return f"Você quis dizer '{query.replace(erro, correcao)}'?"
                else:
                    # Se não encontrou resultados com a correção, sugerir mesmo assim
                    return f"Você quis dizer '{query.replace(erro, correcao)}'?"
        
        # 3. Buscar termos relacionados
        categorias = {
            "velocidade": ["excesso", "velocidade", "máxima", "permitida", "radar"],
            "documentos": ["habilitação", "cnh", "documento", "licenciamento"],
            "alcool": ["álcool", "embriaguez", "bafômetro", "etilômetro"],
            "estacionamento": ["estacionar", "vaga", "proibido"],
            "equipamentos": ["cinto", "capacete", "cadeirinha", "segurança"],
            "sinalizacao": ["sinal", "semáforo", "placa", "faixa"],
            "conducao": ["direção", "conduzir", "manobra", "perigosa"],
            "pedestres": ["pedestre", "faixa", "calçada", "travessia"]
        }
        
        query_tokens = set(query_lower.split())
        for categoria, termos in categorias.items():
            if any(token in query_tokens for token in termos):
                # Buscar infrações na mesma categoria
                sql_categoria = """
                SELECT * FROM bdbautos 
                WHERE """ + " OR ".join([f"LOWER(\"Infração\") LIKE LOWER(:termo{i})" for i in range(len(termos))])
                
                params = {f"termo{i}": f"%{termo}%" for i, termo in enumerate(termos)}
                result = db.execute(text(sql_categoria), params)
                
                if list(result):
                    outros_termos = [t for t in termos if t not in query_tokens]
                    if outros_termos:
                        return f"Tente pesquisar por '{random.choice(outros_termos)}'"
        
        # 4. Sugestões genéricas
        termos_comuns = ["estacionar", "velocidade", "habilitação", "documentos", "sinal"]
        return f"Tente pesquisar por '{random.choice(termos_comuns)}'"
        
    except Exception as e:
        logger.error(f"Erro ao sugerir correção: {e}")
        return None

def diagnostico_banco(db: Session):
    """
    Função de diagnóstico para listar os primeiros 10 registros do banco de dados.
    Útil para verificar a conexão e estrutura dos dados.
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

def calcular_relevancia(resultado, query: str, pontuacoes_relevancia: dict) -> float:
    """
    Calcula a pontuação de relevância para um resultado específico.
    
    Args:
        resultado: Objeto Infracao
        query: Termo de busca original
        pontuacoes_relevancia: Dicionário com pontuações base por código
        
    Returns:
        Pontuação de relevância (float)
    """
    # Constantes de peso para diferentes tipos de match
    PESO_EXATO = 100
    PESO_INICIO = 80
    PESO_PARCIAL = 60
    PESO_FUZZY = 40
    
    # Constantes de peso para diferentes campos
    PESO_CODIGO = 100
    PESO_DESCRICAO = 80
    PESO_ARTIGOS = 60
    PESO_RESPONSAVEL = 40
    PESO_OUTROS = 20
    
    # Inicializar relevância com a pontuação base do código
    relevancia = pontuacoes_relevancia.get(resultado.codigo, 0)
    
    # Normalizar query e textos para comparação
    query_norm = normalizar_texto(query)
    query_termos = set(query_norm.split())
    
    # 1. Matches no código
    codigo_norm = normalizar_texto(resultado.codigo)
    if query_norm == codigo_norm:
        relevancia += PESO_EXATO
    elif codigo_norm.startswith(query_norm):
        relevancia += PESO_INICIO
    elif query_norm in codigo_norm:
        relevancia += PESO_PARCIAL
    
    # 2. Matches na descrição
    descricao_norm = normalizar_texto(resultado.descricao)
    if query_norm == descricao_norm:
        relevancia += PESO_EXATO * 0.8  # Peso reduzido para descrição
    elif descricao_norm.startswith(query_norm):
        relevancia += PESO_INICIO * 0.8
    elif query_norm in descricao_norm:
        relevancia += PESO_PARCIAL * 0.8
    
    # 3. Matches em outros campos
    for campo, valor, peso in [
        ("artigos_ctb", resultado.artigos_ctb, PESO_ARTIGOS),
        ("responsavel", resultado.responsavel, PESO_RESPONSAVEL),
        ("orgao_autuador", resultado.orgao_autuador, PESO_OUTROS),
        ("gravidade", resultado.gravidade, PESO_OUTROS)
    ]:
        if valor:
            valor_norm = normalizar_texto(str(valor))
            if any(termo in valor_norm for termo in query_termos):
                relevancia += peso * 0.5  # Peso reduzido para campos secundários
    
    # 4. Ajuste final baseado em fatores adicionais
    if hasattr(resultado, 'match_count'):
        relevancia += resultado.match_count * 10
    if hasattr(resultado, 'relevance_score'):
        relevancia += resultado.relevance_score * 5
        
    return relevancia

def pesquisar_infracoes(query: str, limit: int = 10, skip: int = 0, db: Session = None) -> Dict[str, Any]:
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
        
        # Fazer diagnóstico do banco antes da busca
        diagnostico_banco(db)
        
        # Normalizar o termo de busca
        query_normalizada = normalizar_texto(query)
        logger.info(f"Busca original: '{query}', normalizada: '{query_normalizada}'")
        
        # Se o termo normalizado parece ser um código (contém apenas números)
        if query_normalizada.isdigit():
            # Buscar por código exato e variações
            codigo = query_normalizada
            
            logger.info(f"Buscando código exato e parcial: {codigo}")
            
            sql = """
            SELECT * FROM bdbautos 
            WHERE CAST("Código de Infração" AS TEXT) = :codigo_exato
               OR REPLACE(CAST("Código de Infração" AS TEXT), '-', '') = :codigo_sem_hifen
               OR CAST("Código de Infração" AS TEXT) LIKE :codigo_parcial
               OR REPLACE(CAST("Código de Infração" AS TEXT), '-', '') LIKE :codigo_parcial
            ORDER BY 
                CASE 
                    WHEN CAST("Código de Infração" AS TEXT) = :codigo_exato THEN 1
                    WHEN REPLACE(CAST("Código de Infração" AS TEXT), '-', '') = :codigo_sem_hifen THEN 2
                    WHEN CAST("Código de Infração" AS TEXT) LIKE :codigo_parcial THEN 3
                    WHEN REPLACE(CAST("Código de Infração" AS TEXT), '-', '') LIKE :codigo_parcial THEN 4
                    ELSE 5
                END
            LIMIT :limit
            """
            
            result = db.execute(text(sql), {
                "codigo_exato": codigo,
                "codigo_sem_hifen": codigo,
                "codigo_parcial": f"%{codigo}%",
                "limit": limit
            })
            
            resultados = _processar_resultados(result)
            total = len(resultados)
            
            logger.info(f"Busca por código encontrou {total} resultados")
            
            if total > 0:
                return {
                    "resultados": resultados[:limit],
                    "total": total,
                    "mensagem": None,
                    "sugestao": None
                }
            
            # Se não encontrou resultados por código, tentar busca por texto
            logger.info("Tentando busca por texto após falha na busca por código")
        
        # Busca por texto (quando não é código ou quando a busca por código falhou)
        sql = """
        SELECT * FROM bdbautos 
        WHERE LOWER("Infração") LIKE LOWER(:texto_search)
           OR LOWER("Responsável") LIKE LOWER(:texto_search)
           OR LOWER("Artigos do CTB") LIKE LOWER(:texto_search)
           OR LOWER("Órgão Autuador") LIKE LOWER(:texto_search)
           OR LOWER("gravidade") LIKE LOWER(:texto_search)
        ORDER BY 
            CASE 
                WHEN LOWER("Infração") LIKE LOWER(:texto_search_exato) THEN 1
                WHEN LOWER("Infração") LIKE LOWER(:texto_search_inicio) THEN 2
                ELSE 3
            END
        LIMIT :limit
        """
        
        result = db.execute(text(sql), {
            "texto_search": f"%{query_normalizada}%",
            "texto_search_exato": query_normalizada,
            "texto_search_inicio": f"{query_normalizada}%",
            "limit": limit
        })
        
        novos_resultados = _processar_resultados(result)
        logger.info(f"Busca por texto encontrou {len(novos_resultados)} resultados novos")
        
        # Combinar resultados (se houver) e retornar
        resultados = (resultados if 'resultados' in locals() else []) + novos_resultados
        total = len(resultados)
        
        if total > 0:
            return {
                "resultados": resultados[:limit],
                "total": total,
                "mensagem": None,
                "sugestao": None
            }
        
        # Se não encontrou resultados, tentar sugerir correções
        sugestao = sugerir_correcao_ortografica(query, db)
        
        # Mensagem amigável baseada no tipo de busca
        if query.replace("-", "").isdigit():
            mensagem = f"Nenhuma infração encontrada com o código '{query}'. Verifique se o código está correto ou tente buscar por descrição."
        else:
            mensagem = f"Nenhuma infração encontrada para '{query}'. Verifique a ortografia ou tente usar termos mais específicos."
        
        return {
            "resultados": [],
            "total": 0,
            "mensagem": mensagem,
            "sugestao": sugestao
        }
        
    except Exception as e:
        logger.error(f"Erro ao pesquisar infrações: {str(e)}")
        logger.error(f"Stack trace: {traceback.format_exc()}")
        return {
            "resultados": [],
            "total": 0,
            "mensagem": "Ocorreu um erro ao processar sua pesquisa.",
            "sugestao": "Tente uma palavra como 'estacionar' ou 'velocidade', ou um código como '7579'"
        }

def _processar_resultados(result):
    """
    Processa os resultados de uma consulta SQL convertendo-os em dicionários com campos normalizados.
    Inclui tratamento de erros e conversão de tipos.
    """
    resultados = []
    try:
        # Obter as colunas
        colunas = result.keys()
        
        # Mapeamento de nomes de colunas do banco para nomes normalizados
        mapeamento_colunas = {
            "Código de Infração": "codigo",
            "Infração": "descricao",
            "Responsável": "responsavel",
            "Valor da Multa": "valor_multa",
            "Órgão Autuador": "orgao_autuador",
            "Artigos do CTB": "artigos_ctb",
            "pontos": "pontos",
            "gravidade": "gravidade"
        }
        
        # Processar cada linha
        for row in result:
            try:
                # Criar um dicionário com nomes normalizados
                row_dict = {}
                for i, col in enumerate(colunas):
                    col_name = str(col)
                    if hasattr(col, 'name'):
                        col_name = col.name
                    
                    # Usar o nome normalizado se existir no mapeamento
                    normalized_name = mapeamento_colunas.get(col_name, col_name.lower())
                    if i < len(row):
                        row_dict[normalized_name] = row[i]
                
                # Tratar valor_multa - garantir que seja float
                try:
                    valor_multa_str = str(row_dict.get("valor_multa", "0.0"))
                    valor_multa_str = valor_multa_str.replace(",", ".")
                    valor_multa_str = ''.join(c for c in valor_multa_str if c.isdigit() or c == '.')
                    valor_multa = float(valor_multa_str)
                except (ValueError, TypeError) as e:
                    valor_multa = 0.0
                    logger.warning(f"Erro ao converter valor da multa: {row_dict.get('valor_multa')} - {str(e)}")
                
                # Tratar pontos - garantir que seja inteiro
                try:
                    pontos_str = str(row_dict.get("pontos", "0"))
                    pontos_str = ''.join(c for c in pontos_str if c.isdigit() or c == '.')
                    pontos = int(float(pontos_str)) if pontos_str else 0
                except (ValueError, TypeError) as e:
                    pontos = 0
                    logger.warning(f"Erro ao converter pontos: {row_dict.get('pontos')} - {str(e)}")
                
                # Tratamento para gravidade - normalizar o texto
                gravidade = str(row_dict.get("gravidade", "")).strip()
                if not gravidade or gravidade.lower() in ["nan", "none", "null", "undefined"]:
                    gravidade = "Não informada"
                
                # Criar dicionário com campos normalizados
                infracao_dict = {
                    "codigo": str(row_dict.get("codigo", "")),
                    "descricao": str(row_dict.get("descricao", "")),
                    "responsavel": str(row_dict.get("responsavel", "")),
                    "valor_multa": valor_multa,
                    "orgao_autuador": str(row_dict.get("orgao_autuador", "")),
                    "artigos_ctb": str(row_dict.get("artigos_ctb", "")),
                    "pontos": pontos,
                    "gravidade": gravidade
                }
                
                resultados.append(infracao_dict)
            except Exception as e:
                logger.error(f"Erro ao processar linha: {e}")
                logger.debug(f"Detalhes da linha: {row}")
                continue
    except Exception as e:
        logger.error(f"Erro ao processar resultados: {e}")
    
    return resultados

def _buscar_todos(db: Session, limit: int = 10, skip: int = 0):
    """
    Retorna os primeiros resultados quando a busca está vazia.
    Inclui paginação e contagem total.
    """
    try:
        sql_query = """
        SELECT * FROM bdbautos 
        ORDER BY "Código de Infração" ASC
        LIMIT :limit OFFSET :skip
        """
        
        result = db.execute(text(sql_query), {"limit": limit, "skip": skip})
        resultados = _processar_resultados(result)
        
        # Contar total de registros para informação de paginação
        count_sql = "SELECT COUNT(*) FROM bdbautos"
        total_result = db.execute(text(count_sql))
        total = 0
        for row in total_result:
            total = row[0]
            break
        
        return {
            "resultados": resultados,
            "total": total,
            "mensagem": "Mostrando os primeiros resultados.",
            "sugestao": None
        }
    except Exception as e:
        logger.error(f"Erro ao buscar todos: {e}")
        return {
            "resultados": [],
            "total": 0,
            "mensagem": f"Erro ao recuperar infrações: {str(e)}",
            "sugestao": "Tente usar o campo de busca para encontrar infrações específicas."
        }
        