# MultasGO - Configuração do Banco de Dados no Railway

Este guia contém instruções para configurar o banco de dados PostgreSQL no Railway para a aplicação MultasGO.

## Pré-requisitos

- Conta no Railway (https://railway.app)
- Projeto MultasGO já criado no Railway
- Banco de dados PostgreSQL já criado e conectado ao serviço MultasGO

## Verificando a Conexão

Antes de prosseguir, verifique se o banco de dados PostgreSQL está corretamente conectado ao serviço MultasGO:

1. No painel do Railway, você deve ver uma seta conectando o serviço PostgreSQL ao serviço MultasGO
2. Nas variáveis de ambiente do serviço MultasGO, você deve ver as variáveis do PostgreSQL compartilhadas:
   - `DATABASE_URL`
   - `PGHOST`
   - `PGPORT`
   - `PGUSER`
   - `PGPASSWORD`
   - `PGDATABASE`

## Configurando o Banco de Dados

### No Windows (PowerShell)

```powershell
# Testar a conexão com o banco de dados
python test_db_connection.py

# Criar as tabelas no banco de dados
python create_tables.py

# Verificar se as tabelas foram criadas corretamente
python test_db_connection.py
```

### No Linux/Mac (Bash)

```bash
# Tornar o script executável
chmod +x setup_database.sh

# Executar o script de configuração
./setup_database.sh
```

## Estrutura do Banco de Dados

O script `create_tables.py` criará as seguintes tabelas:

### Tabela `infracoes`

Armazena informações sobre os tipos de infrações de trânsito.

| Campo     | Tipo          | Descrição                           |
|-----------|---------------|-------------------------------------|
| id        | SERIAL        | Identificador único da infração     |
| codigo    | VARCHAR(10)   | Código da infração                  |
| descricao | TEXT          | Descrição da infração               |
| valor     | DECIMAL(10,2) | Valor da multa em reais             |
| pontos    | INTEGER       | Pontos na carteira                  |

### Tabela `autos`

Armazena os autos de infração registrados.

| Campo          | Tipo          | Descrição                                |
|----------------|---------------|------------------------------------------|
| id             | SERIAL        | Identificador único do auto              |
| placa          | VARCHAR(8)    | Placa do veículo                         |
| data_infracao  | TIMESTAMP     | Data e hora da infração                  |
| local_infracao | TEXT          | Local onde ocorreu a infração            |
| infracao_id    | INTEGER       | Referência à tabela de infrações         |
| agente         | VARCHAR(100)  | Nome do agente que registrou a infração  |
| observacoes    | TEXT          | Observações adicionais                   |
| status         | VARCHAR(20)   | Status do auto (pendente, pago, etc.)    |
| created_at     | TIMESTAMP     | Data de criação do registro              |

## Verificação

Após executar os scripts, você pode verificar se as tabelas foram criadas corretamente executando:

```
python test_db_connection.py
```

Este script irá:
1. Testar a conexão com o banco de dados
2. Listar as tabelas existentes
3. Verificar se as tabelas necessárias (`infracoes` e `autos`) existem
4. Mostrar alguns exemplos de infrações cadastradas

## Solução de Problemas

### Erro de Conexão

Se você receber um erro de conexão, verifique:

1. Se o banco de dados PostgreSQL está em execução no Railway
2. Se as variáveis de ambiente estão corretamente configuradas
3. Se o serviço MultasGO tem acesso às variáveis do PostgreSQL

### Tabelas Não Criadas

Se as tabelas não forem criadas corretamente:

1. Verifique os logs de erro do script `create_tables.py`
2. Certifique-se de que o usuário do banco de dados tem permissões para criar tabelas
3. Tente executar o script novamente

## Suporte

Se você encontrar problemas durante a configuração, entre em contato com a equipe de suporte do MultasGO. 