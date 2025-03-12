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
    Pesquisa infrações por código ou descrição com busca altamente tolerante a erros.
    Projetado para uso em condições de campo por agentes de trânsito.
    """
    # Limpar e normalizar o termo de busca
    if not query or query.strip() == "":
        # Se a busca estiver vazia, mostrar os primeiros resultados
        return _buscar_todos(db, limit, skip)
    
    query = query.strip().lower()
    query = query.replace("-", "").replace(".", "").replace(",", "")  # Remover separadores comuns
    
    try:
        # Executar diagnóstico primeiro para verificar a conexão com o banco
        diagnostico = diagnostico_banco(db)
        logger.info(f"Conexão com banco OK. Encontrados {len(diagnostico)} registros de exemplo")
        
        # 1. Mapeamento abrangente de termos e sinônimos comuns em trânsito
        termos_comuns = {
            "estacionar": ["estacionar", "estacionamento", "parado", "parada", "estacionado", "estacionou", "parou"],
            "velocidade": ["velocidade", "excesso", "rapido", "rapida", "veloz", "veloc", "acelerado", "ve loc"],
            "celular": ["celular", "telefone", "aparelho", "whatsapp", "mensagem", "celul", "fone", "smartphone"],
            "cinto": ["cinto", "seguranca", "seguranc", "cinto de seguranca", "c seguranca"],
            "alcool": ["alcool", "embriaguez", "bebida", "alcoolizado", "bebida", "embriagado", "bebeu", "etilico"],
            "semaforo": ["semaforo", "sinal", "vermelho", "farol", "sinaleira", "pare", "sinal fechado"],
            "parar": ["parar", "parada", "parou", "freou", "freado", "detenção", "retencao"],
            "ultrapassagem": ["ultrapassagem", "ultrapas", "ultrapa", "ultrapassa", "ultrapasso", "ultrapassou"],
            "contramao": ["contramao", "contra-mao", "sentido", "mao contraria", "direcao", "contra mao"],
            "capacete": ["capacete", "moto", "capac", "motocicleta", "motoqueiro", "motociclista", "motoboy"],
            "faixa": ["faixa", "pedestre", "pedestres", "pista", "faixa de pedestre", "travessia"]
        }
        
        # 2. Verificar se o termo se parece com um código numérico
        # Extrair todos os dígitos para busca numérica parcial
        apenas_numeros = ''.join(c for c in query if c.isdigit())
        
        # 3. Preparar múltiplos termos para busca
        termos_para_busca = []
        
        # Adicionar o termo original e variações diretas
        termos_para_busca.append(query)
        
        # Verificar termos comuns para sinônimos e variações
        for termo_comum, variantes in termos_comuns.items():
            # Checar semelhança com cada variante para tolerar erros ortográficos
            for variante in variantes:
                # Usar comparação simples primeiro (mais rápido)
                if variante in query or query in variante:
                    if termo_comum not in termos_para_busca:
                        termos_para_busca.append(termo_comum)
                        logger.info(f"Termo '{query}' mapeado para termo comum '{termo_comum}' (correspondência simples)")
                        break
                # Verificar similaridade para erros ortográficos
                elif len(query) > 3 and len(variante) > 3:  # Aplicar apenas a termos não muito curtos
                    # Calcular similaridade usando lógica simples
                    if query[:3] == variante[:3] or query[-3:] == variante[-3:]:  # Primeiras ou últimas 3 letras iguais
                        if termo_comum not in termos_para_busca:
                            termos_para_busca.append(termo_comum)
                            logger.info(f"Termo '{query}' mapeado para termo comum '{termo_comum}' (prefixo/sufixo)")
                            break
        
        # 4. Busca combinada (numérica + texto) para maior flexibilidade
        todos_resultados = []
        
        # 4.1 Se temos dígitos, realizar busca por código
        if apenas_numeros:
            # Realizar busca por código, aceitando correspondências parciais
            sql_query = """
            SELECT * FROM bdbautos 
            WHERE CAST("Código de Infração" AS TEXT) LIKE :codigo_search
            ORDER BY "Código de Infração" ASC
            LIMIT :limit OFFSET :skip
            """
            
            # Buscar com qualquer parte do código
            codigo_search = f"%{apenas_numeros}%"
            logger.info(f"Executando busca por código parcial: {codigo_search}")
            
            result = db.execute(
                text(sql_query), 
                {"codigo_search": codigo_search, "limit": limit*2, "skip": skip}  # Buscamos mais para permitir mesclagem
            )
            
            # Processar resultados da busca por código
            resultados_codigo = _processar_resultados(result)
            todos_resultados.extend(resultados_codigo)
            logger.info(f"Busca por código encontrou {len(resultados_codigo)} resultados")
        
        # 4.2 Busca por texto para cada termo
        for termo in termos_para_busca:
            sql_query = """
            SELECT * FROM bdbautos 
            WHERE LOWER("Infração") LIKE :texto_search
               OR LOWER("Responsável") LIKE :texto_search
               OR LOWER("Órgão Autuador") LIKE :texto_search
               OR LOWER("Artigos do CTB") LIKE :texto_search
               OR LOWER("gravidade") LIKE :texto_search
            ORDER BY "Código de Infração" ASC
            LIMIT :limit OFFSET :skip
            """
            
            texto_search = f"%{termo.lower()}%"
            logger.info(f"Executando busca por texto: {texto_search}")
            
            result = db.execute(
                text(sql_query), 
                {"texto_search": texto_search, "limit": limit*2, "skip": skip}
            )
            
            resultados_texto = _processar_resultados(result)
            
            # Adicionar apenas resultados ainda não incluídos (evitar duplicatas)
            codigos_existentes = {r.codigo for r in todos_resultados}
            for r in resultados_texto:
                if r.codigo not in codigos_existentes:
                    todos_resultados.append(r)
                    codigos_existentes.add(r.codigo)
            
            logger.info(f"Busca por '{termo}' adicionou {len(resultados_texto) - len(codigos_existentes)} resultados únicos")
        
        # 5. Retornar resultados paginados
        total = len(todos_resultados)
        resultados_paginados = todos_resultados[skip:skip+limit]
        
        # Se encontrou resultados, retornar com mensagem explicativa
        if resultados_paginados:
            if query != termos_para_busca[0] and len(termos_para_busca) > 1:
                mensagem = f"Resultados expandidos para termos relacionados a '{query}'"
            else:
                mensagem = None
                
            return {
                "resultados": resultados_paginados,
                "total": total,
                "mensagem": mensagem,
                "sugestao": None
            }
        
        # 6. Caso não encontre nada, gerar sugestões inteligentes
        # Listar os termos mais comuns no banco para sugestão
        termos_populares = _obter_termos_populares(db)
        
        # Selecionar 3 termos aleatórios das infrações mais comuns
        termos_sugeridos = random.sample(termos_populares, min(3, len(termos_populares)))
        
        sugestao = f"Tente buscar por: {', '.join(termos_sugeridos)} ou um código como 54870"
        logger.info(f"Nenhum resultado encontrado. Sugestão: {sugestao}")
        
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
            "sugestao": "Tente um termo simples como 'Estacionar' ou um código como '54'"
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

def _obter_termos_populares(db: Session, num_termos: int = 5):
    """Obtém os termos mais populares do banco de dados para sugestões"""
    try:
        # Buscar as infrações mais comuns
        sql_query = """
        SELECT "Infração" FROM bdbautos 
        GROUP BY "Infração"
        ORDER BY COUNT(*) DESC
        LIMIT :num_termos
        """
        
        result = db.execute(text(sql_query), {"num_termos": num_termos})
        
        termos = []
        for row in result:
            if row[0]:
                termos.append(row[0])
        
        # Se não encontrou termos, usar alguns padrões
        if not termos:
            termos = ["Estacionar", "Parar", "Velocidade", "Celular", "Cinto"]
        
        return termos
    except Exception as e:
        logger.error(f"Erro ao obter termos populares: {e}")
        return ["Estacionar", "Parar", "Velocidade", "Celular", "Cinto"]