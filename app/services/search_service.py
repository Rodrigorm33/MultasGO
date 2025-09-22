from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, List, Any, Optional, Tuple
import re
from unidecode import unidecode

from app.core.logger import logger
from app.core.cache_manager import cache_manager, smart_cache
from app.core.spell_corrector import spell_corrector, corrigir_termo_busca
from app.core.suggestion_engine import suggestion_engine


def normalizar_para_busca(texto: str) -> str:
    """
    Normaliza texto para busca insensível a acentos.
    Remove acentos, converte para minúsculas e remove espaços extras.
    """
    if not texto:
        return ""

    # Usar unidecode para remover acentos
    texto_normalizado = unidecode(texto.strip().lower())
    return texto_normalizado

# RapidFuzz como fallback opcional (para não quebrar se ainda estiver instalado)
try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
    logger.info("RapidFuzz disponível como fallback")
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logger.info("RapidFuzz não disponível - usando corretor nativo")

# SymSpell como fallback (importação condicional)
try:
    from symspellpy import SymSpell, Verbosity
    SYMSPELL_AVAILABLE = True
    logger.info("SymSpell disponível para fallback de busca")
except ImportError:
    SYMSPELL_AVAILABLE = False
    logger.info("SymSpell não disponível - usando corretor nativo")

# Sistema de Sinônimos para Busca Inteligente (EXPANDIDO com análise de dados)
SINONIMOS_BUSCA = {
    # === MELHORIAS BASEADAS NA ANÁLISE DE DADOS ===
    
    # Veículos (palavra mais frequente: 204 ocorrências)
    "carro": ["veiculo", "automovel", "auto", "viatura"],
    "veiculo": ["carro", "automovel", "auto", "viatura"],
    "automovel": ["veiculo", "carro", "auto", "viatura"],
    "auto": ["veiculo", "carro", "automovel", "viatura"],
    "viatura": ["veiculo", "carro", "automovel", "auto"],
    
    # Motocicletas (17 ocorrências identificadas)
    "moto": ["motocicleta", "motoneta", "ciclomotor", "bike"],
    "motoca": ["motocicleta", "motoneta", "ciclomotor"],
    "bike": ["motocicleta", "motoneta", "ciclomotor", "moto"],
    "motocicleta": ["moto", "motoca", "motoneta", "ciclomotor"],
    "motoneta": ["motocicleta", "moto", "motoca", "ciclomotor"],
    "ciclomotor": ["motocicleta", "moto", "motoneta"],
    
    # Condutores (18 ocorrências)
    "motorista": ["condutor", "piloto", "guia"],
    "piloto": ["condutor", "motorista", "guia"],
    "guia": ["condutor", "motorista", "piloto"],
    "condutor": ["motorista", "piloto", "guia"],
    
    # Estacionamento (36 ocorrências)
    "parar": ["estacionar", "deixar"],
    "deixar": ["estacionar", "parar"],
    "estacionar": ["parar", "deixar"],
    "estacionamento": ["parar", "deixar", "estacionar"],
    
    # Velocidade (23 ocorrências identificadas)
    "rapidez": ["velocidade"],
    "rapido": ["velocidade", "rapidez"],
    "correr": ["velocidade", "rapidez"],
    "velocidade": ["rapidez", "rapido", "correr", "limite", "radar"],
    "radar": ["velocidade", "limite"],
    "limite": ["velocidade", "radar"],
    
    # Segurança (30 ocorrências)
    "seguranca": ["protecao", "equipamento", "cinto", "capacete"],
    "protecao": ["seguranca", "equipamento", "cinto", "capacete"],
    
    # Documentos
    "carteira": ["habilitacao", "documento", "cnh"],
    "cnh": ["habilitacao", "documento", "carteira"],
    "habilitacao": ["carteira", "documento", "cnh"],
    "documento": ["carteira", "habilitacao", "cnh"],
    
    # Equipamentos obrigatórios
    "equipamento": ["obrigatorio", "triângulo", "extintor"],
    "obrigatorio": ["equipamento", "necessario", "exigido"],
    "necessario": ["obrigatorio", "equipamento", "exigido"],
    "exigido": ["obrigatorio", "equipamento", "necessario"],
    
    # Infrações identificadas na análise
    "multa": ["infracao", "auto"],
    "infracao": ["multa", "auto"],
    "auto": ["multa", "infracao"],
    
    # Bicicletas
    "bicicleta": ["bike", "ciclovia"],
    "ciclovia": ["bicicleta", "bike"],
    
    # === SINÔNIMOS ORIGINAIS MANTIDOS ===
    
    # Infrações de sinal/semáforo
    "furar sinal": ["furar_sinal_especial"],
    "queimar sinal": ["furar_sinal_especial"],
    "passar sinal": ["furar_sinal_especial"],
    "avançar sinal": ["furar_sinal_especial"],
    
    # Infrações relacionadas a álcool (ajustado para termos reais do banco)
    # MELHORADO: Mapeamento direto para retornar mesmos resultados que "alcool"
    "etilometro": ["alcool", "influencia", "teste", "recusar", "submetido"],
    "etilômetro": ["alcool", "influencia", "teste", "recusar", "submetido"],
    "bafometro": ["alcool", "influencia", "teste", "recusar", "submetido"],
    "bafômetro": ["alcool", "influencia", "teste", "recusar", "submetido"],
    "bebida": ["alcool", "influencia", "teste", "recusar", "submetido"],
    "bebida alcoolica": ["alcool", "influencia", "teste", "recusar", "submetido"],
    
    # Sinônimos originais mantidos  
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
    
    # ==== NOVOS SINÔNIMOS DE ALTA PRIORIDADE ====
    # Baseados na análise do banco de dados MultasGO
    
    # Grupo TELEFONE/CELULAR (alta prioridade)
    "celular": ["telefone", "aparelho", "dispositivo"],
    "aparelho": ["telefone", "celular", "dispositivo"],
    "smartphone": ["telefone", "celular", "aparelho"],
    
    # Grupo MOTOCICLETA/MOTO (alta prioridade)
    "moto": ["motocicleta", "ciclomotor", "motoneta"],
    "ciclomotor": ["motocicleta", "moto", "motoneta"],
    "motoneta": ["motocicleta", "moto", "ciclomotor"],
    "bike": ["motocicleta", "moto"],
    
    # Grupo CONDUTOR/MOTORISTA (alta prioridade)
    "motorista": ["condutor", "piloto", "guia"],
    "piloto": ["condutor", "motorista", "guia"],
    "guia": ["condutor", "motorista", "piloto"],
    
    # Grupo ESTACIONAR/PARAR (alta prioridade)
    "estacionar": ["parar", "deixar", "imobilizar"],
    "imobilizar": ["parar", "estacionar", "deixar"],
    "abandonar": ["deixar", "parar", "estacionar"],
    
    # Grupo VELOCIDADE/RAPIDEZ (alta prioridade)
    "rapidez": ["velocidade", "pressa", "limite"],
    "pressa": ["velocidade", "rapidez"],
    "limite": ["velocidade", "maxima", "permitida"],
    
    # Grupo HABILITAÇÃO/CARTEIRA (solicitado pelo usuário)
    "carteira": ["habilitacao", "licenca", "documento"],
    "licenca": ["habilitacao", "carteira", "documento"],
    "permissao": ["habilitacao", "licenca", "autorizacao"],
    
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

# Cache otimizado usando SmartCache
def limpar_cache_palavras():
    """Limpa o cache de palavras do banco após modificações nos dados"""
    try:
        search_cache = cache_manager.get_cache("search")
        if search_cache:
            search_cache.clear()

        # Limpar cache de função também
        if hasattr(extrair_palavras_banco, "_cache"):
            del extrair_palavras_banco._cache

        logger.info("Cache de palavras do banco limpo após modificação de dados")
    except Exception as e:
        logger.warning(f"Erro ao limpar cache: {e}")

def normalizar_texto(texto: str) -> str:
    """
    Normaliza o texto removendo acentos e caracteres especiais.
    MELHORADO: Melhor tratamento de acentos e busca parcial.
    """
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
    params: Any, 
    limit: int = 10, 
    skip: int = 0,
    order_by_priority: bool = False,
    search_term: Optional[str] = None
) -> Any:
    """
    Executa consulta SQL com WHERE clause customizada e ORDER BY inteligente.
    """
    
    # Construir ORDER BY baseado na prioridade
    if order_by_priority and search_term:
        # Normalizar o termo de busca para comparação
        search_term_clean = search_term.lower().strip()
        
        # ORDER BY com prioridade para palavras exatas
        order_by_clause = f"""
        ORDER BY 
            CASE 
                -- PRIORIDADE MÁXIMA: Palavra exata isolada (espaços ou início/fim)
                WHEN UPPER("Infração") LIKE UPPER('% {search_term_clean} %') 
                  OR UPPER("Infração") LIKE UPPER('{search_term_clean} %') 
                  OR UPPER("Infração") LIKE UPPER('% {search_term_clean}') 
                  OR UPPER("Infração") = UPPER('{search_term_clean}') THEN 1
                  
                -- PRIORIDADE ALTA: Começa com o termo
                WHEN UPPER("Infração") LIKE UPPER('{search_term_clean}%') THEN 2
                
                -- PRIORIDADE MÉDIA: Contém o termo no meio
                WHEN UPPER("Infração") LIKE UPPER('%{search_term_clean}%') THEN 3
                
                -- PRIORIDADE BAIXA: Outros casos
                ELSE 4
            END,
            
            -- Ordem secundária por gravidade
            CASE 
                WHEN "Gravidade" LIKE '%Gravissima%' THEN 1
                WHEN "Gravidade" LIKE '%Grave%' THEN 2 
                WHEN "Gravidade" LIKE '%Media%' THEN 3
                WHEN "Gravidade" LIKE '%Leve%' THEN 4
                ELSE 5
            END,
            
            -- Ordem terciária por pontos (maior para menor)
            "Pontos" DESC,
            
            -- Ordem final por código
            "Código de Infração"
        """
    else:
        # ORDER BY padrão sem prioridade
        order_by_clause = """
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
        """
    
    # Construir SQL completo
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
    {order_by_clause}
    LIMIT {limit} OFFSET {skip}
    """
    
    return db.execute(text(sql), params)

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
                "mensagem": "Use apenas 1 palavra ou código para pesquisar. Exemplos: cinto, bafômetro, velocidade, 60501"
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

def extrair_palavras_banco(db: Session) -> List[str]:
    """
    Extrai todas as palavras únicas do banco de dados para busca fuzzy.
    Cache local para evitar consultas repetidas.
    """
    if not hasattr(extrair_palavras_banco, "_cache"):
        logger.info("Extraindo palavras únicas do banco para cache de busca fuzzy...")
        
        sql = """
        SELECT "Infração" as descricao
        FROM bdbautos 
        """
        
        result = db.execute(text(sql))
        todas_infracoes = result.fetchall()
        
        # Extrair todas as palavras únicas
        palavras_unicas = set()
        for infracao in todas_infracoes:
            palavras = re.findall(r'\b\w{3,}\b', normalizar_texto(infracao.descricao).lower())
            palavras_unicas.update(palavras)
        
        # Cache das palavras (conversão para lista para corretor)
        extrair_palavras_banco._cache = list(palavras_unicas)
        logger.info(f"Cache criado com {len(extrair_palavras_banco._cache)} palavras únicas")
    
    return extrair_palavras_banco._cache

# Instância global do SymSpell (lazy loading)
_symspell_instance = None

def inicializar_symspell(db: Session) -> Optional[SymSpell]:
    """
    Inicializa e treina SymSpell com palavras do banco (fallback).
    Só é chamado quando RapidFuzz falha completamente.
    """
    global _symspell_instance
    
    if not SYMSPELL_AVAILABLE:
        return None
    
    if _symspell_instance is not None:
        return _symspell_instance
    
    try:
        logger.info("Inicializando SymSpell como fallback...")
        
        # Criar instância SymSpell
        sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
        
        # Obter palavras do banco
        palavras_banco = extrair_palavras_banco(db)
        
        # Treinar SymSpell com palavras do banco
        for palavra in palavras_banco:
            if len(palavra) >= 3:  # Só palavras significativas
                sym_spell.create_dictionary_entry(palavra, 1)
        
        # Cache da instância
        _symspell_instance = sym_spell
        
        logger.info(f"SymSpell inicializado com {len(palavras_banco)} palavras como fallback")
        return _symspell_instance
        
    except Exception as e:
        logger.error(f"Erro ao inicializar SymSpell: {e}")
        return None

def busca_symspell_fallback(termo_original: str, db: Session) -> List[str]:
    """
    FALLBACK: Busca com SymSpell quando RapidFuzz falha completamente.
    Último recurso para correção ortográfica avançada.
    
    Args:
        termo_original: Termo que não foi encontrado por RapidFuzz
        db: Sessão do banco de dados
        
    Returns:
        List[str]: Lista de termos corrigidos pelo SymSpell
    """
    if not SYMSPELL_AVAILABLE:
        logger.info("SymSpell não disponível para fallback")
        return []
    
    # Inicializar SymSpell se necessário
    sym_spell = inicializar_symspell(db)
    if sym_spell is None:
        return []
    
    try:
        termo_norm = normalizar_texto(termo_original).lower()
        logger.info(f"🔄 FALLBACK SymSpell ativado para: '{termo_norm}'")
        
        # Buscar sugestões com SymSpell
        suggestions = sym_spell.lookup(
            termo_norm, 
            Verbosity.CLOSEST,  # Só as melhores sugestões
            max_edit_distance=2,
            transfer_casing=False
        )
        
        # Extrair termos das sugestões
        termos_corrigidos = []
        for suggestion in suggestions[:5]:  # Máximo 5 sugestões
            termo_corrigido = suggestion.term
            if termo_corrigido != termo_norm:  # Não incluir termo original
                termos_corrigidos.append(termo_corrigido)
        
        if termos_corrigidos:
            logger.info(f"[OK] SymSpell encontrou {len(termos_corrigidos)} correções: {termos_corrigidos}")
        else:
            logger.info(f"[ERRO] SymSpell não encontrou correções para '{termo_norm}'")
        
        return termos_corrigidos
        
    except Exception as e:
        logger.error(f"Erro na busca SymSpell: {e}")
        return []

def busca_fuzzy_melhorada(termo_original: str, db: Session, score_minimo: int = 75) -> List[str]:
    """
    Implementa busca fuzzy avançada usando corretor nativo com filtro de prefixos.

    Args:
        termo_original: Termo que o usuário digitou
        db: Sessão do banco de dados
        score_minimo: Score mínimo para considerar match (0-100)

    Returns:
        List[str]: Lista de termos relacionados encontrados
    """
    if not termo_original or len(termo_original) < 3:
        return []

    termo_norm = normalizar_texto(termo_original).lower()
    logger.info(f"Iniciando busca fuzzy melhorada para: '{termo_norm}'")

    # Obter palavras do banco
    palavras_banco = extrair_palavras_banco(db)

    # 1º FILTRO: Palavras que começam com o termo (PREFIXO)
    palavras_prefixo = [p for p in palavras_banco if p.startswith(termo_norm)]

    if palavras_prefixo:
        logger.info(f"[OK] Encontradas {len(palavras_prefixo)} palavras com prefixo '{termo_norm}': {palavras_prefixo[:5]}")
        return palavras_prefixo[:10]  # Limitar para performance

    # 2º FILTRO: Busca fuzzy com corretor nativo (se não encontrou prefixos)
    logger.info(f"Nenhuma palavra com prefixo encontrada, usando corretor ortográfico...")

    try:
        # Usar o novo corretor ortográfico
        termo_corrigido, confianca, metodo = spell_corrector.corrigir_termo(
            termo_norm,
            palavras_banco,
            limite_similaridade=score_minimo / 100.0
        )

        if confianca > 0.5:  # Se encontrou uma correção decente
            # Buscar sugestões múltiplas
            sugestoes = spell_corrector.buscar_sugestoes(termo_norm, palavras_banco, max_sugestoes=10)
            palavras_encontradas = [sugestao[0] for sugestao in sugestoes if sugestao[1] >= score_minimo / 100.0]

            if palavras_encontradas:
                logger.info(f"[OK] Corretor encontrou {len(palavras_encontradas)} palavras: {palavras_encontradas}")
                return palavras_encontradas

        # Fallback para RapidFuzz se disponível
        if RAPIDFUZZ_AVAILABLE:
            logger.info("Usando RapidFuzz como fallback...")
            palavras_similar = [p for p in palavras_banco if abs(len(p) - len(termo_norm)) <= 3]
            if palavras_similar:
                matches = process.extract(
                    termo_norm,
                    palavras_similar,
                    scorer=fuzz.WRatio,
                    limit=10,
                    score_cutoff=score_minimo
                )
                palavras_encontradas = [match[0] for match in matches]
                if palavras_encontradas:
                    logger.info(f"[OK] RapidFuzz fallback encontrou {len(palavras_encontradas)} palavras")
                    return palavras_encontradas

        logger.info(f"[ERRO] Busca fuzzy não encontrou palavras similares")
        return []

    except Exception as e:
        logger.warning(f"Erro na busca fuzzy: {e}")
        return []

def busca_fuzzy_simples(termo_original: str, texto_alvo: str, tolerancia: int = 1) -> bool:
    """
    Busca fuzzy simples usando corretor nativo.
    """
    if not termo_original or not texto_alvo:
        return False

    termo_norm = normalizar_texto(termo_original)
    texto_norm = normalizar_texto(texto_alvo)

    try:
        # Usar corretor nativo
        import difflib
        similaridade = difflib.SequenceMatcher(None, termo_norm, texto_norm).ratio()
        return similaridade >= 0.75

    except Exception as e:
        logger.debug(f"Erro na busca fuzzy simples: {e}")

        # Fallback para RapidFuzz se disponível
        if RAPIDFUZZ_AVAILABLE:
            try:
                score = fuzz.partial_ratio(termo_norm, texto_norm)
                return score >= 75
            except:
                pass

        # Último fallback: busca básica
        return termo_norm in texto_norm or texto_norm in termo_norm

def buscar_com_fuzzy(db: Session, termo_original: str, limit: int, skip: int) -> Any:
    """
    Executa busca fuzzy AVANÇADA usando corretor nativo com filtro de prefixos.
    
    Args:
        db: Sessão do banco de dados
        termo_original: Termo original digitado pelo usuário
        limit: Limite de resultados
        skip: Offset para paginação
    
    Returns:
        Resultado da consulta ou None se não encontrar
    """
    logger.info(f"[BUSCA] Iniciando busca fuzzy AVANÇADA para: '{termo_original}'")
    
    # Usar nova função de busca fuzzy melhorada
    palavras_relacionadas = busca_fuzzy_melhorada(termo_original, db, score_minimo=70)
    
    if not palavras_relacionadas:
        logger.info(f"[ERRO] Busca fuzzy não encontrou palavras relacionadas")
        return None
    
    # Construir consulta dinâmica com todas as palavras encontradas
    condicoes = []
    params = {}
    
    for i, palavra in enumerate(palavras_relacionadas):
        param_name = f"palavra_{i}"
        condicoes.append(f'UPPER("Infração") LIKE UPPER(:{param_name})')
        params[param_name] = f"%{palavra}%"
    
    where_clause = " OR ".join(condicoes)
    
    logger.info(f"[OK] Buscando por {len(palavras_relacionadas)} palavras relacionadas: {palavras_relacionadas}")
    
    # Executar consulta com ordenação por relevância
    sql = f"""
    SELECT "Código de Infração" as codigo,
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
        LENGTH("Infração") ASC
    LIMIT :limit OFFSET :skip
    """
    
    params.update({"limit": limit, "skip": skip})
    
    result = db.execute(text(sql), params)
    resultados = result.fetchall()
    
    if resultados:
        logger.info(f"[OK] Busca fuzzy AVANÇADA encontrou {len(resultados)} resultados")
        return resultados
    
    logger.info(f"[ERRO] Nenhum resultado encontrado mesmo com palavras relacionadas")
    return None

def pesquisar_infracoes(query: str, limit: int = 10, skip: int = 0, db: Session = None) -> Dict[str, Any]:
    try:
        # Guardar o termo de pesquisa original para mensagens
        query_original = query

        # Registrar a consulta original para fins de log (APENAS NO LOG, NÃO RETORNAR PARA USUÁRIO)
        logger.info(f"[BUSCA] Busca por: '{query_original}'")

        # SISTEMA DE SUGESTÕES: Atualizar palavras do banco (cache local)
        _atualizar_palavras_banco_suggestion_engine(db)

        # SISTEMA DE SUGESTÕES: Verificar ortografia sempre (mesmo com resultados)
        sugestao_ortografica = suggestion_engine.verificar_ortografia(query_original)
        if sugestao_ortografica:
            logger.debug(f"[INFO] Sugestão encontrada: '{query_original}' → '{sugestao_ortografica}'")
        
        # VALIDAR QUERY ORIGINAL - COM VALIDAÇÃO MAIS FLEXÍVEL
        erro_validacao = validar_consulta_flexivel(query_original)
        if erro_validacao:
            return erro_validacao
        
        # NORMALIZAR TERMO DESDE O INÍCIO (resolver problema de acentos)
        query_normalizada = normalizar_texto(query_original)
        
        # Remover hífens da consulta para padronização
        query_limpa = query_original.replace('-', '').replace(' ', '')
        
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
                    "sugestao": sugestao_ortografica
                }
            else:
                return {
                    "resultados": [],
                    "total": 0,
                    "mensagem": f"Nenhuma infração encontrada para o código '{query_original}'. Verifique o número e tente novamente.",
                    "sugestao": sugestao_ortografica
                }
        else:
            # BUSCA SIMPLES SEM COMPLICAÇÕES - GARANTIDA PARA FUNCIONAR
            logger.info(f"Busca simples sem normalizações complexas")
            
            # Busca básica com prioridade rigorosa para palavras exatas
            result = executar_consulta_infracoes(
                db, 
                '''UPPER("Infração") LIKE UPPER(:termo)''',
                {"termo": f"%{query_original}%"},
                limit,
                skip,
                order_by_priority=True,
                search_term=query_original
            )
            
            resultados, total = processar_resultados(result)
            
            if total > 0:
                logger.info(f"[OK] Encontrou {total} resultados")
                return {
                    "resultados": resultados,
                    "total": total,
                    "mensagem": f"Encontrados {total} resultados para '{query_original}'.",
                    "sugestao": sugestao_ortografica
                }
            
            # BUSCA SECUNDÁRIA: busca insensível a acentos
            logger.info(f"Busca inteligente insensível a acentos")

            # Normalizar o termo de busca
            query_normalizado = normalizar_para_busca(query_original)

            # Buscar todos os registros e filtrar em Python para garantir correspondência de acentos
            result_all = db.execute(text('''
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
            ''')).fetchall()

            # Filtrar resultados com correspondência insensível a acentos
            resultados_filtrados = []
            for row in result_all:
                descricao_normalizada = normalizar_para_busca(row.descricao)
                if query_normalizado in descricao_normalizada:
                    resultados_filtrados.append(row)

            # Aplicar limit e skip
            total_filtrados = len(resultados_filtrados)
            resultados_paginados = resultados_filtrados[skip:skip + limit]

            # Processar resultados usando a função existente
            resultados2, _ = processar_resultados(resultados_paginados)
            total2 = total_filtrados
            
            if total2 > 0:
                logger.info(f"[OK] Encontrou {total2} resultados sem acentos")
                return {
                    "resultados": resultados2,
                    "total": total2,
                    "mensagem": f"Encontrados {total2} resultados para '{query_original}'.",
                    "sugestao": sugestao_ortografica
                }
            
            # Nenhum resultado encontrado
            logger.info(f"[ERRO] Nenhum resultado encontrado para '{query_original}'")
            return {
                "resultados": [],
                "total": 0,
                "mensagem": f"Nenhuma infração encontrada para '{query_original}'. Tente termos como: velocidade, cinto, telefone, álcool, sinal.",
                "sugestao": sugestao_ortografica
            }
    
    except Exception as e:
        logger.error(f"[ERRO] Erro na pesquisa: {str(e)}")
        return {
            "resultados": [],
            "total": 0,
            "mensagem": "Erro interno. Tente novamente em alguns instantes.",
            "sugestao": None
        }

def validar_consulta_flexivel(query: str) -> Optional[Dict[str, Any]]:
    """
    Validação ULTRA RESTRITIVA - apenas códigos ou UMA palavra simples.
    """
    # Validação de tamanho mínimo
    if not query or len(query.strip()) < 2:
        return {
            "resultados": [],
            "total": 0,
            "mensagem": "Digite pelo menos 2 caracteres para pesquisar."
        }
    
    # VALIDAÇÃO DE TAMANHO MÁXIMO - 15 caracteres
    if len(query.strip()) > 15:
        return {
            "resultados": [],
            "total": 0,
            "mensagem": "Use apenas 1 palavra ou código para pesquisar. Exemplos: cinto, bafômetro, velocidade, 60501"
        }
    
    # VALIDAÇÃO DE CARACTERES ESPECIAIS ESTRANHOS
    import re
    if re.search(r'[^a-zA-Z0-9áàãâäéêëíîïóôõöúûüçñ\s-]', query):
        return {
            "resultados": [],
            "total": 0,
            "mensagem": "Use apenas 1 palavra ou código para pesquisar. Exemplos: cinto, bafômetro, velocidade, 60501"
        }
    
    # Verificação de abuso/segurança
    if verificar_abuso(query):
        return {
            "resultados": [],
            "total": 0,
            "mensagem": "Use apenas 1 palavra ou código para pesquisar. Exemplos: cinto, bafômetro, velocidade, 60501"
        }
    
    # VALIDAÇÃO ULTRA RESTRITIVA - apenas códigos ou UMA palavra
    query_limpo = query.strip()
    
    # Se for código numérico, permitir
    if query_limpo.replace('-', '').replace(' ', '').isdigit():
        return None
    
    # Para texto: contar palavras RIGOROSAMENTE (SEM ESPAÇOS MÚLTIPLOS)
    palavras = [p.strip() for p in query_limpo.split() if len(p.strip()) >= 2]
    
    # Se tem MAIS DE 1 palavra, rejeitar SEMPRE
    if len(palavras) > 1:
        return {
            "resultados": [],
            "total": 0,
            "mensagem": "Use apenas 1 palavra ou código para pesquisar. Exemplos: cinto, bafômetro, velocidade, 60501"
        }
    
    # Se tem espaços no meio da palavra (indicando múltiplas palavras mal formatadas)
    if ' ' in query_limpo and not query_limpo.replace('-', '').replace(' ', '').isdigit():
        return {
            "resultados": [],
            "total": 0,
            "mensagem": "Use apenas 1 palavra ou código para pesquisar. Exemplos: cinto, bafômetro, velocidade, 60501"
        }
    
    return None
def listar_infracoes_paginado(limit: int = 10, skip: int = 0, db: Session = None) -> Dict[str, Any]:
    """
    Lista todas as infrações com paginação simples.
    Função simplificada que executa query direta.
    """
    try:
        # Query simples para listar todas as infrações ordenadas por código
        sql_query = """
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
        ORDER BY "Código de Infração" ASC
        LIMIT :limit OFFSET :skip
        """

        # Executar query principal diretamente
        resultado = db.execute(text(sql_query), {"limit": limit, "skip": skip})
        rows = resultado.fetchall()

        # Converter resultados para lista de dicionários
        resultados = []
        for row in rows:
            # Função auxiliar para converter valores numéricos com segurança
            def safe_int(value, default=0):
                if not value:
                    return default
                try:
                    # Remover espaços e verificar se é numérico
                    clean_value = str(value).strip()
                    if clean_value.isdigit():
                        return int(clean_value)
                    else:
                        return default
                except (ValueError, TypeError):
                    return default

            def safe_float(value, default=0.0):
                if not value:
                    return default
                try:
                    clean_value = str(value).strip()
                    return float(clean_value)
                except (ValueError, TypeError):
                    return default

            resultados.append({
                "codigo": row.codigo or "",
                "descricao": row.descricao or "",
                "responsavel": row.responsavel or "",
                "valor_multa": safe_float(row.valor_multa),
                "orgao_autuador": row.orgao_autuador or "",
                "artigos_ctb": row.artigos_ctb or "",
                "pontos": safe_int(row.pontos),
                "gravidade": row.gravidade or ""
            })

        # Query para contar total
        count_query = "SELECT COUNT(*) as total FROM bdbautos"
        count_result = db.execute(text(count_query))
        total = count_result.scalar() or 0

        mensagem = None
        if not resultados:
            mensagem = "Nenhuma infração encontrada"

        return {
            "resultados": resultados,
            "total": total,
            "mensagem": mensagem
        }

    except Exception as e:
        logger.error(f"Erro ao listar infrações: {str(e)}")
        return {
            "resultados": [],
            "total": 0,
            "mensagem": "Erro ao carregar infrações"
        }

def listar_infracoes_com_filtros(limit: int = 10, skip: int = 0, filtros: Dict[str, Any] = None, db: Session = None) -> Dict[str, Any]:
    """
    Lista infrações com filtros aplicados.
    Função simples e funcional para o explorador.
    """
    try:
        if filtros is None:
            filtros = {}

        # Construir WHERE clause baseado nos filtros
        where_conditions = []
        params = {}

        # Filtro por gravidade
        if filtros.get("gravidade"):
            where_conditions.append("\"Gravidade\" LIKE :gravidade")
            params["gravidade"] = f"%{filtros['gravidade']}%"

        # Filtro por responsável
        if filtros.get("responsavel"):
            where_conditions.append("\"Responsável\" LIKE :responsavel")
            params["responsavel"] = f"%{filtros['responsavel']}%"

        # Filtro por órgão autuador
        if filtros.get("orgao"):
            where_conditions.append("\"Órgão Autuador\" LIKE :orgao")
            params["orgao"] = f"%{filtros['orgao']}%"

        # Filtro por busca textual na descrição
        if filtros.get("busca"):
            where_conditions.append("\"Infração\" LIKE :busca")
            params["busca"] = f"%{filtros['busca']}%"

        # Filtros por pontos
        if filtros.get("pontos_min") is not None:
            where_conditions.append("CAST(\"Pontos\" AS INTEGER) >= :pontos_min")
            params["pontos_min"] = filtros["pontos_min"]

        if filtros.get("pontos_max") is not None:
            where_conditions.append("CAST(\"Pontos\" AS INTEGER) <= :pontos_max")
            params["pontos_max"] = filtros["pontos_max"]


        # Montar WHERE clause
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"


        # Definir ordenação baseada na presença de filtros
        if where_conditions:
            # Com filtros: ordenar por código (comportamento atual)
            order_clause = 'ORDER BY "Código de Infração" ASC'
        else:
            # Sem filtros: ordenar por gravidade (mais gravosa para menos gravosa)
            order_clause = '''ORDER BY
                CASE "Gravidade"
                    WHEN 'Gravissima3X' THEN 1
                    WHEN 'Gravissima2X' THEN 2
                    WHEN 'Gravissima' THEN 3
                    WHEN 'Grave' THEN 4
                    WHEN 'Media' THEN 5
                    WHEN 'Leve' THEN 6
                    WHEN 'Nao ha' THEN 6
                    ELSE 7
                END ASC,
                "Código de Infração" ASC'''

        # Query principal com filtros
        sql_query = f"""
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
        {order_clause}
        LIMIT :limit OFFSET :skip
        """

        # Adicionar parâmetros de paginação
        params["limit"] = limit
        params["skip"] = skip


        # Executar query principal
        resultado = db.execute(text(sql_query), params)
        rows = resultado.fetchall()

        # Converter resultados usando as funções seguras
        resultados = []
        for row in rows:
            def safe_int(value, default=0):
                if not value:
                    return default
                try:
                    clean_value = str(value).strip()
                    if clean_value.isdigit():
                        return int(clean_value)
                    else:
                        return default
                except (ValueError, TypeError):
                    return default

            def safe_float(value, default=0.0):
                if not value:
                    return default
                try:
                    clean_value = str(value).strip()
                    return float(clean_value)
                except (ValueError, TypeError):
                    return default

            resultados.append({
                "codigo": row.codigo or "",
                "descricao": row.descricao or "",
                "responsavel": row.responsavel or "",
                "valor_multa": safe_float(row.valor_multa),
                "orgao_autuador": row.orgao_autuador or "",
                "artigos_ctb": row.artigos_ctb or "",
                "pontos": safe_int(row.pontos),
                "gravidade": row.gravidade or ""
            })

        # Query para contar total com os mesmos filtros
        count_query = f"""
        SELECT COUNT(*) as total
        FROM bdbautos
        WHERE {where_clause}
        """

        count_result = db.execute(text(count_query), {k: v for k, v in params.items() if k not in ["limit", "skip"]})
        total = count_result.scalar() or 0

        mensagem = None
        if not resultados and where_conditions:
            mensagem = "Nenhuma infração encontrada com os filtros aplicados"
        elif not resultados:
            mensagem = "Nenhuma infração encontrada"

        return {
            "resultados": resultados,
            "total": total,
            "mensagem": mensagem,
            "filtros_aplicados": [k for k, v in filtros.items() if v is not None]
        }

    except Exception as e:
        logger.error(f"Erro ao listar infrações com filtros: {str(e)}")
        return {
            "resultados": [],
            "total": 0,
            "mensagem": "Erro ao carregar infrações com filtros"
        }


# Cache local para palavras do banco (evitar consultas repetidas)
_cache_palavras_banco = None
_cache_timestamp = 0


@smart_cache(cache_name="data", ttl=1800)  # Cache por 30 minutos
def _atualizar_palavras_banco_suggestion_engine(db: Session):
    """
    Atualiza as palavras do banco no suggestion engine.
    Usa cache para evitar consultas desnecessárias.
    """
    global _cache_palavras_banco, _cache_timestamp
    import time

    # Verificar se o cache ainda é válido (30 minutos)
    if _cache_palavras_banco and (time.time() - _cache_timestamp) < 1800:
        return

    try:
        # Buscar todas as infrações do banco
        result = db.execute(text('SELECT "Infração" FROM bdbautos')).fetchall()

        # Extrair palavras únicas das descrições
        palavras_unicas = set()
        for row in result:
            if row[0]:  # Se a infração não for None
                # Dividir em palavras e normalizar
                palavras = re.findall(r'\b\w+\b', row[0].lower())
                for palavra in palavras:
                    if len(palavra) >= 3:  # Apenas palavras com 3+ caracteres
                        palavras_unicas.add(palavra)

        # Adicionar palavras comuns de trânsito manualmente
        palavras_transito = {
            'velocidade', 'alcool', 'celular', 'transito', 'pelicula', 'insulfilm',
            'motocicleta', 'estacionar', 'farol', 'capacete', 'documento', 'condutor',
            'passageiro', 'cinto', 'seguranca', 'ultrapassagem', 'proibido', 'infracao',
            'habilitacao', 'conversao', 'circulacao', 'veiculo'
        }
        palavras_unicas.update(palavras_transito)

        # Atualizar o suggestion engine
        suggestion_engine.atualizar_palavras_banco(palavras_unicas)

        # Atualizar cache
        _cache_palavras_banco = palavras_unicas
        _cache_timestamp = time.time()

        logger.debug(f"Palavras do banco atualizadas no suggestion engine: {len(palavras_unicas)} termos")

    except Exception as e:
        logger.error(f"Erro ao atualizar palavras do banco no suggestion engine: {e}")
        # Em caso de erro, usar um conjunto mínimo de palavras
        palavras_minimas = {
            'velocidade', 'alcool', 'celular', 'transito', 'pelicula', 'insulfilm',
            'motocicleta', 'estacionar', 'farol', 'capacete'
        }
        suggestion_engine.atualizar_palavras_banco(palavras_minimas)
