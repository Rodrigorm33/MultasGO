-- Script para criar as tabelas necessárias para o MultasGO
-- Execute este script no terminal do PostgreSQL no Railway

-- Criar tabela de infrações
CREATE TABLE IF NOT EXISTS infracoes (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) NOT NULL,
    descricao TEXT NOT NULL,
    valor DECIMAL(10, 2) NOT NULL,
    pontos INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Verificar se já existem dados na tabela de infrações
DO $$
BEGIN
    IF (SELECT COUNT(*) FROM infracoes) = 0 THEN
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
        
        RAISE NOTICE 'Dados de exemplo inseridos na tabela infracoes';
    ELSE
        RAISE NOTICE 'A tabela infracoes já contém dados, nenhum dado foi inserido';
    END IF;
END $$;

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

-- Criar índices para melhorar a performance
CREATE INDEX IF NOT EXISTS idx_autos_placa ON autos(placa);
CREATE INDEX IF NOT EXISTS idx_autos_data_infracao ON autos(data_infracao);
CREATE INDEX IF NOT EXISTS idx_autos_status ON autos(status);

-- Verificar as tabelas criadas
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Contar registros nas tabelas
SELECT 'infracoes' AS tabela, COUNT(*) AS total_registros FROM infracoes
UNION ALL
SELECT 'autos' AS tabela, COUNT(*) AS total_registros FROM autos;

-- Mensagem de conclusão
DO $$
BEGIN
    RAISE NOTICE 'Configuração do banco de dados concluída com sucesso!';
END $$; 