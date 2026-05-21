"""
Teste v2 - Busca MultasGO com palavras NOVAS (nao repetidas do v1)
===================================================================
Baseado na analise real do banco de dados (439 registros).
Foca em termos que EXISTEM no banco e erros de digitacao realisticos.

USO:
  python teste/teste_busca_v2.py
  python teste/teste_busca_v2.py --verbose
  python teste/teste_busca_v2.py -c "acidente"
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


BASE_URL = "http://localhost:8080"
API_PREFIX = "/api/v1/infracoes"
TIMEOUT_SECONDS = 10


class C:
    OK = "\033[92m"
    FAIL = "\033[91m"
    WARN = "\033[93m"
    INFO = "\033[96m"
    DIM = "\033[90m"
    BOLD = "\033[1m"
    END = "\033[0m"


@dataclass
class TestCase:
    query: str
    descricao: str
    categoria: str
    espera_resultados: bool = True
    min_resultados: int = 1
    espera_sugestao: Optional[str] = None
    espera_codigo: Optional[str] = None
    endpoint: str = "pesquisa"


# ============================================================
# NOVOS CENARIOS - Todos diferentes do teste v1
# ============================================================

# --- 1. Termos reais do banco (nunca testados antes) ---
TESTES_TERMOS_BANCO = [
    TestCase("acostamento", "Parar no acostamento", "termos_banco", min_resultados=1),
    TestCase("buzinar", "Uso indevido da buzina", "termos_banco", min_resultados=1),
    TestCase("contramao", "Transitar contramao", "termos_banco", min_resultados=1),
    TestCase("rolamento", "Pista de rolamento", "termos_banco", min_resultados=1),
    TestCase("circulacao", "Circulacao de veiculos", "termos_banco", min_resultados=1),
    TestCase("transporte", "Transporte remunerado", "termos_banco", min_resultados=1),
    TestCase("reboque", "Veiculo de reboque/tracao", "termos_banco", min_resultados=1),
    TestCase("guincho", "Reboque/guincho", "termos_banco", min_resultados=1),
    TestCase("acidente", "Acidente de transito", "termos_banco", min_resultados=1),
    TestCase("socorro", "Prestar socorro", "termos_banco", min_resultados=1),
    TestCase("crianca", "Transporte de crianca", "termos_banco", min_resultados=1),
    TestCase("calcada", "Guia da calcada", "termos_banco", min_resultados=1),
    TestCase("fumaca", "Producao de fumaca/gases", "termos_banco", min_resultados=1),
    TestCase("iluminacao", "Sistema de iluminacao", "termos_banco", min_resultados=1),
    TestCase("sinalizar", "Sinalizar manobra", "termos_banco", min_resultados=1),
    TestCase("registro", "Registro de veiculo", "termos_banco", min_resultados=1),
    TestCase("regulamentacao", "Em desacordo regulamentacao", "termos_banco", min_resultados=1),
    TestCase("obstaculo", "Obstaculo na via", "termos_banco", min_resultados=1),
    TestCase("viaduto", "Retorno em viaduto", "termos_banco", min_resultados=1),
    TestCase("ponte", "Estacionar em pontes", "termos_banco", min_resultados=1),
]

# --- 2. Erros ortograficos NOVOS (termos nunca testados) ---
TESTES_ERROS_NOVOS = [
    # Acostamento
    TestCase("acostameto", "Sem N em acostamento", "erros_novos"),
    TestCase("acostamneto", "Letras trocadas MN", "erros_novos"),
    TestCase("acostamemto", "M em vez de N", "erros_novos"),

    # Buzina
    TestCase("busina", "S em vez de Z", "erros_novos"),
    TestCase("buzna", "Sem I", "erros_novos"),

    # Contramao
    TestCase("contramão", "Com til (encoding)", "erros_novos"),
    TestCase("comtramao", "M em vez de N", "erros_novos"),

    # Circulacao
    TestCase("circulasao", "S em vez de C", "erros_novos"),
    TestCase("sirculacao", "S em vez de C no inicio", "erros_novos"),

    # Crianca
    TestCase("criança", "Com cedilha", "erros_novos"),
    TestCase("criansa", "S em vez de C", "erros_novos"),

    # Acidente
    TestCase("acidete", "Sem N", "erros_novos"),
    TestCase("assidente", "SS em vez de C", "erros_novos"),
    TestCase("acidentte", "Double T", "erros_novos"),

    # Calcada
    TestCase("calçada", "Com cedilha", "erros_novos"),
    TestCase("calsada", "S em vez de C", "erros_novos"),

    # Fumaca
    TestCase("fumaça", "Com cedilha", "erros_novos"),
    TestCase("fumassa", "SS em vez de C", "erros_novos"),

    # Pneu
    TestCase("peneu", "Vogal extra", "erros_novos"),
    TestCase("pnel", "L em vez de U", "erros_novos"),

    # Viaduto
    TestCase("viadulto", "L extra", "erros_novos"),
    TestCase("viadto", "Sem U", "erros_novos"),

    # Guincho
    TestCase("gincho", "I em vez de UI", "erros_novos"),
    TestCase("guicho", "Sem N", "erros_novos"),

    # Transporte
    TestCase("trasporte", "Sem N", "erros_novos"),
    TestCase("transpotre", "Letras trocadas", "erros_novos"),

    # Registro
    TestCase("resgistro", "G extra", "erros_novos"),
    TestCase("registto", "Double T", "erros_novos"),

    # Rolamento
    TestCase("rolameto", "Sem N", "erros_novos"),
    TestCase("rolamneto", "Letras trocadas", "erros_novos"),
]

# --- 3. Frases compostas NOVAS baseadas no banco ---
TESTES_COMPOSTOS_NOVOS = [
    TestCase("prestar socorro", "Socorro em acidente", "compostos_novos"),
    TestCase("pista rolamento", "Estacionar na pista", "compostos_novos"),
    TestCase("transporte remunerado", "Transporte ilegal", "compostos_novos"),
    TestCase("mau estado", "Veiculo mau estado", "compostos_novos"),
    TestCase("derramando carga", "Transitar derramando", "compostos_novos"),
    TestCase("guia calcada", "Afastado da guia", "compostos_novos"),
    TestCase("excesso peso", "Sobrepeso veiculo", "compostos_novos"),
    TestCase("dirigir suspensao", "CNH suspensa", "compostos_novos"),
    TestCase("tracao animal", "Veiculo tracao animal", "compostos_novos"),
    TestCase("categoria diferente", "CNH categoria diferente", "compostos_novos"),
    TestCase("transportar passageiro", "Excesso de passageiros", "compostos_novos"),
    TestCase("transitar proibido", "Local proibido", "compostos_novos"),
    TestCase("entregar veiculo", "Entregar veiculo sem CNH", "compostos_novos"),
    TestCase("reduzir velocidade", "Nao reduzir velocidade", "compostos_novos"),
    TestCase("manobra perigosa", "Manobra perigosa/arriscada", "compostos_novos"),
]

# --- 4. Codigos novos (diferentes do teste v1) ---
TESTES_CODIGOS_NOVOS = [
    TestCase("7633", "Codigo celular (76331)", "codigos_novos", espera_resultados=True),
    TestCase("76331", "Codigo celular completo", "codigos_novos", espera_codigo="76331"),
    TestCase("5428", "Codigo estacionar (54281)", "codigos_novos"),
    TestCase("6041", "Codigo conversao (60412)", "codigos_novos"),
    TestCase("5029", "Codigo CNH suspensa (50292)", "codigos_novos"),
    TestCase("741", "Prefixo numerico curto", "codigos_novos"),
    TestCase("5592", "Codigo parar (55920)", "codigos_novos"),
    TestCase("6670", "Codigo iluminacao (66700)", "codigos_novos"),
]

# --- 5. Smart endpoint com novos termos ---
TESTES_SMART_NOVOS = [
    TestCase("aci", "Smart: prefixo acidente", "smart_novos", endpoint="smart"),
    TestCase("buz", "Smart: prefixo buzina", "smart_novos", endpoint="smart"),
    TestCase("cont", "Smart: prefixo contramao", "smart_novos", endpoint="smart"),
    TestCase("circ", "Smart: prefixo circulacao", "smart_novos", endpoint="smart"),
    TestCase("tran", "Smart: prefixo transporte/transito", "smart_novos", endpoint="smart"),
    TestCase("acostameto", "Smart: erro acostamento", "smart_novos", endpoint="smart"),
    TestCase("busina", "Smart: erro buzina", "smart_novos", endpoint="smart", espera_sugestao="buzina"),
    TestCase("7633", "Smart: codigo parcial celular", "smart_novos", endpoint="smart"),
    TestCase("crian", "Smart: prefixo crianca", "smart_novos", endpoint="smart"),
    TestCase("fuma", "Smart: prefixo fumaca", "smart_novos", endpoint="smart"),
]

# --- 6. Autocomplete com novos prefixos ---
TESTES_AUTOCOMPLETE_NOVOS = [
    TestCase("aco", "Autocomplete: acostamento", "autocomplete_novos", endpoint="autocomplete"),
    TestCase("buz", "Autocomplete: buzina", "autocomplete_novos", endpoint="autocomplete"),
    TestCase("con", "Autocomplete: contramao/condutor/conversao", "autocomplete_novos", endpoint="autocomplete"),
    TestCase("gui", "Autocomplete: guia/guincho", "autocomplete_novos", endpoint="autocomplete"),
    TestCase("reb", "Autocomplete: reboque", "autocomplete_novos", endpoint="autocomplete"),
    TestCase("cri", "Autocomplete: crianca", "autocomplete_novos", endpoint="autocomplete"),
    TestCase("fum", "Autocomplete: fumaca", "autocomplete_novos", endpoint="autocomplete"),
    TestCase("via", "Autocomplete: viaduto/via", "autocomplete_novos", endpoint="autocomplete"),
    TestCase("pon", "Autocomplete: ponte", "autocomplete_novos", endpoint="autocomplete"),
    TestCase("ani", "Autocomplete: animal", "autocomplete_novos", endpoint="autocomplete"),
    TestCase("tun", "Autocomplete: tunel", "autocomplete_novos", endpoint="autocomplete"),
    TestCase("lan", "Autocomplete: lanterna", "autocomplete_novos", endpoint="autocomplete"),
]

# --- 7. Linguagem coloquial (como um usuario REAL fala) ---
TESTES_COLOQUIAL = [
    TestCase("batida", "Sinonimo coloquial de acidente", "coloquial"),
    TestCase("colisao", "Sinonimo formal de acidente", "coloquial"),
    TestCase("cadeirinha", "Assento de crianca", "coloquial"),
    TestCase("escapamento", "Fumaca do escapamento", "coloquial"),
    TestCase("meio fio", "Calcada/guia", "coloquial"),
    TestCase("mercadoria", "Transporte de carga", "coloquial"),
    TestCase("filme", "Pelicula/insulfilm no vidro", "coloquial"),
    TestCase("mao contraria", "Contramao coloquial", "coloquial"),
    TestCase("passeio", "Calcada/passeio publico", "coloquial"),
    TestCase("sobrepeso", "Excesso de peso", "coloquial"),
    TestCase("correr demais", "Excesso de velocidade", "coloquial"),
    TestCase("entregar carro", "Entregar veiculo sem CNH", "coloquial"),
]

# --- 8. Erros de digitacao no celular (rapido, troca de letras adjacentes) ---
TESTES_CELULAR = [
    TestCase("veículo", "Com acento (mobile)", "digitacao_celular"),
    TestCase("dirgiir", "Letras embaralhadas dirigir", "digitacao_celular"),
    TestCase("passr", "Digitacao rapida parar", "digitacao_celular"),
    TestCase("estacioar", "Faltando N estacionar", "digitacao_celular"),
    TestCase("capacte", "Faltando E capacete", "digitacao_celular"),
    TestCase("trasitar", "Faltando N transitar", "digitacao_celular"),
    TestCase("condutr", "Faltando O condutor", "digitacao_celular"),
    TestCase("passagero", "Faltando I passageiro", "digitacao_celular"),
    TestCase("segruanca", "Letras trocadas seguranca", "digitacao_celular"),
    TestCase("sinalizacoa", "Letras trocadas sinalizacao", "digitacao_celular"),
    TestCase("ciruclacao", "Letras trocadas circulacao", "digitacao_celular"),
    TestCase("velcocidade", "Letras trocadas velocidade", "digitacao_celular"),
    TestCase("documanto", "A em vez de E documento", "digitacao_celular"),
    TestCase("habiltacao", "Faltando I habilitacao", "digitacao_celular"),
    TestCase("converssao", "SS em vez de S conversao", "digitacao_celular"),
]

# --- 9. Gravidades como busca ---
TESTES_GRAVIDADE = [
    TestCase("gravissima", "Gravidade maxima", "gravidade", min_resultados=5),
    TestCase("media", "Gravidade media", "gravidade", min_resultados=5),
    TestCase("proprietario", "Responsavel proprietario", "gravidade", min_resultados=1),
    TestCase("condutor", "Responsavel condutor", "gravidade", min_resultados=5),
    TestCase("estadual", "Orgao estadual", "gravidade", min_resultados=5),
    TestCase("rodoviario", "Orgao rodoviario", "gravidade", min_resultados=1),
    TestCase("municipal", "Orgao municipal", "gravidade", min_resultados=1),
]

# --- 10. Termos especificos CTB (Codigo Transito Brasileiro) ---
TESTES_CTB = [
    TestCase("ppd", "Permissao para dirigir", "ctb", min_resultados=1),
    TestCase("acc", "Autorizacao para conduzir", "ctb", min_resultados=1),
    TestCase("contran", "Conselho Nacional Transito", "ctb", min_resultados=1),
    TestCase("ctb", "Codigo de Transito Brasileiro", "ctb", min_resultados=1),
    TestCase("lentes corretoras", "Usar lentes obrigatorias", "ctb"),
    TestCase("agravamento", "Fator de agravamento", "ctb"),
]


# ============================================================
# MOTOR DE TESTES (copiado do v1, sem mudancas)
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
    req = Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    req.add_header("Accept", "application/json, text/html, */*")
    req.add_header("Accept-Language", "pt-BR,pt;q=0.9,en;q=0.8")
    resp = urlopen(req, timeout=TIMEOUT_SECONDS)
    body = resp.read().decode("utf-8")
    return json.loads(body), resp.status


def executar_teste(tc: TestCase, base_url: str, verbose: bool = False) -> TestResult:
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
        tempo = (time.time() - t0) * 1000
    except HTTPError as e:
        tempo = (time.time() - t0) * 1000
        return TestResult(
            test=tc, passou=(not tc.espera_resultados and e.code in (400, 422)),
            status_code=e.code, tempo_ms=tempo,
            erro=f"HTTP {e.code}: {e.reason}"
        )
    except URLError as e:
        return TestResult(test=tc, passou=False, tempo_ms=0, erro=f"Conexao falhou: {e.reason}")
    except Exception as e:
        return TestResult(test=tc, passou=False, tempo_ms=0, erro=str(e))

    resultado = TestResult(test=tc, passou=True, status_code=status_code, tempo_ms=tempo)

    if tc.endpoint == "autocomplete":
        total = len(data) if isinstance(data, list) else 0
        resultado.total_resultados = total
        resultado.detalhes["termos"] = [item.get("termo", "") for item in data[:5]] if isinstance(data, list) else []
        if tc.espera_resultados and total == 0:
            resultado.passou = False
            resultado.erro = "Esperava sugestoes de autocomplete, recebeu 0"

    elif tc.endpoint == "smart":
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
            correcoes = [s for s in sugestoes if s.get("tipo") == "correcao"]
            if correcoes:
                termo_corr = correcoes[0].get("termo", "")
                if tc.espera_sugestao.lower() not in termo_corr.lower():
                    resultado.passou = False
                    resultado.erro = f"Esperava sugestao '{tc.espera_sugestao}', recebeu '{termo_corr}'"
            elif total > 0:
                pass
            else:
                resultado.passou = False
                resultado.erro = f"Esperava sugestao '{tc.espera_sugestao}', nao encontrada"

    else:
        resultados = data.get("resultados", [])
        total = data.get("total", 0)
        sugestao = data.get("sugestao")
        resultado.total_resultados = total
        resultado.sugestao = sugestao

        if tc.espera_resultados:
            if total == 0:
                if sugestao:
                    resultado.detalhes["tem_sugestao"] = True
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

        if tc.espera_codigo and resultados:
            codigos = [r.get("codigo", "").replace("-", "") for r in resultados]
            if tc.espera_codigo not in codigos:
                resultado.passou = False
                resultado.erro = f"Codigo '{tc.espera_codigo}' nao encontrado"

    return resultado


def imprimir_resultado(r: TestResult, verbose: bool = False):
    icone = f"{C.OK}PASS{C.END}" if r.passou else f"{C.FAIL}FAIL{C.END}"
    tempo_str = f"{r.tempo_ms:.0f}ms"
    if r.tempo_ms > 500:
        tempo_str = f"{C.FAIL}{tempo_str}{C.END}"
    elif r.tempo_ms > 200:
        tempo_str = f"{C.WARN}{tempo_str}{C.END}"
    else:
        tempo_str = f"{C.DIM}{tempo_str}{C.END}"

    extra = ""
    if r.sugestao:
        extra += f" {C.INFO}sugestao=\"{r.sugestao}\"{C.END}"
    if r.detalhes.get("tem_sugestao"):
        extra += f" {C.WARN}(0 result, tem sugestao){C.END}"

    print(f"  [{icone}] {C.BOLD}\"{r.test.query}\"{C.END} -> {r.total_resultados} res [{tempo_str}]{extra}")
    if not r.passou and r.erro:
        print(f"         {C.FAIL}-> {r.erro}{C.END}")
    if verbose:
        if r.detalhes.get("termos"):
            print(f"         {C.DIM}autocomplete: {r.detalhes['termos']}{C.END}")
        if r.detalhes.get("sugestoes"):
            print(f"         {C.DIM}smart: {r.detalhes['sugestoes']}{C.END}")


def executar_categoria(nome, testes, base_url, verbose):
    print(f"\n{C.BOLD}{'='*60}{C.END}")
    print(f"{C.BOLD} {nome} ({len(testes)} testes){C.END}")
    print(f"{C.BOLD}{'='*60}{C.END}")

    resultados = []
    for tc in testes:
        r = executar_teste(tc, base_url, verbose)
        imprimir_resultado(r, verbose)
        resultados.append(r)
        time.sleep(0.05)

    passou = sum(1 for r in resultados if r.passou)
    taxa = (passou / len(resultados) * 100) if resultados else 0
    cor = C.OK if passou == len(resultados) else (C.WARN if taxa >= 70 else C.FAIL)
    print(f"\n  {cor}Resultado: {passou}/{len(resultados)} ({taxa:.0f}%){C.END}")
    return resultados


def gerar_relatorio(todos):
    total = len(todos)
    passou = sum(1 for r in todos if r.passou)
    falhou = total - passou
    taxa = (passou / total * 100) if total else 0

    tempos = [r.tempo_ms for r in todos if r.tempo_ms > 0]
    tempo_medio = sum(tempos) / len(tempos) if tempos else 0

    print(f"\n\n{'='*60}")
    print(f"{C.BOLD} RELATORIO FINAL - TESTE v2{C.END}")
    print(f"{'='*60}")

    cor = C.OK if falhou == 0 else (C.WARN if taxa >= 80 else C.FAIL)
    print(f"\n  Total: {total} | {C.OK}Pass: {passou}{C.END} | {C.FAIL}Fail: {falhou}{C.END} | {cor}Taxa: {taxa:.1f}%{C.END}")
    print(f"  Tempo medio: {tempo_medio:.0f}ms")

    falhas = [r for r in todos if not r.passou]
    if falhas:
        print(f"\n  {C.BOLD}Falhas:{C.END}")
        categorias = {}
        for r in falhas:
            categorias.setdefault(r.test.categoria, []).append(r)
        for cat, items in sorted(categorias.items()):
            print(f"    {C.FAIL}{cat}{C.END}: {len(items)}")
            for r in items:
                print(f"      - \"{r.test.query}\" -> {r.erro}")

    buracos = [r for r in todos if not r.passou and r.total_resultados == 0 and not r.sugestao]
    if buracos:
        print(f"\n  {C.FAIL}{C.BOLD}BURACOS:{C.END}")
        for r in buracos:
            print(f"    {C.FAIL}\"{r.test.query}\"{C.END} - {r.test.descricao}")

    print(f"\n{'='*60}")
    if taxa == 100:
        print(f"  {C.OK}{C.BOLD}PERFEITO! 100%{C.END}")
    elif taxa >= 90:
        print(f"  {C.OK}MUITO BOM ({taxa:.0f}%){C.END}")
    elif taxa >= 75:
        print(f"  {C.WARN}BOM, PODE MELHORAR ({taxa:.0f}%){C.END}")
    else:
        print(f"  {C.FAIL}PRECISA DE MELHORIAS ({taxa:.0f}%){C.END}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Teste v2 - MultasGO")
    parser.add_argument("--url", default=BASE_URL)
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--categoria", "-c")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args()

    if args.no_color:
        for attr in dir(C):
            if not attr.startswith("_"):
                setattr(C, attr, "")

    base_url = args.url.rstrip("/")

    print(f"\n{C.BOLD}{'='*60}{C.END}")
    print(f"{C.BOLD} MultasGO - Teste v2 (palavras novas){C.END}")
    print(f"{C.BOLD}{'='*60}{C.END}")
    print(f"  URL: {base_url} | Data: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    print(f"\n  Conectando...", end="")
    try:
        urlopen(f"{base_url}/health", timeout=5)
        print(f" {C.OK}OK{C.END}")
    except Exception:
        try:
            urlopen(f"{base_url}/", timeout=5)
            print(f" {C.OK}OK{C.END}")
        except Exception:
            print(f" {C.FAIL}FALHOU{C.END}")
            print(f"  Execute: python iniciar_app.py")
            sys.exit(1)

    categorias = {
        "TERMOS REAIS DO BANCO": TESTES_TERMOS_BANCO,
        "ERROS ORTOGRAFICOS NOVOS": TESTES_ERROS_NOVOS,
        "BUSCAS COMPOSTAS NOVAS": TESTES_COMPOSTOS_NOVOS,
        "CODIGOS NOVOS": TESTES_CODIGOS_NOVOS,
        "SMART ENDPOINT NOVOS": TESTES_SMART_NOVOS,
        "AUTOCOMPLETE NOVOS": TESTES_AUTOCOMPLETE_NOVOS,
        "LINGUAGEM COLOQUIAL": TESTES_COLOQUIAL,
        "DIGITACAO CELULAR (rapida)": TESTES_CELULAR,
        "GRAVIDADE/RESPONSAVEL/ORGAO": TESTES_GRAVIDADE,
        "TERMOS CTB (tecnicos)": TESTES_CTB,
    }

    if args.categoria:
        match = None
        for k in categorias:
            if args.categoria.lower() in k.lower():
                match = k
                break
        if match:
            categorias = {match: categorias[match]}
        else:
            print(f"\n  {C.FAIL}Categoria '{args.categoria}' nao encontrada.{C.END}")
            for k in categorias:
                print(f"    - {k}")
            sys.exit(1)

    total_testes = sum(len(v) for v in categorias.values())
    print(f"  Total: {C.BOLD}{total_testes}{C.END} testes")

    todos = []
    for nome, testes in categorias.items():
        todos.extend(executar_categoria(nome, testes, base_url, args.verbose))

    gerar_relatorio(todos)

    falhas = sum(1 for r in todos if not r.passou)
    sys.exit(0 if falhas == 0 else 1)


if __name__ == "__main__":
    main()
