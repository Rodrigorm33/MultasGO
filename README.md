<img width="1222" height="801" alt="image" src="https://github.com/user-attachments/assets/5463d720-5e38-490a-ba22-bf1fab2ce067" />

🚗 MultasGO – Pesquisa Inteligente de Infrações de Trânsito

Sistema avançado para consulta de autos de infração no Brasil, com correção ortográfica, sugestões “você quis dizer” e proteção contra bots.

🌟 Principais Funcionalidades
🔍 Busca Inteligente

Pesquisa por código (ex: 60501) ou texto com relevância.

Correção ortográfica automática (ex: “velosidade” → “velocidade”).

Sistema “Você quis dizer” estilo Google.

Sinônimos contextuais (ex: “bafômetro” encontra infrações de álcool).

Busca insensível a acentos (“alcool” / “álcool”).

🎨 Interface Moderna

Design responsivo com tema de semáforo.

Cards interativos com detalhes expansíveis.

Destaque dos termos pesquisados.

Validação de entrada em tempo real.

Orientações educativas em pesquisas inválidas.

⚡ Performance

Cache inteligente com limite de memória configurável.

Warm-up automático (primeira consulta até 80% mais rápida).

Reuso de conexões HTTP.

Monitor de performance com alertas.

GC otimizado para evitar memory leaks.

🛡️ Segurança

Proteção anti-bot com detecção de User-Agents maliciosos.

Bloqueio de IPs de alto risco (70+ ranges).

CAPTCHA matemático em acessos suspeitos.

Rate limiting (100 req/min/IP).

Validação contra SQL Injection e XSS.

🚀 Como Usar
⚠️ Dados não incluídos

Por segurança, o repositório não contém:

❌ Banco de dados

❌ Arquivos CSV

❌ Configurações .env

📊 Passos básicos

Baixe o CSV de infrações do CTB.

Renomeie para BANCODADOS_LIMPO.csv e coloque na raiz.

Execute:

python start.py


O sistema irá:
✅ Criar o banco de dados
✅ Importar o CSV
✅ Instalar dependências
✅ Inicializar cache e warm-up
✅ Abrir o navegador em http://localhost:8080

💻 Tecnologias

Backend

FastAPI (async)

SQLite / PostgreSQL

SQLAlchemy + Pydantic

Frontend

HTML5 / CSS3 responsivo

JavaScript ES6+

Font Awesome

Paleta baseada em semáforo

Sistemas internos

SpellCorrector (ortografia)

SuggestionEngine (sugestões)

SmartCache (cache com TTL)

PerformanceMonitor (monitoramento)

GeoSecurityMiddleware (proteção geográfica)

📊 Correção Inteligente

Mais de 95 correções específicas para termos de trânsito, com taxa de sucesso de 100% em <5ms.

Exemplos:

"velosidade" → "velocidade"
"infraçao" → "infracao"
"alcol" → "alcool"
"tansito" → "transito"

🛡️ Segurança
Níveis de Risco

🟢 SAFE (0–19): acesso normal

🟡 LOW (20–39): monitorado

🟠 MEDIUM (40–59): rate limiting

🔴 HIGH (60–79): CAPTCHA obrigatório

⚫ CRITICAL (80+): bloqueio

Padrões Detectados

URLs suspeitas: /admin, /phpmyadmin, /.env

Injeções: union, drop, script, eval

Headers ausentes: Accept, Accept-Language

⚙️ Configuração

Arquivo .env (exemplo):

MAX_CACHE_MEMORY_MB=100
CACHE_CLEANUP_INTERVAL=1800
HTTP_POOL_CONNECTIONS=10
RATE_LIMIT_REQUESTS=100
BLOCK_DURATION=300
PORT=8080

📈 Monitoramento

/debug/metrics → métricas de performance/cache

/debug/security-stats → estatísticas de segurança

Exemplo:

curl http://localhost:8080/debug/metrics | jq '.performance'

📁 Estrutura
MultasGO/
├── app/
│   ├── api/endpoints/         # Endpoints
│   ├── core/                  # Sistemas internos
│   ├── db/                    # Banco
│   ├── middleware/            # Middlewares de segurança
│   ├── schemas/               # Pydantic
│   ├── services/              # Lógica
│   ├── static/                # CSS/JS
│   └── templates/             # HTML
├── multasgo.db
├── start.py
└── requirements.txt

🎯 APIs

Pesquisa:

GET /api/v1/infracoes/pesquisa?q={termo}


Explorador:

GET /api/v1/infracoes/explorador?skip=0&limit=10


Pesquisa avançada:

POST /api/v1/infracoes/explorador
{
  "gravidade": "Gravissima",
  "pontos_min": 5,
  "busca": "velocidade"
}

🏆 Diferenciais

Correção ortográfica com “Você quis dizer” estilo Google.

Sinônimos inteligentes adaptados ao CTB.

Orientações educativas de pesquisa.

Proteção geográfica contra bots.

Warm-up para consultas imediatas.

CAPTCHA matemático para acessos suspeitos.

📞 Suporte

Swagger: http://localhost:8080/docs

Métricas: http://localhost:8080/debug/metrics

Interface: http://localhost:8080

📄 Licença

Licença MIT – Uso livre e otimizado para consultas ao CTB.
