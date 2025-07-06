from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List, Any, Optional, Tuple
import re
from unidecode import unidecode

from app.core.logger import logger

# Sistema de Sinônimos para Busca Inteligente
SINONIMOS_BUSCA = {
    # Infrações de sinal/semáforo
    "furar sinal": ["furar_sinal_especial"],
    "queimar sinal": ["furar_sinal_especial"],
    "passar sinal": ["furar_sinal_especial"],
    "avançar sinal": ["furar_sinal_especial"],
    
    # Infrações relacionadas a álcool (ajustado para termos reais do banco)
    "bafômetro": ["bafometro_especial"],
    "bafometro": ["bafometro_especial"],
    "teste bafômetro": ["bafometro_especial"],
    "teste do bafômetro": ["bafometro_especial"],
    "recusar bafômetro": ["bafometro_especial"],
    "recusar bafometro": ["bafometro_especial"],
    "beber dirigir": ["alcool", "influencia", "teste", "recusar", "submetido", "substancia"],
    "bebida álcool": ["alcool", "influencia", "teste", "recusar", "submetido", "substancia"],
    "embriagado": ["alcool", "influencia", "teste", "recusar", "submetido", "substancia"],
    "alcoolizado": ["alcool", "influencia", "teste", "recusar", "submetido", "substancia"],
    "dirigir bebado": ["alcool", "influencia", "teste", "recusar", "submetido", "substancia"],
    "beber álcool": ["alcool", "influencia", "teste", "recusar", "submetido", "substancia"],
    
    # Infrações de celular
    "usar celular": ["celular"],
    "celular dirigindo": ["celular"],
    "dirigir falando": ["celular"],
    "whatsapp": ["celular"],
    "telefone celular": ["celular"],
    
    # Infrações de estacionamento
    "estacionar errado": ["estacionamento", "parar", "local", "proibido"],
    "parar lugar proibido": ["estacionamento", "parar", "local", "proibido"],
    "área carga": ["estacionamento", "parar", "local", "proibido"],
    "vaga deficiente": ["estacionamento", "parar", "local", "proibido"],
    
    # Infrações de velocidade
    "excesso velocidade": ["velocidade", "limite", "radar", "máxima", "permitida"],
    "muito rápido": ["velocidade", "limite", "radar", "máxima", "permitida"],
    "correr demais": ["velocidade", "limite", "radar", "máxima", "permitida"],
    "radar": ["velocidade", "limite", "radar", "máxima", "permitida"],
    
    # Infrações de documentação
    "carteira vencida": ["habilitação", "documento", "carteira", "vencida", "válida"],
    "documento vencido": ["habilitação", "documento", "carteira", "vencida", "válida"],
    "cnh vencida": ["habilitação", "documento", "carteira", "vencida", "válida"],
    "sem carteira": ["habilitação", "documento", "carteira", "vencida", "válida"],
    "dirigir sem habilitação": ["habilitação", "documento", "carteira", "vencida", "válida"],
    
    # Infrações de cinto de segurança
    "sem cinto": ["cinto", "segurança", "proteção", "individual"],
    "cinto segurança": ["cinto", "segurança", "proteção", "individual"],
    "não usar cinto": ["cinto", "segurança", "proteção", "individual"],
    
    # Infrações de conversão
    "conversão proibida": ["conversão", "retorno", "curva", "manobra"],
    "retorno proibido": ["conversão", "retorno", "curva", "manobra"],
    "curva proibida": ["conversão", "retorno", "curva", "manobra"],
    
    # Infrações de ultrapassagem
    "ultrapassar errado": ["ultrapassagem", "ultrapassar", "faixa", "contramão"],
    "ultrapassagem proibida": ["ultrapassagem", "ultrapassar", "faixa", "contramão"],
    "passar carro": ["ultrapassagem", "ultrapassar", "faixa", "contramão"],
    
    # Infrações de capacete
    "sem capacete": ["capacete", "proteção", "motocicleta", "moto"],
    "capacete": ["capacete", "proteção", "motocicleta", "moto"],
    "não usar capacete": ["capacete", "proteção", "motocicleta", "moto"],
    
    # Infrações de placa
    "placa ilegível": ["placa", "identificação", "número", "caracteres"],
    "placa suja": ["placa", "identificação", "número", "caracteres"],
    "sem placa": ["placa", "identificação", "número", "caracteres"],
    
    # Infrações de farol
    "farol apagado": ["farol", "luz", "iluminação", "aceso"],
    "sem farol": ["farol", "luz", "iluminação", "aceso"],
    "luz apagada": ["farol", "luz", "iluminação", "aceso"],
    
    # Infrações de transporte
    "transporte passageiro": ["transporte", "passageiro", "pessoa", "lotação"],
    "muita gente": ["transporte", "passageiro", "pessoa", "lotação"],
    "excesso passageiro": ["transporte", "passageiro", "pessoa", "lotação"],
    
    # Infrações de rodízio
    "rodízio": ["rodízio", "circulação", "placa", "restrição"],
    "circular rodízio": ["rodízio", "circulação", "placa", "restrição"],
    
    # Infrações de faixa
    "faixa errada": ["faixa", "pista", "circulação", "preferencial"],
    "mudar faixa": ["faixa", "pista", "circulação", "preferencial"],
    "faixa ônibus": ["faixa", "pista", "circulação", "preferencial"],
    
    # Infrações de pedestres
    "atropelamento": ["pedestre", "pessoa", "atravessar", "faixa"],
    "não dar preferência": ["pedestre", "pessoa", "atravessar", "faixa"],
    "pedestre": ["pedestre", "pessoa", "atravessar", "faixa"],
    
    # Infrações de ruído
    "barulho": ["ruído", "som", "perturbação", "poluição"],
    "som alto": ["ruído", "som", "perturbação", "poluição"],
    "poluição sonora": ["ruído", "som", "perturbação", "poluição"],
    
    # Infrações de equipamentos
    "equipamento obrigatório": ["equipamento", "obrigatório", "portátil", "triângulo"],
    "triângulo": ["equipamento", "obrigatório", "portátil", "triângulo"],
    "extintor": ["equipamento", "obrigatório", "portátil", "triângulo"],
    
    # Infrações de peso
    "excesso peso": ["peso", "carga", "limite", "máximo"],
    "muito peso": ["peso", "carga", "limite", "máximo"],
    "sobrepeso": ["peso", "carga", "limite", "máximo"],
}

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
    Ordena por relevância: Gravíssimas primeiro, depois Graves, Médias e Leves.
    
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
        "Valor da multa" as valor_multa,
        "Órgão Autuador" as orgao_autuador,
        "Artigos do CTB" as artigos_ctb,
        "Pontos" as pontos,
        "Gravidade" as gravidade
    FROM bdbautos 
    WHERE {where_clause}
    ORDER BY 
        CASE 
            WHEN "Gravidade" LIKE '%Gravissima%' THEN 1
            WHEN "Gravidade" LIKE '%Grave%' THEN 2 
            WHEN "Gravidade" LIKE '%Media%' THEN 3
            WHEN "Gravidade" LIKE '%Leve%' THEN 4
            ELSE 5
        END,
        "Pontos" DESC,
        "Código de Infração"
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
    
    # Nova validação: verificar se é uma frase (múltiplas palavras)
    query_limpo = query.strip()
    
    # Não aplicar validação para códigos numéricos
    if not query_limpo.replace('-', '').replace(' ', '').isdigit():
        # Dividir por espaços e contar palavras significativas
        palavras = [p.strip() for p in query_limpo.split() if len(p.strip()) >= 2]
        
        # Combinações permitidas (que não devem gerar erro)
        combinacoes_permitidas = [
            # Nomes compostos comuns
            ["cinto", "seguranca"], ["cinto", "segurança"],
            ["telefone", "celular"], ["radio", "comunicador"],
            ["banco", "dados"], ["codigo", "infração"], ["codigo", "infracao"],
            ["capacete", "seguranca"], ["capacete", "segurança"],
            ["faixa", "pedestre"], ["faixa", "pedestres"],
            ["placa", "veiculo"], ["placa", "veículo"],
            ["documento", "veiculo"], ["documento", "veículo"],
            ["habilitacao", "vencida"], ["habilitação", "vencida"],
            ["pneu", "desgastado"], ["pneu", "careca"],
        ]
        
        # Verificar se é uma combinação permitida
        combinacao_permitida = False
        if len(palavras) == 2:
            palavras_lower = [p.lower() for p in palavras]
            for combinacao in combinacoes_permitidas:
                if palavras_lower == [c.lower() for c in combinacao]:
                    combinacao_permitida = True
                    break
        
        # Se tem mais de 2 palavras OU tem 2 palavras que não são uma combinação permitida
        if len(palavras) > 2 or (len(palavras) == 2 and not combinacao_permitida):
            return {
                "resultados": [],
                "total": 0,
                "mensagem": "Para melhores resultados, pesquise por apenas uma palavra ou código. Ex: cinto, bafômetro, velocidade, chinelo, capacete, 60501."
            }
    
    return None

def expandir_termo_busca(termo_original: str) -> List[str]:
    """
    Expande um termo de busca incluindo sinônimos relevantes.
    
    Args:
        termo_original: Termo de busca original do usuário
        
    Returns:
        Lista de termos para busca (incluindo o original e sinônimos)
    """
    termo_normalizado = normalizar_texto(termo_original)
    termos_busca = [termo_original]  # Sempre incluir o termo original
    encontrou_sinonimo_exato = False
    
    # Buscar sinônimos exatos
    for termo_sinonimo, sinonimos in SINONIMOS_BUSCA.items():
        if termo_normalizado == normalizar_texto(termo_sinonimo):
            termos_busca.extend(sinonimos)
            logger.info(f"Sinônimos encontrados para '{termo_original}': {sinonimos}")
            encontrou_sinonimo_exato = True
            break
    
    # Só buscar sinônimos parciais se não encontrou sinônimo exato
    if not encontrou_sinonimo_exato:
        palavras_termo = termo_normalizado.split()
        for palavra in palavras_termo:
            if len(palavra) >= 3:  # Apenas palavras com 3+ caracteres
                for termo_sinonimo, sinonimos in SINONIMOS_BUSCA.items():
                    if palavra in normalizar_texto(termo_sinonimo):
                        termos_busca.extend(sinonimos)
                        logger.info(f"Sinônimos parciais encontrados para '{palavra}': {sinonimos}")
    
    # Tratamento especial para álcool (com e sem acento)
    if "alcool" in termo_normalizado or "álcool" in termo_normalizado:
        termos_busca.extend(["alcool", "influencia", "teste", "recusar", "submetido", "substancia"])
        logger.info(f"Sinônimos de álcool adicionados: ['alcool', 'influencia', 'teste', 'recusar', 'submetido', 'substancia']")
    
    # Remover duplicatas preservando ordem
    termos_unicos = []
    for termo in termos_busca:
        if termo not in termos_unicos:
            termos_unicos.append(termo)
    
    return termos_unicos

def buscar_bafometro_especial(db: Session, limit: int, skip: int) -> Any:
    """
    Busca específica para bafômetro que retorna apenas os códigos específicos de álcool,
    ordenados por relevância (principais primeiro).
    
    Args:
        db: Sessão do banco de dados
        limit: Limite de resultados
        skip: Offset para paginação
        
    Returns:
        Resultado da consulta SQL
    """
    # Query customizada com ORDER BY por prioridade
    sql = f"""
    SELECT 
        "Código de Infração" as codigo,
        "Infração" as descricao,
        "Responsável" as responsavel,
        "Valor da multa" as valor_multa,
        "Órgão Autuador" as orgao_autuador,
        "Artigos do CTB" as artigos_ctb,
        "Pontos" as pontos,
        "Gravidade" as gravidade
    FROM bdbautos 
    WHERE "Código de Infração" IN (:codigo1, :codigo2, :codigo3)
    ORDER BY 
        CASE "Código de Infração"
            WHEN '51691' THEN 1  -- Dirigir sob influência de álcool (PRINCIPAL)
            WHEN '75790' THEN 2  -- Recusar teste bafômetro
            WHEN '51692' THEN 3  -- Dirigir sob influência de outras substâncias
            ELSE 4
        END
    LIMIT :limit OFFSET :skip
    """
    
    params = {
        "codigo1": "51691",  # Dirigir sob a influência de álcool (PRINCIPAL)
        "codigo2": "75790",  # Recusar-se a ser submetido a teste
        "codigo3": "51692",  # Dirigir sob influência de qualquer outra substância
        "limit": limit,
        "skip": skip
    }
    
    return db.execute(text(sql), params)

def buscar_furar_sinal_especial(db: Session, limit: int, skip: int) -> Any:
    """
    Busca específica para furar sinal que retorna apenas infrações de avanço de semáforo,
    ordenadas por relevância (principais primeiro).
    
    Args:
        db: Sessão do banco de dados
        limit: Limite de resultados
        skip: Offset para paginação
        
    Returns:
        Resultado da consulta SQL
    """
    # Query customizada com ORDER BY por prioridade
    sql = f"""
    SELECT 
        "Código de Infração" as codigo,
        "Infração" as descricao,
        "Responsável" as responsavel,
        "Valor da multa" as valor_multa,
        "Órgão Autuador" as orgao_autuador,
        "Artigos do CTB" as artigos_ctb,
        "Pontos" as pontos,
        "Gravidade" as gravidade
    FROM bdbautos 
    WHERE "Código de Infração" IN (:codigo1, :codigo2, :codigo3, :codigo4, :codigo5, :codigo6, :codigo7)
    ORDER BY 
        CASE "Código de Infração"
            WHEN '60501' THEN 1  -- Avançar sinal vermelho (principal)
            WHEN '60502' THEN 2  -- Avançar sinal de parada obrigatória
            WHEN '60503' THEN 3  -- Avançar sinal vermelho eletrônico
            WHEN '59591' THEN 4  -- Ultrapassar contramão junto sinal
            WHEN '60841' THEN 5  -- Ultrapassar fila sinal luminoso
            WHEN '56731' THEN 6  -- Parar sobre faixa pedestre
            WHEN '56732' THEN 7  -- Parar sobre faixa pedestre eletrônico
            ELSE 8
        END
    LIMIT :limit OFFSET :skip
    """
    
    params = {
        "codigo1": "60501",  # Avançar o sinal vermelho do semáforo (PRINCIPAL)
        "codigo2": "60502",  # Avançar o sinal de parada obrigatória (PRINCIPAL)
        "codigo3": "60503",  # Avançar o sinal vermelho do semáforo sob fiscalização eletrônica (PRINCIPAL)
        "codigo4": "59591",  # Ultrapassar pela contramão veículo parado em fila junto sinal luminoso
        "codigo5": "60841",  # Ultrapassar veículos motorizados em fila, parados em razão de sinal luminoso
        "codigo6": "56731",  # Parar sobre faixa de pedestres na mudança de sinal luminoso
        "codigo7": "56732",  # Parar sobre faixa de pedestres na mudança de sinal luminoso (fiscalização eletrônica)
        "limit": limit,
        "skip": skip
    }
    
    return db.execute(text(sql), params)

def buscar_com_sinonimos(db: Session, termos_busca: List[str], limit: int, skip: int) -> Any:
    """
    Executa busca usando múltiplos termos (original + sinônimos).
    
    Args:
        db: Sessão do banco de dados
        termos_busca: Lista de termos para buscar
        limit: Limite de resultados
        skip: Offset para paginação
        
    Returns:
        Resultado da consulta SQL
    """
    # Verificar se é busca especial de bafômetro
    if "bafometro_especial" in termos_busca:
        return buscar_bafometro_especial(db, limit, skip)
    
    # Verificar se é busca especial de furar sinal
    if "furar_sinal_especial" in termos_busca:
        return buscar_furar_sinal_especial(db, limit, skip)
    
    # Construir a cláusula WHERE com OR para todos os termos
    where_clauses = []
    params = {}
    
    for i, termo in enumerate(termos_busca):
        param_name = f"termo_{i}"
        where_clauses.append(f"UPPER(\"Infração\") LIKE UPPER(:{param_name})")
        params[param_name] = f"%{termo}%"
    
    where_clause = " OR ".join(where_clauses)
    
    return executar_consulta_infracoes(db, where_clause, params, limit, skip)

def pesquisar_infracoes(query: str, limit: int = 10, skip: int = 0, db: Session = None) -> Dict[str, Any]:
    try:
        # Guardar o termo de pesquisa original para mensagens
        query_original = query
        
        # Registrar a consulta original para fins de log
        logger.info(f"Executando pesquisa INTELIGENTE com termo original: '{query_original}', limit: {limit}, skip: {skip}")
        
        # VALIDAR QUERY ORIGINAL ANTES DE LIMPÁ-LA
        erro_validacao = validar_consulta(query_original)
        if erro_validacao:
            return erro_validacao
        
        # Remover hífens da consulta para padronização
        query_limpa = query.replace('-', '').replace(' ', '')
        
        # Registrar se houve alteração
        if query_limpa != query_original:
            logger.info(f"Termo de pesquisa normalizado: '{query_original}' -> '{query_limpa}'")
        
        # Normalizar o termo de busca
        query_normalizada = normalizar_texto(query_limpa)
        logger.info(f"Termo normalizado para busca: '{query_normalizada}'")
        
        # Executar consulta apropriada baseada no tipo de pesquisa
        if query_limpa.isdigit():
            # Busca por código (suporta códigos parciais e formatados)
            result = executar_consulta_infracoes(
                db, 
                "CAST(\"Código de Infração\" AS TEXT) LIKE :codigo_parcial",
                {"codigo_parcial": f"%{query_limpa}%"},
                limit,
                skip
            )
            
            # Processar resultados da consulta
            resultados, total = processar_resultados(result)
            
            # Para buscas por código, retornar resultado direto
            if total > 0:
                return {
                    "resultados": resultados,
                    "total": total,
                    "mensagem": None,
                    "metodo_busca": "codigo"
                }
            else:
                return {
                    "resultados": [],
                    "total": 0,
                    "mensagem": f"Nenhuma infração encontrada para o código '{query_original}'. Verifique o número e tente novamente."
                }
        else:
            # BUSCA INTELIGENTE POR TEXTO COM SINÔNIMOS
            
            # 1ª TENTATIVA: Busca com termo original
            logger.info(f"1ª tentativa - Busca com termo original: '{query_original}'")
            result = executar_consulta_infracoes(
                db, 
                "UPPER(\"Infração\") LIKE UPPER(:query_parcial)",
                {"query_parcial": f"%{query_original}%"},
                limit,
                skip
            )
            
            resultados, total = processar_resultados(result)
            
            if total > 0:
                logger.info(f"✅ Encontrou {total} resultados com termo original")
                return {
                    "resultados": resultados,
                    "total": total,
                    "mensagem": None,
                    "metodo_busca": "original"
                }
            
            # 2ª TENTATIVA: Busca com sinônimos se não encontrou nada
            logger.info(f"2ª tentativa - Expandindo busca com sinônimos para: '{query_original}'")
            termos_busca = expandir_termo_busca(query_original)
            
            if len(termos_busca) > 1:  # Se encontrou sinônimos
                logger.info(f"Usando {len(termos_busca)} termos de busca: {termos_busca}")
                result = buscar_com_sinonimos(db, termos_busca, limit, skip)
                resultados, total = processar_resultados(result)
                
                if total > 0:
                    logger.info(f"✅ Encontrou {total} resultados com sinônimos")
                    return {
                        "resultados": resultados,
                        "total": total,
                        "mensagem": f"Encontramos {total} infração(ões) relacionada(s) a '{query_original}' usando busca inteligente.",
                        "metodo_busca": "sinonimos",
                        "termos_usados": termos_busca[1:]  # Excluir termo original
                    }
            
            # 3ª TENTATIVA: Busca por palavras individuais se ainda não encontrou
            logger.info(f"3ª tentativa - Busca por palavras individuais")
            palavras = query_original.split()
            if len(palavras) > 1:
                for palavra in palavras:
                    if len(palavra) >= 3:  # Apenas palavras com 3+ caracteres
                        logger.info(f"Tentando busca com palavra: '{palavra}'")
                        result = executar_consulta_infracoes(
                            db, 
                            "UPPER(\"Infração\") LIKE UPPER(:query_parcial)",
                            {"query_parcial": f"%{palavra}%"},
                            limit,
                            skip
                        )
                        
                        resultados, total = processar_resultados(result)
                        if total > 0:
                            logger.info(f"✅ Encontrou {total} resultados com palavra '{palavra}'")
                            return {
                                "resultados": resultados,
                                "total": total,
                                "mensagem": f"Encontramos {total} infração(ões) relacionada(s) à palavra '{palavra}' da sua busca '{query_original}'.",
                                "metodo_busca": "palavra_parcial",
                                "palavra_encontrada": palavra
                            }
            
            # Se chegou aqui, não encontrou nada
            logger.info(f"❌ Nenhum resultado encontrado para '{query_original}' mesmo com busca inteligente")
            return {
                "resultados": [],
                "total": 0,
                "mensagem": f"Nenhuma infração encontrada para '{query_original}'. Tente termos como: 'sinal', 'velocidade', 'álcool', 'estacionamento', 'documento' ou 'cinto'.",
                "metodo_busca": "nenhum",
                "sugestoes": ["sinal", "velocidade", "álcool", "estacionamento", "documento", "cinto", "capacete", "celular"]
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