from sqlalchemy.orm import Session
from sqlalchemy import text
from rapidfuzz import fuzz, process
from typing import Dict, List, Any
import traceback
import random

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
    Pesquisa infrações por código ou descrição.
    Otimizado para uso por agentes de trânsito em campo.
    """
    # Preparar o termo de busca (limpar e normalizar)
    query_limpa = query.strip()
    if not query_limpa:
        # Se a busca estiver vazia, mostrar os primeiros resultados
        return _buscar_todos(db, limit, skip)
    
    query_limpa = query_limpa.lower()
    query_limpa = query_limpa.replace("-", "").replace(".", "").replace(",", "")
    
    try:
        # Executar diagnóstico primeiro para verificar a conexão com o banco
        diagnostico = diagnostico_banco(db)
        logger.info(f"Diagnóstico do banco: encontrados {len(diagnostico)} registros de exemplo")
        
        # Lista para armazenar todos os resultados
        resultados_combinados = []
        codigos_existentes = set()
        
        # 1. Busca direta por código
        codigo_limpo = ''.join(c for c in query_limpa if c.isdigit())
        if codigo_limpo:
            sql_codigo = """
            SELECT * FROM bdbautos 
            WHERE CAST("Código de Infração" AS TEXT) = :codigo_exato
               OR CAST("Código de Infração" AS TEXT) LIKE :codigo_parcial
            ORDER BY "Código de Infração" ASC
            LIMIT :limit
            """
            
            result_codigo = db.execute(
                text(sql_codigo), 
                {
                    "codigo_exato": codigo_limpo, 
                    "codigo_parcial": f"%{codigo_limpo}%",
                    "limit": limit*2
                }
            )
            
            resultados_codigo = _processar_resultados(result_codigo)
            for resultado in resultados_codigo:
                resultados_combinados.append(resultado)
                codigos_existentes.add(resultado.codigo)
            
            logger.info(f"Busca por código encontrou {len(resultados_codigo)} resultados")
        
        # 2. Busca direta por texto na descrição e outros campos
        sql_texto = """
        SELECT * FROM bdbautos 
        WHERE LOWER("Infração") LIKE LOWER(:texto_search)
           OR LOWER("Responsável") LIKE LOWER(:texto_search)
           OR LOWER("Artigos do CTB") LIKE LOWER(:texto_search)
           OR LOWER("Órgão Autuador") LIKE LOWER(:texto_search)
           OR LOWER("gravidade") LIKE LOWER(:texto_search)
        ORDER BY "Código de Infração" ASC
        LIMIT :limit
        """
        
        result_texto = db.execute(
            text(sql_texto), 
            {"texto_search": f"%{query_limpa}%", "limit": limit*2}
        )
        
        resultados_texto = _processar_resultados(result_texto)
        for resultado in resultados_texto:
            if resultado.codigo not in codigos_existentes:
                resultados_combinados.append(resultado)
                codigos_existentes.add(resultado.codigo)
        
        logger.info(f"Busca por texto encontrou {len(resultados_texto)} resultados novos")
        
        # 3. Busca por palavras individuais se não encontrou resultados ou tem múltiplas palavras
        if len(resultados_combinados) < 2 and ' ' in query_limpa:
            palavras = query_limpa.split()
            for palavra in palavras:
                if len(palavra) >= 3:  # Ignorar palavras muito curtas
                    sql_palavra = """
                    SELECT * FROM bdbautos 
                    WHERE LOWER("Infração") LIKE LOWER(:palavra_search)
                    ORDER BY "Código de Infração" ASC
                    LIMIT :limit
                    """
                    
                    result_palavra = db.execute(
                        text(sql_palavra), 
                        {"palavra_search": f"%{palavra}%", "limit": limit*2}
                    )
                    
                    resultados_palavra = _processar_resultados(result_palavra)
                    for resultado in resultados_palavra:
                        if resultado.codigo not in codigos_existentes:
                            resultados_combinados.append(resultado)
                            codigos_existentes.add(resultado.codigo)
                    
                    logger.info(f"Busca por palavra '{palavra}' encontrou {len(resultados_palavra)} resultados novos")
        
        # 4. Busca especial para termos conhecidos
        termos_especiais = {
            "recusa": ["recusar", "etilometro", "bafometro", "teste", "alcool"],
            "cinto": ["seguranca", "sinto", "cinto de seguranca"],
            "velocidade": ["excesso", "rapido", "velocidade permitida", "velocidade maxima"],
            "celular": ["usar celular", "telefone", "aparelho"],
            "estacionar": ["estacionamento", "parado"],
            "transitar": ["transito", "passagem"],
            "semaforo": ["sinal", "luz vermelha", "vermelho"],
            "habilitacao": ["habilitado", "inabilitado", "carteira", "cnh"],
            "alcoolizado": ["alcool", "bebida", "embriagado", "etilico"]
        }
        
        if len(resultados_combinados) < 2:
            for termo_principal, sinonimos in termos_especiais.items():
                for sinonimo in sinonimos:
                    if sinonimo in query_limpa or query_limpa in sinonimo:
                        # Encontrou um termo especial, fazer busca específica
                        termos_busca = [termo_principal] + sinonimos
                        for termo in termos_busca:
                            sql_especial = """
                            SELECT * FROM bdbautos 
                            WHERE LOWER("Infração") LIKE LOWER(:termo_search)
                            ORDER BY "Código de Infração" ASC
                            LIMIT :limit
                            """
                            
                            result_especial = db.execute(
                                text(sql_especial), 
                                {"termo_search": f"%{termo}%", "limit": limit}
                            )
                            
                            resultados_especial = _processar_resultados(result_especial)
                            for resultado in resultados_especial:
                                if resultado.codigo not in codigos_existentes:
                                    resultados_combinados.append(resultado)
                                    codigos_existentes.add(resultado.codigo)
                            
                            logger.info(f"Busca por termo especial '{termo}' encontrou {len(resultados_especial)} resultados novos")
                        break
        
        # 5. Verificar se temos resultados
        if resultados_combinados:
            # Aplicar paginação
            total = len(resultados_combinados)
            inicio = min(skip, total)
            fim = min(skip + limit, total)
            resultados_paginados = resultados_combinados[inicio:fim]
            
            mensagem = None
            if query != query_limpa:
                mensagem = f"Mostrando resultados para '{query_limpa}'"
            
            return {
                "resultados": resultados_paginados,
                "total": total,
                "mensagem": mensagem,
                "sugestao": None
            }
        
        # 6. Se não encontrou nada, buscar sugestões
        sql_populares = """
        SELECT DISTINCT "Infração" FROM bdbautos 
        LIMIT 5
        """
        
        result_populares = db.execute(text(sql_populares))
        termos_populares = []
        
        for row in result_populares:
            if row[0]:
                termos_populares.append(row[0])
        
        if not termos_populares:
            termos_populares = ["Estacionar", "Parar", "Velocidade", "Recusar teste", "Habilitação"]
        
        # Escolher 3 termos aleatórios
        termos_sugeridos = random.sample(termos_populares, min(3, len(termos_populares)))
        
        sugestao = f"Tente buscar por: {', '.join(termos_sugeridos)} ou um número como 7579"
        logger.info(f"Nenhum resultado encontrado. Sugerindo: {sugestao}")
        
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
            "sugestao": "Tente uma palavra como 'recusa' ou 'estacionar', ou um código como '7579'"
        }

def _processar_resultados(result):
    """Processa os resultados de uma consulta SQL em objetos Infracao"""
    resultados = []
    try:
        # Obter as colunas
        colunas = result.keys()
        
        # Processar cada linha
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
                
                # Criar objeto Infracao com tratamento de tipos
                infracao = Infracao(
                    codigo=str(row_dict.get("Código de Infração", "")),
                    descricao=str(row_dict.get("Infração", "")),
                    responsavel=str(row_dict.get("Responsável", "")),
                    valor_multa=float(str(row_dict.get("Valor da Multa", "0.0")).replace(",", ".")),
                    orgao_autuador=str(row_dict.get("Órgão Autuador", "")),
                    artigos_ctb=str(row_dict.get("Artigos do CTB", "")),
                    pontos=int(float(str(row_dict.get("pontos", "0")).replace(",", "."))),
                    gravidade=str(row_dict.get("gravidade", ""))
                )
                resultados.append(infracao)
            except Exception as e:
                logger.error(f"Erro ao processar linha: {e}")
                logger.error(f"Detalhes da linha: {row}")
    except Exception as e:
        logger.error(f"Erro ao processar resultados: {e}")
    
    return resultados

def _buscar_todos(db: Session, limit: int = 10, skip: int = 0):
    """Retorna os primeiros resultados quando a busca está vazia"""
    try:
        sql_query = """
        SELECT * FROM bdbautos 
        ORDER BY "Código de Infração" ASC
        LIMIT :limit OFFSET :skip
        """
        
        result = db.execute(text(sql_query), {"limit": limit, "skip": skip})
        resultados = _processar_resultados(result)
        
        # Contar total
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
            "mensagem": f"Erro: {str(e)}",
            "sugestao": None
        }