# 🚗 MultasGO - Sistema Avançado de Pesquisa de Infrações de Trânsito

> **Sistema inteligente para consulta de autos de infração de trânsito brasileiro com correção ortográfica automática, sugestões "você quis dizer" e proteção avançada contra bots.**

## 🌟 **Funcionalidades Principais**

### 🔍 **Sistema de Busca Inteligente**
- **Pesquisa exata** por código de infração (ex: 60501, 51691)
- **TF-IDF in-memory index** com ranking estilo Google
- **Smart overlay** em tempo real com sugestões + preview de resultados
- **Autocomplete** por prefixo/substring (0.19ms latência)
- **Correção ortográfica automática** - 96 correções (ex: "velosidade" → "velocidade")
- **149 sinônimos** inteligentes (ex: "bafômetro" encontra infrações de álcool)
- **Busca insensível a acentos** (funciona com "alcool" ou "álcool")
- **297 testes automatizados** com 100% de aprovação

### 🎨 **Interface Moderna**
- **Design responsivo** com tema de semáforo (verde, amarelo, vermelho)
- **Cards interativos** com detalhes expansíveis
- **Destaque visual** dos termos pesquisados
- **Validação em tempo real** do campo de busca
- **Proteção contra múltiplas palavras** com popup educativo

### ⚡ **Performance e Otimização**
- **Cache inteligente** com limite de memória configurável
- **Warm-up automático** para primeira consulta 80% mais rápida
- **Pool de conexões HTTP** reutilizáveis
- **Monitor de performance** com alertas automáticos
- **Garbage collection** inteligente para evitar memory leaks

### 🛡️ **Segurança Avançada**
- **Proteção anti-bot** com detecção de User-Agents maliciosos
- **Bloqueio de IPs chineses** (70+ ranges mapeados)
- **CAPTCHA matemático** para requests suspeitos
- **Rate limiting** de 100 requests/min por IP
- **Validação rigorosa** contra SQL injection e XSS

## 📦 **Dataset (não incluído no repositório)**

O arquivo `BANCODADOS_LIMPO.csv` (~5MB) com as infrações do CTB **não está versionado** neste repo — é a fonte primária do autor e está coberto pelo `.gitignore`.

Para rodar localmente você precisa fornecer um CSV com as colunas esperadas pelo modelo (`app/models/infracao_model.py`). Sugestões de fontes públicas:
- **Portal CTB** — Anexo II do Código de Trânsito Brasileiro
- **Dados abertos do DENATRAN/SENATRAN**
- **Datasets de transparência estadual** (DETRANs)

Coloque o arquivo final em `BANCODADOS_LIMPO.csv` na raiz do projeto antes de rodar `python start.py`.

## 🚀 **Inicialização Rápida**

### **Método Simplificado:**
```bash
# Clique duas vezes no arquivo ou execute:
python start.py
```

O sistema irá:
- ✅ Configurar banco de dados automaticamente
- ✅ Instalar dependências se necessário
- ✅ Inicializar cache e warm-up
- ✅ Abrir o navegador automaticamente em http://localhost:8080

### **Comandos Avançados:**
```bash
python start.py                    # Desenvolvimento
python start.py --prod            # Produção
python start.py --setup-only      # Apenas configurar
```

## 💻 **Tecnologias e Arquitetura**

### **Backend:**
- **FastAPI** - Framework web moderno e async
- **SQLite/PostgreSQL** - Suporte a ambos os bancos
- **SQLAlchemy** - ORM com consultas SQL otimizadas
- **Pydantic** - Validação de dados e schemas

### **Sistemas Próprios Implementados:**
- **app/search/** - Modulo de busca completo (TF-IDF, spell, autocomplete, analytics)
- **CorretorOrtografico** - 5 camadas de correção, 96 correções diretas, 100% Python nativo
- **InMemorySearchIndex** - Indice TF-IDF com two-pass retrieval
- **SmartCache** - Cache inteligente com TTL e limite de memória
- **PerformanceMonitor** - Monitoramento em tempo real
- **GeoSecurityMiddleware** - Proteção geográfica avançada

### **Frontend:**
- **HTML5/CSS3** moderno com design responsivo
- **JavaScript ES6+** com fetch API
- **Font Awesome** para ícones
- **Design system** baseado em cores de semáforo

## 📊 **Sistema de Correção Ortográfica**

### **Estratégia em 5 Camadas** (`app/search/spell.py`):
1. **Busca Exata** - Verificação direta no banco
2. **Dicionário de Correções** - 96 correções específicas de trânsito
3. **Normalização** - Remove acentos e case insensitive
4. **Similaridade difflib** - Python nativo com algoritmo otimizado
5. **Levenshtein** - Último recurso para casos extremos

### **Dicionário** (`app/search/dictionaries/terms.py`):
- **96 CORRECOES** - ex: "velosidade"→"velocidade", "celuar"→"celular", "sirculacao"→"circulacao"
- **149 SINONIMOS** - ex: "bafometro"→etilometro, "buzina"→buzina, "guincho"→reboque
- **50 TERMOS_PRIORITARIOS** - termos com boost no ranking

### **Taxa de Sucesso: 100%** (297 testes automatizados)

## 🛡️ **Sistema de Segurança Avançada**

### **Proteção Anti-Bot:**
- **70+ ranges de IPs chineses** mapeados e bloqueados
- **Detecção de User-Agents maliciosos**: python-requests, scrapy, sqlmap, etc.
- **CAPTCHA matemático** para requests suspeitos
- **Análise de risco** baseada em múltiplos fatores

### **Níveis de Risco:**
- 🟢 **SAFE** (0-19): Acesso normal
- 🟡 **LOW** (20-39): Monitoramento
- 🟠 **MEDIUM** (40-59): Rate limiting
- 🔴 **HIGH** (60-79): CAPTCHA obrigatório
- ⚫ **CRITICAL** (80+): Bloqueio imediato

### **Padrões de Ataque Detectados:**
```bash
URLs suspeitas: /admin, /wp-admin, /phpmyadmin, /.env
Parâmetros maliciosos: union, select, drop, script, eval
Headers ausentes: Accept, Accept-Language
```

## ⚙️ **Configuração Avançada**

### **Arquivo `.env` - Configurações Recomendadas:**
```bash
# === PERFORMANCE ===
MAX_CACHE_MEMORY_MB=100        # Limite cache (ajustar conforme RAM)
CACHE_CLEANUP_INTERVAL=1800    # Limpeza a cada 30min
HTTP_POOL_CONNECTIONS=10       # Conexões simultâneas
HTTP_TIMEOUT=30                # Timeout requests

# === WARM-UP ===
ENABLE_WARMUP=True             # Ativar warm-up
WARMUP_QUERIES=velocidade,alcool,celular,farol,estacionar

# === SEGURANÇA ===
RATE_LIMIT_REQUESTS=100        # 100 requests/min por IP
BLOCK_DURATION=300             # Bloqueio por 5min
ENABLE_BOT_PROTECTION=True     # Proteção anti-bot

# === DATABASE ===
DB_POOL_SIZE=5                 # Pool de conexões DB
DB_MAX_OVERFLOW=10             # Conexões extras
DB_POOL_RECYCLE=3600          # Reciclar conexões (1h)

# === PORTA ===
PORT=8080                      # Porta produção = desenvolvimento
```

## 📈 **Monitoramento e Debug**

### **Endpoints de Debug (desenvolvimento):**

#### 📊 **Métricas Completas** - `/debug/metrics`
```json
{
  "performance": {
    "memory": {"system_percent": 45.2, "process_mb": 180.5},
    "optimization": {"gc_runs": 15, "cache_cleanups": 8}
  },
  "cache": {
    "search": {"memory_usage_mb": 25.8, "hit_rate_percent": 89.5}
  },
  "geo_security": {
    "chinese_ips_detected": 23,
    "blocked_ips": 5
  }
}
```

#### 🔒 **Estatísticas de Segurança** - `/debug/security-stats`
```json
{
  "active_clients": 15,
  "blocked_clients": 3,
  "suspicious_ips": 8,
  "total_blocks": 12
}
```

### **Comandos de Teste:**
```bash
# Verificar uso de memória
curl http://localhost:8080/debug/metrics | jq '.performance.memory'

# Verificar cache
curl http://localhost:8080/debug/metrics | jq '.cache'

# Verificar segurança
curl http://localhost:8080/debug/security-stats
```

## 📁 **Estrutura do Projeto**

```
MultasGO/
├── app/
│   ├── api/endpoints/infracoes.py  # 12 endpoints (pesquisa, smart, autocomplete, analytics)
│   ├── search/                     # Modulo de busca (single source of truth)
│   │   ├── engine.py               # pesquisar() - orquestrador principal
│   │   ├── in_memory.py            # InMemorySearchIndex - TF-IDF ranking
│   │   ├── spell.py                # CorretorOrtografico - 5 camadas
│   │   ├── autocomplete.py         # Prefixo/substring matching
│   │   ├── analytics.py            # Tracking de queries
│   │   ├── validators.py           # Whitelist input validation
│   │   └── dictionaries/terms.py   # 96 correcoes, 149 sinonimos, 50 prioritarios
│   ├── core/                       # Cache, config, performance monitor
│   ├── db/                         # SQLite/PostgreSQL adaptativo
│   ├── middleware/                  # Security, geo-blocking, monitoring
│   ├── services/search_service.py  # Thin wrapper → app/search/
│   ├── static/css/styles.css       # Design responsivo + overlay fix
│   ├── static/js/script.js         # Smart overlay + autocomplete
│   └── templates/                  # HTML (index, explorador)
├── teste/                          # 297 test cases (100% pass)
├── multasgo.db                     # Banco SQLite (439 registros)
├── start.py                        # Inicializador inteligente
└── requirements.txt                # Dependencias (sem RapidFuzz)
```

## 🎯 **APIs Disponíveis**

### **Pesquisa Principal:**
```bash
GET /api/v1/infracoes/pesquisa?q={termo}&limit=10&skip=0
```

### **Smart Overlay (sugestoes + preview):**
```bash
GET /api/v1/infracoes/smart?q={termo}&limite_sugestoes=8&limite_preview=5
```

### **Autocomplete:**
```bash
GET /api/v1/infracoes/autocomplete?q={prefixo}
```

### **Explorador:**
```bash
GET /api/v1/infracoes/explorador?skip=0&limit=10
```

### **Analytics:**
```bash
GET /api/v1/infracoes/termos-populares
GET /api/v1/infracoes/analytics/estatisticas
GET /api/v1/infracoes/analytics/queries-populares
GET /api/v1/infracoes/analytics/queries-sem-resultado
```

## 🧪 **Validação e Testes**

### **Sistema de Correção:**
- ✅ Taxa de sucesso: **100%** (297 testes automatizados)
- ✅ Tempo médio: **< 5ms** por correção
- ✅ **96 correções** + **149 sinônimos** + **50 termos prioritários**
- ✅ Autocomplete: **0.19ms** latência média

### **Performance:**
- ✅ Primeira consulta **80% mais rápida** com warm-up
- ✅ Cache hit rate **> 80%** após inicialização
- ✅ Controle de memória **< 100MB** de cache
- ✅ **Zero memory leaks** detectados

### **Segurança:**
- ✅ **95% dos ataques** automatizados bloqueados
- ✅ IPs chineses detectados e tratados
- ✅ Rate limiting funcionando corretamente
- ✅ CAPTCHA matemático operacional

## 🏆 **Melhorias Implementadas**

### **v3.0 (Feb 2026):**
1. **Modulo `app/search/`** - Refatoração completa, single source of truth
2. **TF-IDF In-Memory Index** - Ranking inteligente estilo Google
3. **Smart Overlay** - Sugestões + preview em tempo real no dropdown
4. **Autocomplete** - Prefixo/substring, 0.19ms latência
5. **Dicionário expandido** - 96 correções, 149 sinônimos, 50 prioritários
6. **297 testes automatizados** - 2 suites, 100% aprovação
7. **CSS fix overlay** - Corrigido clipping por overflow-x:hidden
8. **Responsivo completo** - Overlay adaptado para 768px, 480px, 360px
9. **SQL injection fixes** - ORDER BY, LIMIT, OFFSET parametrizados
10. **SSH hardening** - Porta custom, chave SSH obrigatória, Fail2Ban, UFW
11. **Monitoramento** - Script automático (RAM + uptime) a cada 5min com alertas por email
12. **Backup automático** - DB + .env diário com retenção de 7 dias
13. **Deploy produção** - https://multasgo.com.br

### **v2.0:**
- Sistema "Você Quis Dizer" com destaque visual
- Correção ortográfica nativa (substituiu RapidFuzz)
- Cache inteligente com limite de memória
- Segurança anti-bot avançada
- Cards expansíveis, monitoramento completo

## 📞 **Suporte e Contato**

- **Produção:** https://multasgo.com.br
- **Documentação API:** https://multasgo.com.br/docs (Swagger UI)
- **Dev local:** http://localhost:8080

## 📄 **Licença**

Este projeto está licenciado sob a licença MIT - Sistema otimizado para consulta de infrações de trânsito brasileiro.

---

**Produção:** https://multasgo.com.br
