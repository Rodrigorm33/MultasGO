# Configuração do Banco de Dados MultasGO no Railway

Este documento contém instruções para configurar o banco de dados PostgreSQL para a aplicação MultasGO no Railway.

## Pré-requisitos

1. Ter uma conta no Railway (https://railway.app)
2. Ter o CLI do Railway instalado e configurado
3. Ter o projeto MultasGO já criado no Railway com o PostgreSQL conectado

## Verificar a Conexão

A conexão entre o serviço MultasGO e o PostgreSQL deve estar configurada corretamente. Você deve ver uma seta conectando os dois serviços no painel do Railway.

## Criar as Tabelas do Banco de Dados

Existem duas maneiras de criar as tabelas necessárias:

### Opção 1: Usando o CLI do Railway (Recomendado)

1. Instale o CLI do Railway se ainda não tiver:
   ```
   npm i -g @railway/cli
   ```

2. Faça login no Railway:
   ```
   railway login
   ```

3. Vincule o CLI ao seu projeto:
   ```
   railway link
   ```

4. Execute o script de criação de tabelas:
   ```
   railway run python railway_create_tables.py
   ```

### Opção 2: Usando o Terminal do Railway

1. Acesse o painel do Railway (https://railway.app)
2. Navegue até o serviço PostgreSQL do seu projeto
3. Clique na aba "Terminal"
4. Execute os seguintes comandos SQL:

```sql
-- Criar tabela de infrações
CREATE TABLE IF NOT EXISTS infracoes (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) NOT NULL,
    descricao TEXT NOT NULL,
    valor DECIMAL(10, 2) NOT NULL,
    pontos INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir dados de exemplo
INSERT INTO infracoes (codigo, descricao, valor, pontos) VALUES
('A01', 'Estacionar em local proibido', 293.47, 5),
('A02', 'Avançar sinal vermelho', 293.47, 7),
('A03', 'Dirigir sem cinto de segurança', 293.47, 5),
('A04', 'Excesso de velocidade até 20%', 130.16, 4),
('A05', 'Excesso de velocidade entre 20% e 50%', 195.23, 5),
('A06', 'Excesso de velocidade acima de 50%', 880.41, 7),
('A07', 'Dirigir sob influência de álcool', 2934.70, 7),
('A08', 'Dirigir sem habilitação', 880.41, 7),
('A09', 'Usar celular ao dirigir', 293.47, 5),
('A10', 'Parar sobre a faixa de pedestres', 293.47, 5);

-- Criar tabela de autos de infração
CREATE TABLE IF NOT EXISTS autos (
    id SERIAL PRIMARY KEY,
    placa VARCHAR(8) NOT NULL,
    data_infracao TIMESTAMP NOT NULL,
    local_infracao TEXT NOT NULL,
    infracao_id INTEGER REFERENCES infracoes(id),
    agente VARCHAR(100) NOT NULL,
    observacoes TEXT,
    status VARCHAR(20) DEFAULT 'pendente',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Verificar se as Tabelas Foram Criadas

Para verificar se as tabelas foram criadas corretamente, você pode:

1. Usar o Terminal do Railway e executar:
   ```sql
   SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
   ```

2. Ou acessar a aba "Data" do serviço PostgreSQL no painel do Railway.

## Próximos Passos

Após criar as tabelas, você deve:

1. Reiniciar o serviço MultasGO para garantir que ele reconheça as novas tabelas
2. Testar a aplicação acessando os endpoints:
   - `/ping` - Deve retornar "pong"
   - `/health` - Deve mostrar o status do banco de dados como "connected"
   - `/check-tables` - Deve listar as tabelas criadas

## Solução de Problemas

Se encontrar problemas:

1. Verifique se as variáveis de ambiente estão configuradas corretamente
2. Certifique-se de que a conexão entre o serviço MultasGO e o PostgreSQL está estabelecida (deve haver uma seta conectando-os)
3. Verifique os logs do serviço MultasGO para identificar possíveis erros 