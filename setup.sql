-- Create infracoes table
CREATE TABLE IF NOT EXISTS infracoes (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) NOT NULL,
    descricao TEXT NOT NULL,
    valor DECIMAL(10, 2) NOT NULL,
    pontos INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Check if infracoes table is empty
DO $$
BEGIN
    IF (SELECT COUNT(*) FROM infracoes) = 0 THEN
        -- Insert sample data
        INSERT INTO infracoes (codigo, descricao, valor, pontos) VALUES
        ('A01', 'Estacionar em local proibido', 293.47, 5),
        ('A02', 'Avancar sinal vermelho', 293.47, 7),
        ('A03', 'Dirigir sem cinto de seguranca', 293.47, 5),
        ('A04', 'Excesso de velocidade ate 20%', 130.16, 4),
        ('A05', 'Excesso de velocidade entre 20% e 50%', 195.23, 5),
        ('A06', 'Excesso de velocidade acima de 50%', 880.41, 7),
        ('A07', 'Dirigir sob influencia de alcool', 2934.70, 7),
        ('A08', 'Dirigir sem habilitacao', 880.41, 7),
        ('A09', 'Usar celular ao dirigir', 293.47, 5),
        ('A10', 'Parar sobre a faixa de pedestres', 293.47, 5);
        
        RAISE NOTICE 'Sample data inserted into infracoes table';
    ELSE
        RAISE NOTICE 'infracoes table already has data, no data inserted';
    END IF;
END $$;

-- Create autos table
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_autos_placa ON autos(placa);
CREATE INDEX IF NOT EXISTS idx_autos_data_infracao ON autos(data_infracao);
CREATE INDEX IF NOT EXISTS idx_autos_status ON autos(status);

-- Check tables
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

-- Count records
SELECT 'infracoes' AS table_name, COUNT(*) AS record_count FROM infracoes
UNION ALL
SELECT 'autos' AS table_name, COUNT(*) AS record_count FROM autos; 