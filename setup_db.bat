@echo off
echo Criando tabelas no banco de dados PostgreSQL...

echo Executando railway run...
railway run psql -c "CREATE TABLE IF NOT EXISTS infracoes (id SERIAL PRIMARY KEY, codigo VARCHAR(10) NOT NULL, descricao TEXT NOT NULL, valor DECIMAL(10, 2) NOT NULL, pontos INTEGER NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"

echo Inserindo dados na tabela infracoes...
railway run psql -c "INSERT INTO infracoes (codigo, descricao, valor, pontos) SELECT 'A01', 'Estacionar em local proibido', 293.47, 5 WHERE NOT EXISTS (SELECT 1 FROM infracoes WHERE codigo = 'A01')"
railway run psql -c "INSERT INTO infracoes (codigo, descricao, valor, pontos) SELECT 'A02', 'Avancar sinal vermelho', 293.47, 7 WHERE NOT EXISTS (SELECT 1 FROM infracoes WHERE codigo = 'A02')"
railway run psql -c "INSERT INTO infracoes (codigo, descricao, valor, pontos) SELECT 'A03', 'Dirigir sem cinto de seguranca', 293.47, 5 WHERE NOT EXISTS (SELECT 1 FROM infracoes WHERE codigo = 'A03')"
railway run psql -c "INSERT INTO infracoes (codigo, descricao, valor, pontos) SELECT 'A04', 'Excesso de velocidade ate 20%', 130.16, 4 WHERE NOT EXISTS (SELECT 1 FROM infracoes WHERE codigo = 'A04')"
railway run psql -c "INSERT INTO infracoes (codigo, descricao, valor, pontos) SELECT 'A05', 'Excesso de velocidade entre 20% e 50%', 195.23, 5 WHERE NOT EXISTS (SELECT 1 FROM infracoes WHERE codigo = 'A05')"
railway run psql -c "INSERT INTO infracoes (codigo, descricao, valor, pontos) SELECT 'A06', 'Excesso de velocidade acima de 50%', 880.41, 7 WHERE NOT EXISTS (SELECT 1 FROM infracoes WHERE codigo = 'A06')"
railway run psql -c "INSERT INTO infracoes (codigo, descricao, valor, pontos) SELECT 'A07', 'Dirigir sob influencia de alcool', 2934.70, 7 WHERE NOT EXISTS (SELECT 1 FROM infracoes WHERE codigo = 'A07')"
railway run psql -c "INSERT INTO infracoes (codigo, descricao, valor, pontos) SELECT 'A08', 'Dirigir sem habilitacao', 880.41, 7 WHERE NOT EXISTS (SELECT 1 FROM infracoes WHERE codigo = 'A08')"
railway run psql -c "INSERT INTO infracoes (codigo, descricao, valor, pontos) SELECT 'A09', 'Usar celular ao dirigir', 293.47, 5 WHERE NOT EXISTS (SELECT 1 FROM infracoes WHERE codigo = 'A09')"
railway run psql -c "INSERT INTO infracoes (codigo, descricao, valor, pontos) SELECT 'A10', 'Parar sobre a faixa de pedestres', 293.47, 5 WHERE NOT EXISTS (SELECT 1 FROM infracoes WHERE codigo = 'A10')"

echo Criando tabela autos...
railway run psql -c "CREATE TABLE IF NOT EXISTS autos (id SERIAL PRIMARY KEY, placa VARCHAR(8) NOT NULL, data_infracao TIMESTAMP NOT NULL, local_infracao TEXT NOT NULL, infracao_id INTEGER REFERENCES infracoes(id), agente VARCHAR(100) NOT NULL, observacoes TEXT, status VARCHAR(20) DEFAULT 'pendente', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"

echo Criando indices...
railway run psql -c "CREATE INDEX IF NOT EXISTS idx_autos_placa ON autos(placa)"
railway run psql -c "CREATE INDEX IF NOT EXISTS idx_autos_data_infracao ON autos(data_infracao)"
railway run psql -c "CREATE INDEX IF NOT EXISTS idx_autos_status ON autos(status)"

echo Verificando tabelas...
railway run psql -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"

echo Contando registros...
railway run psql -c "SELECT 'infracoes' AS tabela, COUNT(*) AS total FROM infracoes UNION ALL SELECT 'autos' AS tabela, COUNT(*) AS total FROM autos"

echo Processo concluido! 