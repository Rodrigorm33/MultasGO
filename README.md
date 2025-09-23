# MultasGO - Sistema de Pesquisa de Infrações de Trânsito

<img width="1004" height="686" alt="image" src="https://github.com/user-attachments/assets/e686d346-d7f9-4a66-927d-2ca291c39406" />

Sistema web para consulta de autos de infração de trânsito brasileiro com busca inteligente e correção ortográfica.

## Funcionalidades

### Busca Avançada
- Pesquisa por código de infração ou texto livre
- Correção ortográfica automática
- Sistema de sugestões "você quis dizer"
- Busca por sinônimos contextuais
- Validação de entrada em tempo real

### Interface
- Design responsivo
- Cards interativos com detalhes expansíveis
- Destaque visual dos termos pesquisados
- Validação educativa para entradas inválidas

### Performance
- Cache inteligente com gerenciamento de memória
- Warm-up automático para consultas rápidas
- Pool de conexões HTTP reutilizáveis
- Monitor de performance integrado

### Segurança
- Proteção anti-bot com detecção de User-Agents
- Bloqueio de IPs de alto risco
- CAPTCHA matemático para acessos suspeitos
- Rate limiting (100 requests/min por IP)
- Validação contra SQL injection e XSS

## Instalação

### Pré-requisitos
Por segurança, este repositório não inclui:
- Banco de dados (.gitignore)
- Arquivos CSV com dados (.gitignore)
- Configurações .env (.gitignore)

### Configuração
1. Obtenha o CSV de infrações do CTB
2. Renomeie para `BANCODADOS_LIMPO.csv` e coloque na raiz do projeto
3. Execute:

```bash
python start.py
```

O sistema irá automaticamente:
- Criar o banco de dados
- Importar os dados do CSV
- Instalar dependências necessárias
- Inicializar cache e warm-up
- Abrir o navegador em http://localhost:8080

## Tecnologias

**Backend:**
- FastAPI (framework async)
- SQLite/PostgreSQL (banco de dados)
- Pydantic (validação de dados)

**Frontend:**
- HTML5/CSS3 responsivo
- JavaScript ES6+
- Font Awesome (ícones)

**Sistemas Internos:**
- SpellCorrector (correção ortográfica)
- SuggestionEngine (sistema de sugestões)
- SmartCache (cache com TTL)
- PerformanceMonitor (monitoramento)
- GeoSecurityMiddleware (proteção geográfica)

## API Endpoints

### Pesquisa Básica
```
GET /api/v1/infracoes/pesquisa?q={termo}
```

### Explorador
```
GET /api/v1/infracoes/explorador?skip=0&limit=10
```

### Pesquisa Avançada
```
POST /api/v1/infracoes/explorador
{
  "gravidade": "Gravissima",
  "pontos_min": 5,
  "busca": "velocidade"
}
```

## Configuração Avançada

Arquivo `.env` (opcional):
```
MAX_CACHE_MEMORY_MB=100
CACHE_CLEANUP_INTERVAL=1800
HTTP_POOL_CONNECTIONS=10
RATE_LIMIT_REQUESTS=100
BLOCK_DURATION=300
PORT=8080
```

## Monitoramento

- **Swagger UI:** http://localhost:8080/docs
- **Métricas:** http://localhost:8080/debug/metrics
- **Segurança:** http://localhost:8080/debug/security-stats

## Estrutura do Projeto

```
MultasGO/
├── app/
│   ├── api/endpoints/         # Endpoints da API
│   ├── core/                  # Sistemas internos
│   ├── db/                    # Configuração do banco
│   ├── middleware/            # Middlewares de segurança
│   ├── schemas/               # Schemas Pydantic
│   ├── services/              # Lógica de negócio
│   ├── static/                # Arquivos CSS/JS
│   └── templates/             # Templates HTML
├── start.py                   # Script de inicialização
└── requirements.txt           # Dependências Python
```

## Comandos de Desenvolvimento

```bash
# Inicialização completa
python start.py

# Apenas FastAPI (desenvolvimento)
python -m app.main

# Testar conexão com banco
python testar_conexao.py

# Testar funcionalidades de busca
python teste_busca_simples.py
python teste_melhorias_busca.py
```

## Licença

MIT License - Uso livre para consultas ao Código de Trânsito Brasileiro.
