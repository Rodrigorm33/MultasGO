"""
Fonte única de verdade para sinônimos, correções e termos de busca do MultasGO.
Consolida dados de: search_service.py, spell_corrector.py, suggestion_engine.py
"""
from typing import Dict, List, Set, Optional

# === SINÔNIMOS BIDIRECIONAIS ===
SINONIMOS: Dict[str, List[str]] = {
    # Veículos
    "carro": ["veiculo", "automovel", "auto", "viatura"],
    "veiculo": ["carro", "automovel", "auto", "viatura"],
    "automovel": ["veiculo", "carro", "auto", "viatura"],
    "auto": ["veiculo", "carro", "automovel", "viatura"],
    "viatura": ["veiculo", "carro", "automovel", "auto"],

    # Motocicletas
    "moto": ["motocicleta", "motoneta", "ciclomotor", "bike"],
    "motoca": ["motocicleta", "motoneta", "ciclomotor"],
    "bike": ["motocicleta", "motoneta", "ciclomotor", "moto"],
    "motocicleta": ["moto", "motoca", "motoneta", "ciclomotor"],
    "motoneta": ["motocicleta", "moto", "motoca", "ciclomotor"],
    "ciclomotor": ["motocicleta", "moto", "motoneta"],

    # Condutores
    "motorista": ["condutor", "piloto", "guia"],
    "piloto": ["condutor", "motorista", "guia"],
    "guia": ["condutor", "motorista", "piloto"],
    "condutor": ["motorista", "piloto", "guia"],

    # Estacionamento
    "parar": ["estacionar", "deixar"],
    "deixar": ["estacionar", "parar"],
    "estacionar": ["parar", "deixar", "imobilizar"],
    "estacionamento": ["parar", "deixar", "estacionar"],
    "imobilizar": ["parar", "estacionar", "deixar"],
    "abandonar": ["deixar", "parar", "estacionar"],

    # Velocidade
    "rapidez": ["velocidade", "pressa", "limite"],
    "rapido": ["velocidade", "rapidez"],
    "correr": ["velocidade", "rapidez"],
    "velocidade": ["rapidez", "rapido", "correr", "limite", "radar"],
    "radar": ["velocidade", "limite"],
    "limite": ["velocidade", "maxima", "permitida", "radar"],
    "pressa": ["velocidade", "rapidez"],

    # Seguranca
    "seguranca": ["protecao", "equipamento", "cinto", "capacete"],
    "protecao": ["seguranca", "equipamento", "cinto", "capacete"],

    # Documentos
    "carteira": ["habilitacao", "documento", "cnh", "licenca"],
    "cnh": ["habilitacao", "documento", "carteira"],
    "habilitacao": ["carteira", "documento", "cnh", "licenca"],
    "documento": ["carteira", "habilitacao", "cnh"],
    "licenca": ["habilitacao", "carteira", "documento"],
    "permissao": ["habilitacao", "licenca", "autorizacao"],

    # Equipamentos
    "equipamento": ["obrigatorio", "triangulo", "extintor"],
    "obrigatorio": ["equipamento", "necessario", "exigido"],
    "necessario": ["obrigatorio", "equipamento", "exigido"],
    "exigido": ["obrigatorio", "equipamento", "necessario"],

    # Multa/Infracao
    "multa": ["infracao", "auto"],
    "infracao": ["multa", "auto"],

    # Bicicletas
    "bicicleta": ["bike", "ciclovia"],
    "ciclovia": ["bicicleta", "bike"],

    # Celular/Telefone
    "celular": ["telefone", "aparelho", "dispositivo"],
    "aparelho": ["telefone", "celular", "dispositivo"],
    "smartphone": ["telefone", "celular", "aparelho"],

    # === BUSCAS COMPOSTAS (sinônimos com contexto) ===

    # Sinal/semaforo
    "furar sinal": ["furar_sinal_especial"],
    "queimar sinal": ["furar_sinal_especial"],
    "passar sinal": ["furar_sinal_especial"],
    "avancar sinal": ["furar_sinal_especial"],

    # Alcool
    "etilometro": ["alcool", "influencia", "teste", "recusar", "submetido"],
    "bafometro": ["alcool", "influencia", "teste", "recusar", "submetido"],
    "bebida": ["alcool", "influencia", "teste", "recusar", "submetido"],
    "bebida alcoolica": ["alcool", "influencia", "teste", "recusar", "submetido"],
    "teste bafometro": ["bafometro_especial"],
    "teste do bafometro": ["bafometro_especial"],
    "recusar bafometro": ["bafometro_especial"],
    "beber dirigir": ["alcool", "influencia", "teste", "recusar", "submetido", "substancia"],
    "embriagado": ["alcool", "influencia", "teste", "recusar", "submetido", "substancia"],
    "alcoolizado": ["alcool", "influencia", "teste", "recusar", "submetido", "substancia"],
    "dirigir bebado": ["alcool", "influencia", "teste", "recusar", "submetido", "substancia"],

    # Celular dirigindo
    "usar celular": ["celular"],
    "celular dirigindo": ["celular"],
    "dirigir falando": ["celular"],
    "whatsapp": ["celular"],
    "telefone celular": ["celular"],

    # Estacionamento composto
    "estacionar errado": ["estacionamento", "parar", "local", "proibido"],
    "parar lugar proibido": ["estacionamento", "parar", "local", "proibido"],
    "area carga": ["estacionamento", "parar", "local", "proibido"],
    "vaga deficiente": ["estacionamento", "parar", "local", "proibido"],

    # Velocidade composto
    "excesso velocidade": ["velocidade", "limite", "radar", "maxima", "permitida"],
    "muito rapido": ["velocidade", "limite", "radar", "maxima", "permitida"],
    "correr demais": ["velocidade", "limite", "radar", "maxima", "permitida"],

    # Documentacao composta
    "carteira vencida": ["habilitacao", "documento", "carteira", "vencida", "valida"],
    "documento vencido": ["habilitacao", "documento", "carteira", "vencida", "valida"],
    "cnh vencida": ["habilitacao", "documento", "carteira", "vencida", "valida"],
    "sem carteira": ["habilitacao", "documento", "carteira", "vencida", "valida"],
    "dirigir sem habilitacao": ["habilitacao", "documento", "carteira", "vencida", "valida"],

    # Cinto
    "sem cinto": ["cinto", "seguranca", "protecao", "individual"],
    "cinto seguranca": ["cinto", "seguranca", "protecao", "individual"],
    "nao usar cinto": ["cinto", "seguranca", "protecao", "individual"],

    # Conversao
    "conversao proibida": ["conversao", "retorno", "curva", "manobra"],
    "retorno proibido": ["conversao", "retorno", "curva", "manobra"],
    "curva proibida": ["conversao", "retorno", "curva", "manobra"],

    # Ultrapassagem
    "ultrapassar errado": ["ultrapassagem", "ultrapassar", "faixa", "contramao"],
    "ultrapassagem proibida": ["ultrapassagem", "ultrapassar", "faixa", "contramao"],
    "passar carro": ["ultrapassagem", "ultrapassar", "faixa", "contramao"],

    # Capacete
    "sem capacete": ["capacete", "protecao", "motocicleta", "moto"],
    "nao usar capacete": ["capacete", "protecao", "motocicleta", "moto"],

    # Placa
    "placa ilegivel": ["placa", "identificacao", "numero", "caracteres"],
    "placa suja": ["placa", "identificacao", "numero", "caracteres"],
    "sem placa": ["placa", "identificacao", "numero", "caracteres"],

    # Farol
    "farol apagado": ["farol", "luz", "iluminacao", "aceso"],
    "sem farol": ["farol", "luz", "iluminacao", "aceso"],
    "luz apagada": ["farol", "luz", "iluminacao", "aceso"],

    # Transporte
    "transporte passageiro": ["transporte", "passageiro", "pessoa", "lotacao"],
    "muita gente": ["transporte", "passageiro", "pessoa", "lotacao"],
    "excesso passageiro": ["transporte", "passageiro", "pessoa", "lotacao"],

    # Rodizio
    "rodizio": ["rodizio", "circulacao", "placa", "restricao"],
    "circular rodizio": ["rodizio", "circulacao", "placa", "restricao"],

    # Faixa
    "faixa errada": ["faixa", "pista", "circulacao", "preferencial"],
    "mudar faixa": ["faixa", "pista", "circulacao", "preferencial"],
    "faixa onibus": ["faixa", "pista", "circulacao", "preferencial"],

    # Pedestres
    "atropelamento": ["pedestre", "pessoa", "atravessar", "faixa"],
    "nao dar preferencia": ["pedestre", "pessoa", "atravessar", "faixa"],
    "pedestre": ["pedestre", "pessoa", "atravessar", "faixa"],

    # Ruido
    "barulho": ["ruido", "som", "perturbacao", "poluicao"],
    "som alto": ["ruido", "som", "perturbacao", "poluicao"],
    "poluicao sonora": ["ruido", "som", "perturbacao", "poluicao"],

    # Equipamentos
    "equipamento obrigatorio": ["equipamento", "obrigatorio", "portatil", "triangulo"],
    "triangulo": ["equipamento", "obrigatorio", "portatil"],
    "extintor": ["equipamento", "obrigatorio", "portatil"],

    # Peso
    "excesso peso": ["peso", "carga", "limite", "maximo"],
    "muito peso": ["peso", "carga", "limite", "maximo"],
    "sobrepeso": ["peso", "carga", "limite", "maximo"],

    # Fumaca/poluicao
    "fumaca": ["fumaca", "gases", "poluicao", "escapamento"],
    "escapamento": ["fumaca", "gases", "poluicao"],

    # Acidente/socorro
    "acidente": ["acidente", "socorro", "vitima", "envolvido"],
    "socorro": ["acidente", "vitima", "envolvido", "prestar"],
    "batida": ["acidente", "socorro", "vitima", "envolvido"],
    "colisao": ["acidente", "socorro", "vitima", "envolvido"],

    # Crianca
    "crianca": ["crianca", "menor", "seguranca"],
    "menor": ["crianca", "seguranca"],
    "cadeirinha": ["crianca", "seguranca", "transportar"],

    # Acostamento
    "acostamento": ["acostamento", "pista", "rolamento"],

    # Buzina
    "buzina": ["buzina", "buzinar", "som"],
    "buzinar": ["buzina", "som"],

    # Contramao
    "contramao": ["contramao", "direcao", "sentido"],
    "mao contraria": ["contramao", "direcao", "sentido"],

    # Reboque/guincho
    "reboque": ["reboque", "tracao", "guincho"],
    "guincho": ["reboque", "tracao"],

    # Calcada/meio-fio
    "calcada": ["calcada", "guia", "meio", "passeio"],
    "meio fio": ["calcada", "guia"],
    "passeio": ["calcada", "guia", "pedestre"],

    # Carga
    "carga": ["carga", "peso", "transporte", "derramando"],
    "mercadoria": ["carga", "transporte"],

    # Pneu
    "pneu": ["pneu", "conservacao", "mau"],
    "pneu careca": ["pneu", "conservacao", "mau"],

    # Vidro/pelicula
    "pelicula": ["pelicula", "vidro", "insulfilm"],
    "insulfilm": ["pelicula", "vidro"],
    "filme": ["pelicula", "vidro", "insulfilm"],

    # Luzes
    "lanterna": ["luz", "iluminacao", "farol"],
    "luz": ["farol", "iluminacao", "lanterna"],
    "iluminacao": ["luz", "farol", "lanterna"],

    # Animal
    "animal": ["animal", "tracao"],

    # Tunel
    "tunel": ["tunel", "luz", "farol"],

    # Viaduto/ponte
    "viaduto": ["viaduto", "ponte", "retorno"],
    "ponte": ["viaduto", "ponte", "estacionar"],
}

# === CORREÇÕES ORTOGRÁFICAS (erros comuns → forma correta) ===
CORRECOES: Dict[str, str] = {
    # Pelicula/insulfilm
    "peliculla": "pelicula", "pelliculas": "pelicula", "insufilm": "insulfilm",
    "insulfilme": "insulfilm", "insulfime": "insulfilm", "insufilme": "insulfilm",
    # Transito
    "tansito": "transito", "trasito": "transito", "transitto": "transito", "transsito": "transito",
    "trnasito": "transito", "tranzito": "transito",
    # Infracao
    "infrasao": "infracao", "infrassao": "infracao", "infrasão": "infracao",
    "infração": "infracao",
    # Velocidade
    "velosidade": "velocidade", "velicidade": "velocidade", "belocidade": "velocidade",
    "velocidde": "velocidade", "velocidaide": "velocidade", "vlocidade": "velocidade",
    "velocidate": "velocidade", "vlocidede": "velocidade", "velocidae": "velocidade",
    # Alcool
    "alcol": "alcool", "alchool": "alcool", "alkool": "alcool", "alcohol": "alcool",
    # Celular
    "selular": "celular", "cellular": "celular", "cellar": "celular", "selelar": "celular",
    "telefon": "celular", "celulr": "celular", "celualr": "celular",
    # Direcao
    "diresao": "direcao",
    # Estacionar
    "estacioanr": "estacionar", "estasionar": "estacionar", "estaconar": "estacionar",
    # Veiculo
    "vehiculo": "veiculo",
    # Farol
    "faroll": "farol", "pharol": "farol",
    # Documento
    "documneto": "documento", "documetno": "documento", "ducumento": "documento",
    # Capacete
    "casacete": "capacete", "capacette": "capacete", "capassete": "capacete",
    # Motocicleta
    "motocileta": "motocicleta",
    # Condutor
    "conditor": "condutor", "codnutor": "condutor", "comdutor": "condutor",
    # Passageiro
    "pasageiro": "passageiro", "pasajeiro": "passageiro",
    # Cinto
    "cinturao": "cinto", "cinturo": "cinto", "sinturao": "cinto",
    # Placa
    "plaka": "placa", "plca": "placa",
    # Seguranca
    "segurnaca": "seguranca", "siguranca": "seguranca", "seguransa": "seguranca",
    # Ultrapassagem
    "ultrpassagem": "ultrapassagem", "ultrapassajem": "ultrapassagem",
    # Retorno
    "retrno": "retorno",
    # Proibido
    "probido": "proibido", "poibido": "proibido", "probibido": "proibido",
    # Sinalizacao
    "sinalizaçao": "sinalizacao",
    # Circulacao
    "circulaçao": "circulacao", "sirculacao": "circulacao", "circulasao": "circulacao",
    # Via
    "estrada": "via", "rua": "via", "avenida": "via", "rodovia": "via",
    # Acidente
    "acidente": "acidente", "acidete": "acidente", "assidente": "acidente",
    # Buzina
    "busina": "buzina", "buzna": "buzina",
    # Contramao
    "contramão": "contramao", "contra mao": "contramao",
    # Acostamento
    "acostameto": "acostamento", "acostamneto": "acostamento",
    # Fumaca
    "fumaça": "fumaca",
    # Calcada
    "calçada": "calcada", "calsada": "calcada",
    # Crianca
    "criança": "crianca", "criansa": "crianca",
    # Pneu
    "pnel": "pneu", "peneu": "pneu",
    # Guincho
    "gincho": "guincho", "guicho": "guincho",
    # Viaduto
    "viadulto": "viaduto",
    # Habilitacao variantes extras
    "abilitasao": "habilitacao", "habilitaçao": "habilitacao",
    # Alcool extras
    "alcohl": "alcool",
}

# === BUSCAS ESPECIAIS (códigos pré-definidos) ===
BUSCAS_ESPECIAIS: Dict[str, List[str]] = {
    "bafometro_especial": ["51691", "75790", "51692"],
    "furar_sinal_especial": ["60501", "60502", "60503", "59591", "60841", "56731", "56732"],
}

# === TERMOS PRIORITÁRIOS (alta frequência) ===
TERMOS_PRIORITARIOS: Set[str] = {
    "velocidade", "alcool", "celular", "farol", "estacionar",
    "veiculo", "documento", "habilitacao", "capacete", "conversao",
    "pelicula", "insulfilm", "transito", "infracao", "condutor",
    "motocicleta", "passageiro", "cinto", "placa", "seguranca",
    "ultrapassagem", "retorno", "proibido", "sinalizacao", "carro",
    "moto", "motorista", "multa", "radar", "faixa", "pedestre",
    "bafometro", "sinal", "telefone", "acidente", "buzina",
    "contramao", "acostamento", "fumaca", "crianca", "pneu",
    "carga", "guincho", "reboque", "calcada", "lanterna",
    "viaduto", "ponte", "tunel", "animal", "pelicula",
}

# === COMBINAÇÕES PERMITIDAS (multi-word queries) ===
COMBINACOES_PERMITIDAS: List[List[str]] = [
    ["cinto", "seguranca"], ["telefone", "celular"],
    ["banco", "dados"], ["codigo", "infracao"],
    ["capacete", "seguranca"], ["faixa", "pedestre"],
    ["placa", "veiculo"], ["documento", "veiculo"],
    ["habilitacao", "vencida"], ["pneu", "desgastado"],
    ["pneu", "careca"],
]


def obter_sinonimos(termo: str) -> List[str]:
    """Retorna sinônimos para um termo normalizado."""
    return SINONIMOS.get(termo.lower().strip(), [])


def obter_correcao(termo: str) -> Optional[str]:
    """Retorna correção ortográfica se disponível."""
    return CORRECOES.get(termo.lower().strip())
