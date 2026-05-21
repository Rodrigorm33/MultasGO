"""
Teste Completo do Sistema de Busca - MultasGO
==============================================
Simula consultas reais de usuarios com erros ortograficos,
prefixos, sinonimos, codigos e buscas compostas.

Testa 3 endpoints:
  1. /api/v1/infracoes/pesquisa?q=...   (busca principal)
  2. /api/v1/infracoes/smart?q=...      (sugestoes + preview)
  3. /api/v1/infracoes/autocomplete?q=... (autocomplete)

USO:
  python teste/teste_busca_completo.py
  python teste/teste_busca_completo.py --url https://seu-dominio.com.br
  python teste/teste_busca_completo.py --verbose
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# ============================================================
# CONFIGURACAO
# ============================================================

BASE_URL = "http://localhost:8080"
API_PREFIX = "/api/v1/infracoes"

TIMEOUT_SECONDS = 10

# Cores ANSI
class C:
    OK = "\033[92m"      # verde
    FAIL = "\033[91m"    # vermelho
    WARN = "\033[93m"    # amarelo
    INFO = "\033[96m"    # ciano
    DIM = "\033[90m"     # cinza
    BOLD = "\033[1m"
    END = "\033[0m"


# ============================================================
# DEFINICAO DOS TESTES
# ============================================================

@dataclass
class TestCase:
    """Um caso de teste individual."""
    query: str
    descricao: str
    categoria: str
    # Expectativas
    espera_resultados: bool = True          # True = deve retornar resultados
    min_resultados: int = 1                 # minimo esperado
    espera_sugestao: Optional[str] = None   # sugestao "voce quis dizer" esperada (substring)
    espera_conter: Optional[str] = None     # texto que DEVE aparecer nos resultados (substring na descricao)
    espera_codigo: Optional[str] = None     # codigo especifico esperado nos resultados
    endpoint: str = "pesquisa"              # pesquisa | smart | autocomplete


# --- CATEGORIA 1: Termos corretos (baseline) ---
TESTES_CORRETOS = [
    TestCase("velocidade", "Termo correto basico", "correto", espera_resultados=True, min_resultados=3),
    TestCase("celular", "Celular - termo frequente", "correto", espera_resultados=True, min_resultados=1),
    TestCase("alcool", "Alcool - sem acento", "correto", espera_resultados=True, min_resultados=1),
    TestCase("estacionar", "Estacionar - verbo", "correto", espera_resultados=True, min_resultados=1),
    TestCase("capacete", "Capacete - equipamento", "correto", espera_resultados=True, min_resultados=1),
    TestCase("habilitacao", "Habilitacao - documento", "correto", espera_resultados=True, min_resultados=1),
    TestCase("farol", "Farol - iluminacao", "correto", espera_resultados=True, min_resultados=1),
    TestCase("cinto", "Cinto de seguranca", "correto", espera_resultados=True, min_resultados=1),
    TestCase("placa", "Placa do veiculo", "correto", espera_resultados=True, min_resultados=1),
    TestCase("ultrapassagem", "Ultrapassagem", "correto", espera_resultados=True, min_resultados=1),
    TestCase("conversao", "Conversao/retorno", "correto", espera_resultados=True, min_resultados=1),
    TestCase("pedestre", "Pedestre/faixa", "correto", espera_resultados=True, min_resultados=1),
    TestCase("motocicleta", "Motocicleta", "correto", espera_resultados=True, min_resultados=1),
    TestCase("documento", "Documento", "correto", espera_resultados=True, min_resultados=1),
]

# --- CATEGORIA 2: Erros ortograficos (o mais critico) ---
TESTES_ERROS_ORTOGRAFICOS = [
    # Velocidade - variantes de erro
    TestCase("velocidate", "Troca de 'd' por 't'", "erro_ortografico", espera_resultados=True),
    TestCase("velocidde", "Letra faltando", "erro_ortografico", espera_resultados=True),
    TestCase("velosidade", "S em vez de C", "erro_ortografico", espera_resultados=True),
    TestCase("velicidade", "I em vez de O", "erro_ortografico", espera_resultados=True),
    TestCase("belocidade", "B em vez de V", "erro_ortografico", espera_resultados=True),
    TestCase("velocidaide", "Letra extra (AI)", "erro_ortografico", espera_resultados=True),
    TestCase("vlocidade", "Letra faltando (E)", "erro_ortografico", espera_resultados=True),
    TestCase("velocidae", "Final errado", "erro_ortografico", espera_resultados=True),

    # Celular - variantes
    TestCase("selular", "S em vez de C", "erro_ortografico", espera_resultados=True),
    TestCase("cellular", "Double L ingles", "erro_ortografico", espera_resultados=True),
    TestCase("cellar", "Sem U", "erro_ortografico", espera_resultados=True),
    TestCase("selelar", "SE em vez de CE", "erro_ortografico", espera_resultados=True),
    TestCase("celulr", "Letra faltando (A)", "erro_ortografico", espera_resultados=True),
    TestCase("celualr", "Letras trocadas (AL->LA)", "erro_ortografico", espera_resultados=True),

    # Alcool - variantes
    TestCase("alcol", "Sem O duplicado", "erro_ortografico", espera_resultados=True),
    TestCase("alchool", "CH em vez de C", "erro_ortografico", espera_resultados=True),
    TestCase("alkool", "K em vez de C", "erro_ortografico", espera_resultados=True),
    TestCase("alcohol", "Ingles", "erro_ortografico", espera_resultados=True),
    TestCase("alcohl", "Letras trocadas", "erro_ortografico", espera_resultados=True),

    # Estacionar - variantes
    TestCase("estacioanr", "Letras trocadas", "erro_ortografico", espera_resultados=True),
    TestCase("estasionar", "S em vez de C", "erro_ortografico", espera_resultados=True),
    TestCase("estaconar", "Sem I", "erro_ortografico", espera_resultados=True),

    # Capacete - variantes
    TestCase("casacete", "SA em vez de PA", "erro_ortografico", espera_resultados=True),
    TestCase("capacette", "Double T", "erro_ortografico", espera_resultados=True),
    TestCase("capassete", "SS em vez de C", "erro_ortografico", espera_resultados=True),

    # Habilitacao - variantes
    TestCase("habilitasao", "S em vez de C", "erro_ortografico", espera_resultados=True),
    TestCase("abilitacao", "Sem H", "erro_ortografico", espera_resultados=True),
    TestCase("habilitaçao", "Com cedilha (C com cedilha)", "erro_ortografico", espera_resultados=True),

    # Documento - variantes
    TestCase("documneto", "Letras trocadas", "erro_ortografico", espera_resultados=True),
    TestCase("documetno", "Letras trocadas (2)", "erro_ortografico", espera_resultados=True),
    TestCase("ducumento", "U em vez de O", "erro_ortografico", espera_resultados=True),

    # Farol - variantes
    TestCase("faroll", "Double L", "erro_ortografico", espera_resultados=True),
    TestCase("pharol", "PH em vez de F", "erro_ortografico", espera_resultados=True),

    # Placa
    TestCase("plaka", "K em vez de CA", "erro_ortografico", espera_resultados=True),
    TestCase("plca", "Sem A", "erro_ortografico", espera_resultados=True),

    # Seguranca
    TestCase("segurnaca", "Letras trocadas", "erro_ortografico", espera_resultados=True),
    TestCase("siguranca", "I em vez de E", "erro_ortografico", espera_resultados=True),
    TestCase("seguransa", "S em vez de C", "erro_ortografico", espera_resultados=True),

    # Ultrapassagem
    TestCase("ultrpassagem", "Sem A", "erro_ortografico", espera_resultados=True),
    TestCase("ultrapassajem", "J em vez de G", "erro_ortografico", espera_resultados=True),

    # Condutor
    TestCase("conditor", "I em vez de U", "erro_ortografico", espera_resultados=True),
    TestCase("codnutor", "Letras trocadas", "erro_ortografico", espera_resultados=True),

    # Proibido
    TestCase("probido", "Sem I", "erro_ortografico", espera_resultados=True),
    TestCase("poibido", "Sem R", "erro_ortografico", espera_resultados=True),
    TestCase("proibdo", "Sem I (2)", "erro_ortografico", espera_resultados=True),

    # Transito
    TestCase("tansito", "Sem R", "erro_ortografico", espera_resultados=True),
    TestCase("trasito", "Sem N", "erro_ortografico", espera_resultados=True),
    TestCase("transitto", "Double T", "erro_ortografico", espera_resultados=True),

    # Motocicleta
    TestCase("motocileta", "Letras trocadas CL->CIL", "erro_ortografico", espera_resultados=True),

    # Passageiro
    TestCase("pasageiro", "Um S so", "erro_ortografico", espera_resultados=True),
    TestCase("pasajeiro", "J em vez de G", "erro_ortografico", espera_resultados=True),

    # Insulfilm
    TestCase("insufilm", "Sem L", "erro_ortografico", espera_resultados=True),
    TestCase("insulfilme", "E extra no final", "erro_ortografico", espera_resultados=True),
    TestCase("insulfime", "Sem L (2)", "erro_ortografico", espera_resultados=True),

    # Infracao
    TestCase("infrasao", "S em vez de C", "erro_ortografico", espera_resultados=True),
]

# --- CATEGORIA 3: Prefixos (digitacao parcial) ---
TESTES_PREFIXOS = [
    TestCase("vel", "Prefixo VEL (velocidade)", "prefixo", espera_resultados=True),
    TestCase("cel", "Prefixo CEL (celular)", "prefixo", espera_resultados=True),
    TestCase("alc", "Prefixo ALC (alcool)", "prefixo", espera_resultados=True),
    TestCase("est", "Prefixo EST (estacionar)", "prefixo", espera_resultados=True),
    TestCase("cap", "Prefixo CAP (capacete)", "prefixo", espera_resultados=True),
    TestCase("hab", "Prefixo HAB (habilitacao)", "prefixo", espera_resultados=True),
    TestCase("far", "Prefixo FAR (farol)", "prefixo", espera_resultados=True),
    TestCase("doc", "Prefixo DOC (documento)", "prefixo", espera_resultados=True),
    TestCase("ult", "Prefixo ULT (ultrapassagem)", "prefixo", espera_resultados=True),
    TestCase("ped", "Prefixo PED (pedestre)", "prefixo", espera_resultados=True),
    TestCase("cin", "Prefixo CIN (cinto)", "prefixo", espera_resultados=True),
    TestCase("conv", "Prefixo CONV (conversao)", "prefixo", espera_resultados=True),
    TestCase("rad", "Prefixo RAD (radar)", "prefixo", espera_resultados=True),
    TestCase("mot", "Prefixo MOT (moto/motocicleta)", "prefixo", espera_resultados=True),
]

# --- CATEGORIA 4: Sinonimos ---
TESTES_SINONIMOS = [
    TestCase("carro", "Sinonimo de veiculo", "sinonimo", espera_resultados=True),
    TestCase("motorista", "Sinonimo de condutor", "sinonimo", espera_resultados=True),
    TestCase("carteira", "Sinonimo de habilitacao/cnh", "sinonimo", espera_resultados=True),
    TestCase("cnh", "CNH = habilitacao", "sinonimo", espera_resultados=True),
    TestCase("radar", "Sinonimo de velocidade", "sinonimo", espera_resultados=True),
    TestCase("moto", "Sinonimo de motocicleta", "sinonimo", espera_resultados=True),
    TestCase("bike", "Sinonimo de motocicleta", "sinonimo", espera_resultados=True),
    TestCase("bebida", "Sinonimo de alcool", "sinonimo", espera_resultados=True),
    TestCase("bafometro", "Sinonimo de alcool/teste", "sinonimo", espera_resultados=True),
    TestCase("barulho", "Sinonimo de ruido", "sinonimo", espera_resultados=True),
    TestCase("rapidez", "Sinonimo de velocidade", "sinonimo", espera_resultados=True),
    TestCase("telefone", "Sinonimo de celular", "sinonimo", espera_resultados=True),
    TestCase("whatsapp", "Sinonimo coloquial celular", "sinonimo", espera_resultados=True),
    TestCase("triangulo", "Equipamento obrigatorio", "sinonimo", espera_resultados=True),
    TestCase("extintor", "Equipamento obrigatorio", "sinonimo", espera_resultados=True),
]

# --- CATEGORIA 5: Buscas compostas (multi-palavra) ---
TESTES_COMPOSTOS = [
    TestCase("excesso velocidade", "Busca composta velocidade", "composto", espera_resultados=True),
    TestCase("furar sinal", "Busca especial sinal", "composto", espera_resultados=True),
    TestCase("sem capacete", "Busca composta capacete", "composto", espera_resultados=True),
    TestCase("sem cinto", "Busca composta cinto", "composto", espera_resultados=True),
    TestCase("carteira vencida", "Busca composta CNH", "composto", espera_resultados=True),
    TestCase("cnh vencida", "Busca composta CNH (2)", "composto", espera_resultados=True),
    TestCase("celular dirigindo", "Uso de celular", "composto", espera_resultados=True),
    TestCase("dirigir bebado", "Alcool ao volante", "composto", espera_resultados=True),
    TestCase("estacionar errado", "Estacionamento proibido", "composto", espera_resultados=True),
    TestCase("ultrapassagem proibida", "Ultrapassagem", "composto", espera_resultados=True),
    TestCase("farol apagado", "Sem farol", "composto", espera_resultados=True),
    TestCase("placa ilegivel", "Placa suja/ilegivel", "composto", espera_resultados=True),
    TestCase("conversao proibida", "Conversao/retorno", "composto", espera_resultados=True),
    TestCase("cinto seguranca", "Cinto de seguranca", "composto", espera_resultados=True),
    TestCase("equipamento obrigatorio", "Equipamentos", "composto", espera_resultados=True),
    TestCase("muito rapido", "Excesso velocidade informal", "composto", espera_resultados=True),
    TestCase("poluicao sonora", "Barulho/som", "composto", espera_resultados=True),
    TestCase("sem placa", "Placa inexistente", "composto", espera_resultados=True),
]

# --- CATEGORIA 6: Busca por codigo ---
TESTES_CODIGOS = [
    TestCase("5169", "Codigo parcial (alcool)", "codigo", espera_resultados=True),
    TestCase("51691", "Codigo completo (alcool)", "codigo", espera_resultados=True, espera_codigo="51691"),
    TestCase("60501", "Codigo furar sinal", "codigo", espera_resultados=True, espera_codigo="60501"),
    TestCase("7455", "Codigo generico 4 digitos", "codigo", espera_resultados=True),
    TestCase("745", "Codigo parcial 3 digitos", "codigo", espera_resultados=True),
]

# --- CATEGORIA 7: Smart endpoint (sugestoes + preview) ---
TESTES_SMART = [
    TestCase("vel", "Smart: prefixo vel", "smart", endpoint="smart", espera_resultados=True),
    TestCase("celular", "Smart: celular completo", "smart", endpoint="smart", espera_resultados=True),
    TestCase("selular", "Smart: erro ortografico no smart", "smart", endpoint="smart", espera_sugestao="celular"),
    TestCase("veloci", "Smart: prefixo longo", "smart", endpoint="smart", espera_resultados=True),
    TestCase("alco", "Smart: prefixo alcool", "smart", endpoint="smart", espera_resultados=True),
    TestCase("baf", "Smart: prefixo bafometro", "smart", endpoint="smart", espera_resultados=True),
    TestCase("51", "Smart: codigo parcial", "smart", endpoint="smart", espera_resultados=True),
    TestCase("furar", "Smart: inicio busca composta", "smart", endpoint="smart", espera_resultados=True),
]

# --- CATEGORIA 8: Autocomplete ---
TESTES_AUTOCOMPLETE = [
    TestCase("vel", "Autocomplete: vel", "autocomplete", endpoint="autocomplete", espera_resultados=True),
    TestCase("cel", "Autocomplete: cel", "autocomplete", endpoint="autocomplete", espera_resultados=True),
    TestCase("est", "Autocomplete: est", "autocomplete", endpoint="autocomplete", espera_resultados=True),
    TestCase("cap", "Autocomplete: cap", "autocomplete", endpoint="autocomplete", espera_resultados=True),
    TestCase("hab", "Autocomplete: hab", "autocomplete", endpoint="autocomplete", espera_resultados=True),
    TestCase("mot", "Autocomplete: mot", "autocomplete", endpoint="autocomplete", espera_resultados=True),
    TestCase("doc", "Autocomplete: doc", "autocomplete", endpoint="autocomplete", espera_resultados=True),
    TestCase("pla", "Autocomplete: pla", "autocomplete", endpoint="autocomplete", espera_resultados=True),
    TestCase("far", "Autocomplete: far", "autocomplete", endpoint="autocomplete", espera_resultados=True),
    TestCase("cin", "Autocomplete: cin", "autocomplete", endpoint="autocomplete", espera_resultados=True),
]

# --- CATEGORIA 9: Casos limites ---
TESTES_LIMITES = [
    TestCase("a", "1 caractere (deve rejeitar)", "limite", espera_resultados=False),
    TestCase("ab", "2 caracteres minimo", "limite", espera_resultados=True),
    TestCase("VELOCIDADE", "Tudo maiusculo", "limite", espera_resultados=True),
    TestCase("VeLoC", "Case misto", "limite", espera_resultados=True),
    TestCase("  velocidade  ", "Espacos extras", "limite", espera_resultados=True),
    TestCase("dirigir", "Verbo generico", "limite", espera_resultados=True),
    TestCase("grave", "Busca por gravidade", "limite", espera_resultados=True),
    TestCase("leve", "Busca por gravidade leve", "limite", espera_resultados=True),
]

# --- CATEGORIA 10: Erros ortograficos "de usuario real" (simulacao naturalista) ---
TESTES_USUARIO_REAL = [
    # Como um brasileiro digitaria no celular com pressa
    TestCase("vlocidede", "Digitacao rapida celular", "usuario_real", espera_resultados=True),
    TestCase("velocidaide", "Troca AI por A", "usuario_real", espera_resultados=True),
    TestCase("multta", "Double T na multa", "usuario_real", espera_resultados=True),
    TestCase("trnasito", "Letras embaralhadas", "usuario_real", espera_resultados=True),
    TestCase("infrassao", "SS em vez de C", "usuario_real", espera_resultados=True),
    TestCase("semafaro", "Semaforo com A", "usuario_real", espera_resultados=True),
    TestCase("estacionamento", "Termo comum correto", "usuario_real", espera_resultados=True),
    TestCase("direcao", "Direcao sem acento", "usuario_real", espera_resultados=True),
    TestCase("licensa", "Licenca com S", "usuario_real", espera_resultados=True),
    TestCase("veiclo", "Veiculo sem U", "usuario_real", espera_resultados=True),
    TestCase("sinalizaao", "Sem C em sinalizacao", "usuario_real", espera_resultados=True),
    TestCase("conduzir", "Conduzir (formal)", "usuario_real", espera_resultados=True),
    TestCase("pneu", "Pneu (equipamento)", "usuario_real", espera_resultados=True),
    TestCase("retrovisor", "Retrovisor (equipamento)", "usuario_real", espera_resultados=True),
    TestCase("faixa", "Faixa (pista/pedestre)", "usuario_real", espera_resultados=True),
]


# ============================================================
# MOTOR DE TESTES
# ============================================================

@dataclass
class TestResult:
    test: TestCase
    passou: bool
    status_code: int = 0
    tempo_ms: float = 0.0
    total_resultados: int = 0
    sugestao: Optional[str] = None
    erro: Optional[str] = None
    detalhes: Dict[str, Any] = field(default_factory=dict)


def fazer_request(url: str) -> Dict[str, Any]:
    """Faz GET request e retorna JSON."""
    req = Request(url)
    # Headers de navegador real para nao ser bloqueado pelo middleware anti-bot
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    req.add_header("Accept", "application/json, text/html, */*")
    req.add_header("Accept-Language", "pt-BR,pt;q=0.9,en;q=0.8")
    resp = urlopen(req, timeout=TIMEOUT_SECONDS)
    body = resp.read().decode("utf-8")
    return json.loads(body), resp.status


def executar_teste(tc: TestCase, base_url: str, verbose: bool = False) -> TestResult:
    """Executa um unico caso de teste."""
    query_encoded = quote(tc.query.strip())

    if tc.endpoint == "pesquisa":
        url = f"{base_url}{API_PREFIX}/pesquisa?q={query_encoded}&limit=20"
    elif tc.endpoint == "smart":
        url = f"{base_url}{API_PREFIX}/smart?q={query_encoded}"
    elif tc.endpoint == "autocomplete":
        url = f"{base_url}{API_PREFIX}/autocomplete?q={query_encoded}"
    else:
        url = f"{base_url}{API_PREFIX}/pesquisa?q={query_encoded}"

    t0 = time.time()
    try:
        data, status_code = fazer_request(url)
        tempo = (time.time() - t0) * 1000  # ms
    except HTTPError as e:
        tempo = (time.time() - t0) * 1000
        # Erros 4xx podem ser esperados (ex: query curta demais)
        return TestResult(
            test=tc, passou=(not tc.espera_resultados and e.code in (400, 422)),
            status_code=e.code, tempo_ms=tempo,
            erro=f"HTTP {e.code}: {e.reason}"
        )
    except URLError as e:
        return TestResult(test=tc, passou=False, tempo_ms=0, erro=f"Conexao falhou: {e.reason}")
    except Exception as e:
        return TestResult(test=tc, passou=False, tempo_ms=0, erro=str(e))

    # === Analisar resposta ===
    resultado = TestResult(test=tc, passou=True, status_code=status_code, tempo_ms=tempo)

    if tc.endpoint == "autocomplete":
        # Autocomplete retorna lista direta
        total = len(data) if isinstance(data, list) else 0
        resultado.total_resultados = total
        resultado.detalhes["termos"] = [item.get("termo", "") for item in data[:5]] if isinstance(data, list) else []

        if tc.espera_resultados and total == 0:
            resultado.passou = False
            resultado.erro = "Esperava sugestoes de autocomplete, recebeu 0"
        elif not tc.espera_resultados and total > 0:
            resultado.passou = False
            resultado.erro = f"Nao esperava resultados, recebeu {total}"

    elif tc.endpoint == "smart":
        # Smart retorna {sugestoes: [...], preview: {resultados: [...], total, sugestao}}
        sugestoes = data.get("sugestoes", [])
        preview = data.get("preview", {})
        total = preview.get("total", 0)
        sugestao = preview.get("sugestao")
        resultado.total_resultados = total
        resultado.sugestao = sugestao
        resultado.detalhes["num_sugestoes"] = len(sugestoes)
        resultado.detalhes["sugestoes"] = [s.get("termo", "") for s in sugestoes[:5]]

        if tc.espera_resultados and total == 0 and len(sugestoes) == 0:
            resultado.passou = False
            resultado.erro = "Esperava resultados/sugestoes, recebeu 0"

        if tc.espera_sugestao and sugestao:
            if tc.espera_sugestao.lower() not in sugestao.lower():
                resultado.passou = False
                resultado.erro = f"Sugestao '{sugestao}' nao contem '{tc.espera_sugestao}'"
        elif tc.espera_sugestao and not sugestao:
            # Verificar se a correcao veio como sugestao no topo
            correcoes = [s for s in sugestoes if s.get("tipo") == "correcao"]
            if correcoes:
                termo_corr = correcoes[0].get("termo", "")
                if tc.espera_sugestao.lower() in termo_corr.lower():
                    pass  # OK, veio como sugestao
                else:
                    resultado.passou = False
                    resultado.erro = f"Esperava sugestao '{tc.espera_sugestao}', nao encontrada"
            elif total > 0:
                # Encontrou resultados sem sugestao - pode estar OK se o sistema corrigiu internamente
                pass
            else:
                resultado.passou = False
                resultado.erro = f"Esperava sugestao '{tc.espera_sugestao}', nao encontrada"

    else:
        # Pesquisa retorna {resultados: [...], total, mensagem, sugestao}
        resultados = data.get("resultados", [])
        total = data.get("total", 0)
        sugestao = data.get("sugestao")
        mensagem = data.get("mensagem", "")
        resultado.total_resultados = total
        resultado.sugestao = sugestao

        if tc.espera_resultados:
            if total == 0:
                # Verificar se ao menos tem sugestao
                if sugestao:
                    resultado.detalhes["tem_sugestao"] = True
                    # Passou parcialmente - nao achou resultado mas sugeriu
                else:
                    resultado.passou = False
                    resultado.erro = "Esperava resultados, recebeu 0 (sem sugestao)"
            elif total < tc.min_resultados:
                resultado.passou = False
                resultado.erro = f"Esperava min {tc.min_resultados} resultados, recebeu {total}"
        else:
            if total > 0:
                resultado.passou = False
                resultado.erro = f"Nao esperava resultados, recebeu {total}"

        if tc.espera_sugestao and sugestao:
            if tc.espera_sugestao.lower() not in sugestao.lower():
                resultado.passou = False
                resultado.erro = f"Sugestao '{sugestao}' nao contem '{tc.espera_sugestao}'"

        if tc.espera_conter and resultados:
            encontrou = False
            for r in resultados:
                desc = r.get("descricao", "").lower()
                if tc.espera_conter.lower() in desc:
                    encontrou = True
                    break
            if not encontrou:
                resultado.passou = False
                resultado.erro = f"Nenhum resultado contem '{tc.espera_conter}'"

        if tc.espera_codigo and resultados:
            codigos = [r.get("codigo", "").replace("-", "") for r in resultados]
            if tc.espera_codigo not in codigos:
                resultado.passou = False
                resultado.erro = f"Codigo '{tc.espera_codigo}' nao encontrado nos resultados"

    return resultado


def imprimir_resultado(r: TestResult, verbose: bool = False):
    """Imprime resultado de um teste."""
    icone = f"{C.OK}PASS{C.END}" if r.passou else f"{C.FAIL}FAIL{C.END}"
    tempo_str = f"{r.tempo_ms:.0f}ms"

    if r.tempo_ms > 500:
        tempo_str = f"{C.FAIL}{tempo_str}{C.END}"
    elif r.tempo_ms > 200:
        tempo_str = f"{C.WARN}{tempo_str}{C.END}"
    else:
        tempo_str = f"{C.DIM}{tempo_str}{C.END}"

    detalhes_extra = ""
    if r.sugestao:
        detalhes_extra += f" {C.INFO}sugestao=\"{r.sugestao}\"{C.END}"
    if r.detalhes.get("tem_sugestao"):
        detalhes_extra += f" {C.WARN}(0 resultados mas tem sugestao){C.END}"

    print(f"  [{icone}] {C.BOLD}\"{r.test.query}\"{C.END} -> {r.total_resultados} resultados [{tempo_str}]{detalhes_extra}")

    if not r.passou and r.erro:
        print(f"         {C.FAIL}-> {r.erro}{C.END}")

    if verbose:
        if r.detalhes.get("termos"):
            print(f"         {C.DIM}autocomplete: {r.detalhes['termos']}{C.END}")
        if r.detalhes.get("sugestoes"):
            print(f"         {C.DIM}smart sugestoes: {r.detalhes['sugestoes']}{C.END}")


def executar_categoria(nome: str, testes: List[TestCase], base_url: str, verbose: bool) -> List[TestResult]:
    """Executa todos os testes de uma categoria."""
    print(f"\n{C.BOLD}{'='*60}{C.END}")
    print(f"{C.BOLD} {nome} ({len(testes)} testes){C.END}")
    print(f"{C.BOLD}{'='*60}{C.END}")

    resultados = []
    for tc in testes:
        r = executar_teste(tc, base_url, verbose)
        imprimir_resultado(r, verbose)
        resultados.append(r)
        time.sleep(0.05)  # pequeno delay para nao sobrecarregar

    passou = sum(1 for r in resultados if r.passou)
    falhou = len(resultados) - passou
    taxa = (passou / len(resultados) * 100) if resultados else 0

    cor = C.OK if falhou == 0 else (C.WARN if taxa >= 70 else C.FAIL)
    print(f"\n  {cor}Resultado: {passou}/{len(resultados)} ({taxa:.0f}%){C.END}")

    return resultados


# ============================================================
# RELATORIO FINAL
# ============================================================

def gerar_relatorio(todos_resultados: List[TestResult]):
    """Gera relatorio final consolidado."""
    total = len(todos_resultados)
    passou = sum(1 for r in todos_resultados if r.passou)
    falhou = total - passou
    taxa = (passou / total * 100) if total else 0

    tempos = [r.tempo_ms for r in todos_resultados if r.tempo_ms > 0]
    tempo_medio = sum(tempos) / len(tempos) if tempos else 0
    tempo_max = max(tempos) if tempos else 0
    tempo_min = min(tempos) if tempos else 0
    lentos = sum(1 for t in tempos if t > 500)

    print(f"\n\n{'='*60}")
    print(f"{C.BOLD} RELATORIO FINAL{C.END}")
    print(f"{'='*60}")

    cor_total = C.OK if falhou == 0 else (C.WARN if taxa >= 80 else C.FAIL)
    print(f"\n  Total de testes: {total}")
    print(f"  {C.OK}Passaram: {passou}{C.END}")
    print(f"  {C.FAIL}Falharam: {falhou}{C.END}")
    print(f"  {cor_total}Taxa de sucesso: {taxa:.1f}%{C.END}")

    print(f"\n  {C.BOLD}Performance:{C.END}")
    print(f"  Tempo medio: {tempo_medio:.0f}ms")
    print(f"  Tempo minimo: {tempo_min:.0f}ms")
    print(f"  Tempo maximo: {tempo_max:.0f}ms")
    if lentos:
        print(f"  {C.WARN}Consultas lentas (>500ms): {lentos}{C.END}")

    # Agrupar falhas por categoria
    falhas = [r for r in todos_resultados if not r.passou]
    if falhas:
        print(f"\n  {C.BOLD}Falhas por categoria:{C.END}")
        categorias = {}
        for r in falhas:
            cat = r.test.categoria
            categorias.setdefault(cat, []).append(r)
        for cat, items in sorted(categorias.items()):
            print(f"    {C.FAIL}{cat}{C.END}: {len(items)} falha(s)")
            for r in items:
                print(f"      - \"{r.test.query}\" -> {r.erro}")

    # Resultados com sugestao (voce quis dizer)
    com_sugestao = [r for r in todos_resultados if r.sugestao]
    if com_sugestao:
        print(f"\n  {C.BOLD}Queries com 'Voce quis dizer':{C.END}")
        for r in com_sugestao[:15]:
            print(f"    \"{r.test.query}\" -> sugestao: \"{r.sugestao}\"")
        if len(com_sugestao) > 15:
            print(f"    ... e mais {len(com_sugestao) - 15}")

    # Queries sem resultado e sem sugestao (buracos no dicionario)
    buracos = [r for r in todos_resultados if not r.passou and r.total_resultados == 0 and not r.sugestao]
    if buracos:
        print(f"\n  {C.BOLD}{C.FAIL}BURACOS NO DICIONARIO (sem resultado e sem sugestao):{C.END}")
        for r in buracos:
            print(f"    {C.FAIL}\"{r.test.query}\"{C.END} - {r.test.descricao}")

    print(f"\n{'='*60}")
    if taxa == 100:
        print(f"  {C.OK}{C.BOLD}SISTEMA DE BUSCA: PERFEITO!{C.END}")
    elif taxa >= 90:
        print(f"  {C.OK}SISTEMA DE BUSCA: MUITO BOM ({taxa:.0f}%){C.END}")
    elif taxa >= 75:
        print(f"  {C.WARN}SISTEMA DE BUSCA: BOM, MAS PODE MELHORAR ({taxa:.0f}%){C.END}")
    else:
        print(f"  {C.FAIL}SISTEMA DE BUSCA: PRECISA DE MELHORIAS ({taxa:.0f}%){C.END}")
    print(f"{'='*60}\n")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Teste completo do sistema de busca MultasGO")
    parser.add_argument("--url", default=BASE_URL, help=f"URL base (default: {BASE_URL})")
    parser.add_argument("--verbose", "-v", action="store_true", help="Modo verbose")
    parser.add_argument("--categoria", "-c", help="Rodar apenas uma categoria")
    parser.add_argument("--no-color", action="store_true", help="Desabilitar cores")
    args = parser.parse_args()

    if args.no_color:
        for attr in dir(C):
            if not attr.startswith("_"):
                setattr(C, attr, "")

    base_url = args.url.rstrip("/")

    print(f"\n{C.BOLD}{'='*60}{C.END}")
    print(f"{C.BOLD} MultasGO - Teste Completo do Sistema de Busca{C.END}")
    print(f"{C.BOLD}{'='*60}{C.END}")
    print(f"  URL: {base_url}")
    print(f"  Data: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Verificar se servidor esta rodando
    print(f"\n  Verificando conexao...", end="")
    try:
        urlopen(f"{base_url}/health", timeout=5)
        print(f" {C.OK}OK{C.END}")
    except Exception:
        try:
            urlopen(f"{base_url}/", timeout=5)
            print(f" {C.OK}OK{C.END}")
        except Exception as e:
            print(f" {C.FAIL}FALHOU{C.END}")
            print(f"\n  {C.FAIL}Servidor nao esta rodando em {base_url}{C.END}")
            print(f"  Execute: python iniciar_app.py")
            sys.exit(1)

    # Definir categorias
    categorias = {
        "TERMOS CORRETOS (baseline)": TESTES_CORRETOS,
        "ERROS ORTOGRAFICOS": TESTES_ERROS_ORTOGRAFICOS,
        "PREFIXOS (digitacao parcial)": TESTES_PREFIXOS,
        "SINONIMOS": TESTES_SINONIMOS,
        "BUSCAS COMPOSTAS": TESTES_COMPOSTOS,
        "BUSCA POR CODIGO": TESTES_CODIGOS,
        "SMART ENDPOINT": TESTES_SMART,
        "AUTOCOMPLETE": TESTES_AUTOCOMPLETE,
        "CASOS LIMITES": TESTES_LIMITES,
        "USUARIO REAL (naturalista)": TESTES_USUARIO_REAL,
    }

    # Filtrar categoria se especificada
    if args.categoria:
        key_match = None
        for k in categorias:
            if args.categoria.lower() in k.lower():
                key_match = k
                break
        if key_match:
            categorias = {key_match: categorias[key_match]}
        else:
            print(f"\n  {C.FAIL}Categoria '{args.categoria}' nao encontrada.{C.END}")
            print(f"  Categorias disponiveis:")
            for k in categorias:
                print(f"    - {k}")
            sys.exit(1)

    # Executar testes
    total_testes = sum(len(v) for v in categorias.values())
    print(f"\n  Total de testes: {C.BOLD}{total_testes}{C.END}")

    todos_resultados = []
    for nome, testes in categorias.items():
        resultados = executar_categoria(nome, testes, base_url, args.verbose)
        todos_resultados.extend(resultados)

    # Relatorio final
    gerar_relatorio(todos_resultados)

    # Exit code
    falhas = sum(1 for r in todos_resultados if not r.passou)
    sys.exit(0 if falhas == 0 else 1)


if __name__ == "__main__":
    main()
