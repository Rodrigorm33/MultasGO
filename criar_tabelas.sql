-- Criar tabela de infrações
CREATE TABLE IF NOT EXISTS infracoes (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) NOT NULL,
    descricao TEXT NOT NULL,
    responsavel VARCHAR(50) NOT NULL,
    valor DECIMAL(10, 2) NOT NULL,
    orgao_autuador VARCHAR(100) NOT NULL,
    artigo_ctb VARCHAR(100) NOT NULL,
    pontos DECIMAL(3, 1) NOT NULL,
    gravidade VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Limpar tabela se já existir
TRUNCATE TABLE infracoes RESTART IDENTITY CASCADE;

-- Inserir dados na tabela de infrações
INSERT INTO infracoes (codigo, descricao, responsavel, valor, orgao_autuador, artigo_ctb, pontos, gravidade) VALUES
('54870', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181 * XI', 5.0, 'Grave'),
('55173', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181 * XIV', 5.0, 'Grave'),
('55330', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181 * XVI', 5.0, 'Grave'),
('55172', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181 * XIV', 5.0, 'Grave'),
('56142', 'Parar na faixa', 'Condutor', 195.23, 'Municipal/Rodoviário', '182 * V', 5.0, 'Grave'),
('54527', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181 * VIII', 5.0, 'Grave'),
('76090', 'Organizar', 'PF ou PJ', 17608.2, 'Municipal/Rodoviário', '253-A, § 1º', 7.0, 'Gravíssima 60 X'),
('54524', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181 * VIII', 5.0, 'Grave'),
('54523', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181 * VIII', 5.0, 'Grave'),
('54010', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181, III', 5.0, 'Grave'),
('54525', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181 * VIII', 5.0, 'Grave'),
('56141', 'Parar na faixa', 'Condutor', 195.23, 'Municipal/Rodoviário', '182 * V', 5.0, 'Grave'),
('53550', 'Fazer ou deixar', 'Condutor', 195.23, 'Municipal/Rodoviário', '179 * I', 5.0, 'Grave'),
('54526', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181 * VIII', 5.0, 'Grave'),
('54522', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181 * VIII', 5.0, 'Grave'),
('54950', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181 * XII', 5.0, 'Grave'),
('55680', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181 * XIX', 5.0, 'Grave'),
('55171', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181 * XIV', 5.0, 'Grave'),
('55414', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181 * XVII', 5.0, 'Grave'),
('54440', 'Estacionar', 'Condutor', 88.38, 'Municipal/Rodoviário', '181 * VII', 3.0, 'Leve'),
('55411', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181 * XVII', 5.0, 'Grave'),
('55412', 'Estacionar', 'Condutor', 195.23, 'Municipal/Rodoviário', '181 * XVII', 5.0, 'Grave');

-- Criar tabela de autos
CREATE TABLE IF NOT EXISTS bdbautos (
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

-- Criar índices para a tabela bdbautos
CREATE INDEX IF NOT EXISTS idx_bdbautos_placa ON bdbautos(placa);
CREATE INDEX IF NOT EXISTS idx_bdbautos_data_infracao ON bdbautos(data_infracao);
CREATE INDEX IF NOT EXISTS idx_bdbautos_status ON bdbautos(status);

-- Limpar tabela se já existir
TRUNCATE TABLE bdbautos RESTART IDENTITY;

-- Inserir dados de exemplo na tabela bdbautos
INSERT INTO bdbautos (placa, data_infracao, local_infracao, infracao_id, agente, observacoes, status) VALUES
('ABC1234', '2025-02-15 10:30:00', 'Avenida Paulista, 1000', 1, 'Carlos Silva', 'Veiculo estacionado em local proibido', 'pendente'),
('DEF5678', '2025-02-20 15:45:00', 'Rua Augusta, 500', 2, 'Ana Oliveira', 'Condutor sem cinto de seguranca', 'pago'),
('GHI9012', '2025-02-25 08:15:00', 'Avenida Reboucas, 750', 3, 'Roberto Santos', 'Veiculo em alta velocidade', 'em recurso'),
('JKL3456', '2025-03-01 12:00:00', 'Rua Oscar Freire, 200', 4, 'Juliana Costa', 'Ultrapassagem em local proibido', 'pendente'),
('MNO7890', '2025-03-02 17:30:00', 'Avenida Brigadeiro Faria Lima, 1500', 5, 'Marcos Pereira', 'Condutor utilizando celular', 'cancelado'); 