from sqlalchemy.orm import Session
from sqlalchemy import or_, func, text
from typing import List, Dict, Any, Tuple, Union
from rapidfuzz import fuzz, process
import re
from app.models.infracao import Infracao
from app.core.config import settings
from app.core.logger import logger

def normalizar_codigo(codigo: str) -> str:
    """
    Normaliza o código da infração removendo hífens e espaços.
    
    Args:
        codigo: Código da infração com ou sem hífen
        
    Returns:
        str: Código normalizado
    """
    # Remover hífens e espaços
    return re.sub(r'[-\s]', '', codigo)

def encontrar_sugestao(db: Session, termo: str) -> str:
    """
    Encontra uma sugestão para um termo de pesquisa que não retornou resultados.
    
    Args:
        db: Sessão do banco de dados
        termo: Termo de pesquisa original
        
    Returns:
        str: Termo sugerido ou None se não houver sugestão
    """
    try:
        logger.info(f"Buscando sugestão para o termo: '{termo}'")
        
        # Normalizar o termo de pesquisa
        termo_normalizado = termo.lower().strip()
        
        # Mapeamento direto para casos comuns
        mapeamento_direto = {
            'xinelo': 'chinelo',
            'chinelo': 'chinelo',
            'sinto': 'cinto',
            'cinto': 'cinto',
            'velucidade': 'velocidade',
            'velocidade': 'velocidade',
            'contranao': 'contramao',
            'contramao': 'contramao'
        }
        
        # Verificar se o termo está no mapeamento direto
        if termo_normalizado in mapeamento_direto:
            sugestao = mapeamento_direto[termo_normalizado]
            # Se a sugestão for igual ao termo, não sugerir
            if sugestao != termo_normalizado:
                logger.info(f"Sugestão direta encontrada para '{termo}': '{sugestao}'")
                return sugestao
            return None
        
        # Obter todas as infrações
        todas_infracoes = db.query(Infracao).all()
        
        # Criar lista de termos para comparação
        termos_comparacao = []
        
        # Adicionar códigos
        for infracao in todas_infracoes:
            termos_comparacao.append(infracao.codigo)
        
        # Adicionar palavras-chave das descrições
        palavras_chave = set()
        for infracao in todas_infracoes:
            # Extrair palavras com mais de 3 caracteres
            palavras = [p.lower() for p in re.findall(r'\b\w{3,}\b', infracao.descricao)]
            palavras_chave.update(palavras)
        
        termos_comparacao.extend(list(palavras_chave))
        
        # Encontrar o termo mais similar usando rapidfuzz
        resultado = process.extractOne(
            termo_normalizado, 
            termos_comparacao,
            scorer=fuzz.token_set_ratio,
            score_cutoff=75
        )
        
        if resultado:
            termo_sugerido, score = resultado
            # Se a sugestão for igual ao termo, não sugerir
            if termo_sugerido != termo_normalizado:
                logger.info(f"Sugestão fuzzy encontrada para '{termo}': '{termo_sugerido}' (score: {score})")
                return termo_sugerido
        
        logger.info(f"Nenhuma sugestão encontrada para '{termo}'")
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar sugestão: {e}")
        return None

def pesquisar_por_codigo(db: Session, codigo: str, limit: int = 10, skip: int = 0) -> List[Infracao]:
    """
    Pesquisa infrações por código exato ou parcial, com suporte a códigos com ou sem hífen.
    
    Args:
        db: Sessão do banco de dados
        codigo: Código da infração (completo ou parcial, com ou sem hífen)
        limit: Número máximo de resultados
        skip: Número de resultados para pular (paginação)
        
    Returns:
        List[Infracao]: Lista de infrações encontradas
    """
    try:
        # Normalizar o código (remover hífens e espaços)
        codigo_normalizado = normalizar_codigo(codigo)
        logger.debug(f"Código normalizado: '{codigo_normalizado}'")
        
        # Usar uma abordagem mais simples para evitar problemas com tipos de dados
        # Buscar todas as infrações e filtrar manualmente
        todas_infracoes = []
        try:
            # Usar uma consulta SQL simples para evitar problemas com tipos de dados
            # Usar text() para evitar problemas de segurança e compatibilidade
            consulta_sql = "SELECT * FROM bdbautos"
            logger.debug(f"Executando consulta SQL: {consulta_sql}")
            
            result = db.execute(text(consulta_sql))
            
            # Obter os nomes das colunas
            colunas = result.keys()
            logger.debug(f"Colunas encontradas: {[col for col in colunas]}")
            
            # Processar os resultados
            for row in result:
                logger.debug(f"Processando linha: {row}")
                logger.debug(f"Tipo da linha: {type(row)}")
                
                try:
                    # Tentar acessar como dicionário
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
                    
                    todas_infracoes.append(infracao)
                except Exception as e:
                    logger.error(f"Erro ao processar resultado: {e}")
                    logger.error(f"Detalhes da linha: {row}")
                    # Continuar com a próxima linha
        except Exception as e:
            logger.error(f"Erro ao buscar todas as infrações: {e}")
            # Fallback para a consulta ORM
            logger.info("Usando fallback para consulta ORM")
            todas_infracoes = db.query(Infracao).all()
        
        # Filtrar manualmente para suportar códigos com ou sem hífen
        resultados = []
        for infracao in todas_infracoes:
            codigo_infracao_normalizado = normalizar_codigo(infracao.codigo)
            
            # Verificar se o código normalizado da consulta está contido no código normalizado da infração
            if codigo_normalizado in codigo_infracao_normalizado:
                resultados.append(infracao)
                
            # Verificar também o formato com hífen (se o código original tiver 5 dígitos)
            elif len(codigo) == 5 and codigo[:4] == infracao.codigo[:4] and codigo[4:] == infracao.codigo[4:]:
                resultados.append(infracao)
                
            # Verificar formato com hífen (se o código original tiver 6 caracteres com hífen)
            elif len(codigo) == 6 and codigo[4] == '-' and codigo[:4] == infracao.codigo[:4] and codigo[5:] == infracao.codigo[4:]:
                resultados.append(infracao)
        
        # Aplicar paginação
        resultados_paginados = resultados[skip:min(skip+limit, len(resultados))]
        
        logger.info(f"Pesquisa por código '{codigo}' (normalizado: '{codigo_normalizado}') retornou {len(resultados_paginados)} resultados")
        return resultados_paginados
    except Exception as e:
        logger.error(f"Erro ao pesquisar por código: {e}")
        raise

def pesquisar_por_descricao_fuzzy(db: Session, descricao: str, limit: int = 10, skip: int = 0) -> List[Dict[str, Any]]:
    """
    Pesquisa infrações por descrição utilizando fuzzy search.
    
    Args:
        db: Sessão do banco de dados
        descricao: Descrição da infração (completa ou parcial)
        limit: Número máximo de resultados
        skip: Número de resultados para pular (paginação)
        
    Returns:
        List[Dict[str, Any]]: Lista de infrações encontradas com score de similaridade
    """
    try:
        # Normalizar a descrição para melhorar a busca
        descricao_normalizada = descricao.lower().strip()
        
        # Substituições comuns para erros de português
        substituicoes = {
            'ç': 'c', 'á': 'a', 'à': 'a', 'â': 'a', 'ã': 'a',
            'é': 'e', 'ê': 'e', 'í': 'i', 'ó': 'o', 'ô': 'o',
            'õ': 'o', 'ú': 'u', 'ü': 'u'
        }
        
        # Aplicar substituições
        for original, substituto in substituicoes.items():
            descricao_normalizada = descricao_normalizada.replace(original, substituto)
        
        # Dividir a consulta em palavras-chave
        palavras_chave = [p for p in descricao_normalizada.split() if len(p) > 2]
        
        # Buscar todas as infrações para aplicar fuzzy search
        todas_infracoes = []
        try:
            # Usar uma consulta SQL simples para evitar problemas com tipos de dados
            # Usar text() para evitar problemas de segurança e compatibilidade
            consulta_sql = "SELECT * FROM bdbautos"
            logger.debug(f"Executando consulta SQL: {consulta_sql}")
            
            result = db.execute(text(consulta_sql))
            
            # Obter os nomes das colunas
            colunas = result.keys()
            logger.debug(f"Colunas encontradas: {[col for col in colunas]}")
            
            # Processar os resultados
            for row in result:
                logger.debug(f"Processando linha: {row}")
                logger.debug(f"Tipo da linha: {type(row)}")
                
                try:
                    # Tentar acessar como dicionário
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
                    
                    todas_infracoes.append(infracao)
                except Exception as e:
                    logger.error(f"Erro ao processar resultado: {e}")
                    logger.error(f"Detalhes da linha: {row}")
                    # Continuar com a próxima linha
        except Exception as e:
            logger.error(f"Erro ao buscar todas as infrações: {e}")
            # Fallback para a consulta ORM
            logger.info("Usando fallback para consulta ORM")
            todas_infracoes = db.query(Infracao).all()
        
        # Aplicar fuzzy search na descrição
        resultados_fuzzy = []
        for infracao in todas_infracoes:
            # Normalizar a descrição da infração
            descricao_infracao_normalizada = infracao.descricao.lower()
            for original, substituto in substituicoes.items():
                descricao_infracao_normalizada = descricao_infracao_normalizada.replace(original, substituto)
            
            # Verificar se pelo menos uma palavra-chave está presente na descrição
            palavras_encontradas = 0
            for palavra in palavras_chave:
                if palavra in descricao_infracao_normalizada:
                    palavras_encontradas += 1
            
            # Se nenhuma palavra-chave foi encontrada e temos mais de uma palavra, pular
            if len(palavras_chave) > 0 and palavras_encontradas == 0:
                continue
                
            # Calcular a similaridade entre a consulta e a descrição (usando diferentes algoritmos)
            score_token_set = fuzz.token_set_ratio(descricao_normalizada, descricao_infracao_normalizada)
            score_token_sort = fuzz.token_sort_ratio(descricao_normalizada, descricao_infracao_normalizada)
            score_partial = fuzz.partial_ratio(descricao_normalizada, descricao_infracao_normalizada)
            
            # Usar o maior score entre os diferentes algoritmos
            score = max(score_token_set, score_token_sort, score_partial)
            
            # Bônus para correspondências exatas de palavras-chave
            if palavras_encontradas > 0:
                # Adicionar bônus proporcional ao número de palavras encontradas
                bonus = min(15, palavras_encontradas * 5)
                score = min(100, score + bonus)
            
            # Adicionar à lista se o score for maior que o limiar
            if score >= settings.FUZZY_SEARCH_THRESHOLD:
                resultados_fuzzy.append({
                    "infracao": infracao,
                    "score": score
                })
        
        # Ordenar por score (maior para menor)
        resultados_fuzzy.sort(key=lambda x: x["score"], reverse=True)
        
        # Aplicar paginação
        resultados_paginados = resultados_fuzzy[skip:skip+limit]
        
        logger.info(f"Pesquisa fuzzy por descrição '{descricao}' retornou {len(resultados_paginados)} resultados")
        return resultados_paginados
    except Exception as e:
        logger.error(f"Erro ao pesquisar por descrição com fuzzy search: {e}")
        raise

def pesquisar_infracoes(db: Session, query: str, limit: int = 10, skip: int = 0) -> Dict[str, Any]:
    """
    Pesquisa infrações por código ou descrição.
    
    Args:
        db: Sessão do banco de dados
        query: Termo de pesquisa (código ou descrição)
        limit: Número máximo de resultados
        skip: Número de resultados para pular (paginação)
        
    Returns:
        Dict[str, Any]: Dicionário com resultados e total
    """
    try:
        logger.info(f"Iniciando pesquisa com termo: '{query}', limit: {limit}, skip: {skip}")
        
        mensagem = None
        sugestao = None
        
        # Verificar se a consulta pode ser um código (contém apenas dígitos, hífens ou espaços)
        if re.match(r'^[\d\-\s]+$', query):
            logger.info(f"Termo '{query}' identificado como possível código de infração")
            
            # Verificar se o formato do código é válido
            codigo_normalizado = normalizar_codigo(query)
            
            # Formatos válidos para códigos de infração no Brasil:
            # - 5 dígitos (ex: 51692)
            # - 4 dígitos + hífen + 1 dígito (ex: 5169-2)
            
            # Verificar se o código tem um formato inválido (mais de um hífen ou formato não reconhecido)
            formato_invalido = False
            if query.count('-') > 1 or (len(codigo_normalizado) != 5 and len(codigo_normalizado) != 6):
                mensagem = "Formato de código inválido. Use o formato XXXXX ou XXXX-X, onde X é um dígito."
                formato_invalido = True
                logger.warning(f"Formato de código inválido: '{query}'")
            
            # Pesquisar por código (com ou sem hífen)
            try:
                resultados_codigo = pesquisar_por_codigo(db, query, limit, skip)
                logger.info(f"Pesquisa por código '{query}' retornou {len(resultados_codigo)} resultados")
                
                # Se encontrou resultados por código, retornar
                if resultados_codigo:
                    # Se encontrou resultados, não mostrar mensagem de erro de formato
                    if formato_invalido and len(resultados_codigo) > 0:
                        mensagem = None
                    
                    return {
                        "resultados": resultados_codigo,
                        "total": len(resultados_codigo),
                        "mensagem": mensagem,
                        "sugestao": sugestao
                    }
            except Exception as e:
                logger.error(f"Erro ao pesquisar por código: {e}")
                # Continuar com a pesquisa por descrição
        
        # Se não encontrou por código ou não é um código, pesquisar por descrição
        logger.info(f"Pesquisando por descrição: '{query}'")
        try:
            resultados_fuzzy = pesquisar_por_descricao_fuzzy(db, query, limit, skip)
            logger.info(f"Pesquisa fuzzy por descrição '{query}' retornou {len(resultados_fuzzy)} resultados")
            
            # Extrair apenas as infrações dos resultados fuzzy
            resultados = [item["infracao"] for item in resultados_fuzzy]
            
            # Se não encontrou resultados, buscar sugestão
            if not resultados:
                logger.info(f"Nenhum resultado encontrado para '{query}'. Buscando sugestão.")
                sugestao = encontrar_sugestao(db, query)
                if sugestao:
                    logger.info(f"Sugestão encontrada para '{query}': '{sugestao}'")
            
            return {
                "resultados": resultados,
                "total": len(resultados),
                "mensagem": mensagem,
                "sugestao": sugestao
            }
        except Exception as e:
            logger.error(f"Erro ao pesquisar por descrição: {e}")
            raise
    except Exception as e:
        logger.error(f"Erro ao pesquisar infrações: {e}")
        raise 