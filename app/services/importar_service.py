import os
import pandas as pd
from sqlalchemy import create_engine, text
import time
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('importacao.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def importar_csv_para_banco(
    csv_path="bdbautos.csv", 
    encoding="cp1252", 
    delimiter=";", 
    database_url=None
):
    """
    Importa dados do CSV para o banco de dados PostgreSQL
    
    Parâmetros:
    - csv_path: Caminho para o arquivo CSV
    - encoding: Codificação do arquivo
    - delimiter: Delimitador do CSV
    - database_url: URL de conexão com o banco de dados
    """
    start_time = time.time()
    
    try:
        # Verificar se o arquivo existe
        if not os.path.exists(csv_path):
            logger.error(f"Arquivo {csv_path} não encontrado!")
            return False, f"Arquivo {csv_path} não encontrado!"
        
        # Ler o arquivo CSV
        logger.info(f"Lendo arquivo CSV com encoding {encoding} e delimitador '{delimiter}'")
        df = pd.read_csv(csv_path, encoding=encoding, delimiter=delimiter)
        logger.info(f"Arquivo CSV lido com sucesso. Total de registros: {len(df)}")
        
        # Mapeamento correto de colunas
        column_map = {
            'Código de infração': 'Código de Infração',
            'Infração': 'Infração',
            'Responsável': 'Responsável',
            'Valor da multa': 'Valor da Multa',
            'Órgão Autuador': 'Órgão Autuador',
            'Artigos do CTB': 'Artigos do CTB',
            'Pontos': 'pontos',
            'Gravidade': 'gravidade'
        }
        
        # Renomear colunas
        df = df.rename(columns=column_map)
        
        # Tratamento da coluna Gravidade
        df['gravidade'] = df['gravidade'].str.strip().str.lower()
        
        # Mapeamento de valores para padronizar
        gravidade_map = {
            'grave': 'grave',
            'gravissima': 'gravissima',
            'gravissima60x': 'gravissima',
            'leve': 'leve'
        }
        df['gravidade'] = df['gravidade'].map(gravidade_map).fillna(df['gravidade'])
        
        # Conexão com o banco de dados
        if not database_url:
            database_url = os.getenv('DATABASE_URL', 'postgresql://usuario:senha@localhost/nomebanco')
        
        engine = create_engine(database_url)
        
        # Iniciar conexão
        with engine.connect() as connection:
            # Iniciar transação
            trans = connection.begin()
            
            try:
                # Limpar tabela existente
                logger.info("Limpando tabela bdbautos para evitar duplicações")
                connection.execute(text("TRUNCATE TABLE bdbautos"))
                
                # Inserir dados em lotes
                batch_size = 50
                total_batches = (len(df) + batch_size - 1) // batch_size
                records_inserted = 0
                
                logger.info(f"Inserindo {len(df)} registros em {total_batches} lotes")
                
                for i in range(total_batches):
                    start_idx = i * batch_size
                    end_idx = min((i + 1) * batch_size, len(df))
                    batch = df.iloc[start_idx:end_idx]
                    
                    # Preparar dados para inserção
                    insert_data = []
                    for _, row in batch.iterrows():
                        insert_data.append({
                            "codigo": str(row["Código de Infração"]),
                            "infracao": str(row["Infração"]),
                            "responsavel": str(row["Responsável"]),
                            "valor": str(row["Valor da Multa"]),
                            "orgao": str(row["Órgão Autuador"]),
                            "artigos": str(row["Artigos do CTB"]),
                            "pontos": str(row["pontos"]),
                            "gravidade": str(row["gravidade"])
                        })
                    
                    # Executar inserção em lote
                    connection.execute(
                        text("""
                        INSERT INTO bdbautos (
                            "Código de Infração", "Infração", "Responsável", 
                            "Valor da Multa", "Órgão Autuador", "Artigos do CTB", 
                            "pontos", "gravidade"
                        ) VALUES (
                            :codigo, :infracao, :responsavel, 
                            :valor, :orgao, :artigos, 
                            :pontos, :gravidade
                        )
                        """),
                        insert_data
                    )
                    
                    records_inserted += len(batch)
                    logger.info(f"Lote {i+1}/{total_batches} inserido. Total atual: {records_inserted}/{len(df)}")
                
                # Commit da transação
                trans.commit()
                
                # Verificar contagem final
                result = connection.execute(text("SELECT COUNT(*) FROM bdbautos")).scalar()
                logger.info(f"Importação concluída. Total de registros na tabela: {result}")
                
                end_time = time.time()
                duration = end_time - start_time
                logger.info(f"Tempo total de importação: {duration:.2f} segundos")
                
                return True, f"Importação concluída com sucesso. {result} registros importados em {duration:.2f} segundos."
            
            except Exception as e:
                # Rollback em caso de erro
                trans.rollback()
                logger.error(f"Erro durante a importação: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return False, f"Erro durante a importação: {str(e)}"
    
    except Exception as e:
        logger.error(f"Erro geral: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"Erro geral: {str(e)}"

# Função principal para execução direta
def main():
    # Você pode configurar o caminho do CSV e URL do banco aqui
    success, message = importar_csv_para_banco(
        csv_path='bdbautos.csv',
        database_url='postgresql://seu_usuario:sua_senha@localhost/seu_banco'
    )
    print(message)

if __name__ == "__main__":
    main()