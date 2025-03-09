# MultasGO - API de Pesquisa de Autos de Infração de Trânsito

API para pesquisa de autos de infração de trânsito, desenvolvida com FastAPI e PostgreSQL, com suporte a busca fuzzy para lidar com erros de digitação.

## Funcionalidades

- Importação automática de dados de infrações a partir de um arquivo CSV
- Pesquisa de infrações por código (exata ou parcial)
- Pesquisa de infrações por descrição com suporte a fuzzy search (tolerante a erros de digitação)
- Documentação interativa da API com Swagger UI

## Tecnologias Utilizadas

- **FastAPI**: Framework web moderno e de alta performance
- **SQLAlchemy**: ORM para interação com o banco de dados
- **PostgreSQL**: Banco de dados relacional
- **RapidFuzz**: Biblioteca para implementação de busca fuzzy
- **Pandas**: Para manipulação e importação de dados do CSV
- **Pydantic**: Para validação de dados e definição de esquemas

## Requisitos

- Python 3.8+
- PostgreSQL

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/multas-go.git
cd multas-go
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv venv
# No Windows
venv\Scripts\activate
# No Linux/Mac
source venv/bin/activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
# Copie o arquivo de exemplo
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

## Execução

1. Inicie o servidor de desenvolvimento:
```bash
python -m app.main
```

2. Acesse a documentação da API:
```
http://localhost:8000/docs
```

## Estrutura do Projeto

```
multas-go/
├── app/
│   ├── api/
│   │   ├── endpoints/
│   │   │   ├── __init__.py
│   │   │   └── infracoes.py
│   │   ├── __init__.py
│   │   └── api.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── logger.py
│   ├── db/
│   │   ├── __init__.py
│   │   └── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── infracao.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── infracao.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── import_service.py
│   │   └── search_service.py
│   ├── __init__.py
│   └── main.py
├── dbautos.csv
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

## Endpoints da API

- `GET /api/v1/infracoes`: Lista todas as infrações
- `GET /api/v1/infracoes/{codigo}`: Obtém uma infração específica pelo código
- `GET /api/v1/infracoes/pesquisa?query={termo}`: Pesquisa infrações por código ou descrição

## Desenvolvimento

### Testes

Para executar os testes:
```bash
pytest
```

### Ambiente de Produção

Para implantação em produção, recomenda-se:

1. Configurar um servidor WSGI como Gunicorn
2. Utilizar um proxy reverso como Nginx
3. Configurar variáveis de ambiente adequadas para produção
4. Utilizar um serviço de banco de dados gerenciado

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para mais detalhes.

## Contato

Para dúvidas ou sugestões, entre em contato através do email: seu-email@exemplo.com

## Backup do Sistema

Para garantir a segurança dos dados e do código do MultasGO, foram criados scripts de backup:

1. **backup_app.py**: Script Python que cria um arquivo ZIP contendo todos os arquivos importantes do sistema.
   - Salva o backup na pasta `MultasGO_Backups` no Desktop do usuário
   - Inclui nome do arquivo com data e hora da criação
   - Exclui arquivos temporários como `__pycache__` e `.pyc`

2. **backup_multas_go.bat**: Arquivo batch para facilitar a execução do backup no Windows.
   - Basta clicar duas vezes neste arquivo para iniciar o processo de backup

Para executar o backup manualmente:
```
python backup_app.py
```

Os backups são salvos em: `C:\Users\[seu-usuario]\Desktop\MultasGO_Backups\` 