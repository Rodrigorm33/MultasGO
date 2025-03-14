import os
import psycopg2
import pandas as pd
from sqlalchemy import create_engine

def get_connection_params():
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Extrair partes da URL
    if '@' in DATABASE_URL:
        host_part = DATABASE_URL.split('@')[1]
        host = host_part.split('/')[0]
        if ':' in host:
            host = host.split(':')[0]
    else:
        host = 'localhost'
    
    if '/' in DATABASE_URL:
        parts = DATABASE_URL.split('/')
        dbname = parts[-1]
    else:
        dbname = 'postgres'
    
    if '//' in DATABASE_URL and '@' in DATABASE_URL:
        user_pass = DATABASE_URL.split('//')[1].split('@')[0]
        if ':' in user_pass:
            user = user_pass.split(':')[0]
            password = user_pass.split(':')[1]
        else:
            user = user_pass
            password = ''
    else:
        user = 'postgres'
        password = ''
    
    port = '5432'
    if '@' in DATABASE_URL and ':' in DATABASE_URL.split('@')[1]:
        port_part = DATABASE_URL.split('@')[1].split('/')[0]
        if ':' in port_part:
            port = port_part.split(':')[1]
    
    return {
        'dbname': dbname,
        'user': user,
        'password': password,
        'host': host,
        'port': port
    }

def importar_csv_para_banco(csv_path, encoding='cp1252'):
    print('=== IMPORTAÇÃO DE DADOS PARA O BANCO ===')
    try:
        # Obter parâmetros de conexão
        params = get_connection_params()
        print(f"Conectando ao banco de dados: {params['host']}/{params['dbname']}")
        
        # Conectar ao banco usando parâmetros extraídos
        conn = psycopg2.connect(
            dbname=params['dbname'],
            user=params['user'],
            password=params['password'],
            host=params['host'],
            port=params['port']
        )
        cursor = conn.cursor()
        
        # Verificar se a tabela já existe e contar registros
        cursor.execute("SELECT COUNT(*) FROM bdbautos")
        count_before = cursor.fetchone()[0]
        print(f"Registros na tabela antes da importação: {count_before}")
        
        # Ler arquivo CSV com encoding correto
        print(f"Lendo arquivo CSV: {csv_path} com encoding {encoding}")
        df = pd.read_csv(csv_path, encoding=encoding)
        print(f"Registros no arquivo CSV: {len(df)}")
        
        # Verificar as colunas do CSV
        print(f"Colunas do CSV: {df.columns.tolist()}")
        
        # Verificar nomes das colunas da tabela
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'bdbautos'")
        db_columns = [col[0] for col in cursor.fetchall()]
        print(f"Colunas no banco de dados: {db_columns}")
        
        # Se a tabela já tem registros, limpar para evitar duplicações
        if count_before > 0:
            print("Limpando tabela existente...")
            cursor.execute("TRUNCATE TABLE bdbautos")
            conn.commit()
        
        # Construir string de conexão para SQLAlchemy
        connection_string = f"postgresql://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{params['dbname']}"
        engine = create_engine(connection_string)
        
        # Ajustar nomes das colunas do CSV para corresponder ao banco de dados se necessário
        column_mapping = {}
        for col in df.columns:
            # Verificar se o nome da coluna precisa ser ajustado
            if col not in db_columns and col.lower() in [c.lower() for c in db_columns]:
                # Encontrar o nome da coluna no banco de dados (ignorando maiúsculas/minúsculas)
                for db_col in db_columns:
                    if db_col.lower() == col.lower():
                        column_mapping[col] = db_col
                        break
        
        if column_mapping:
            print(f"Mapeamento de colunas: {column_mapping}")
            df = df.rename(columns=column_mapping)
        
        # Importar dados usando pandas to_sql
        print("Importando dados do CSV para o banco...")
        df.to_sql('bdbautos', engine, if_exists='append', index=False)
        
        # Verificar se todos os registros foram importados
        cursor.execute("SELECT COUNT(*) FROM bdbautos")
        count_after = cursor.fetchone()[0]
        print(f"Registros na tabela após importação: {count_after}")
        
        print(f"Importação concluída: {count_after} registros importados")
        
        # Fechar conexões
        cursor.close()
        conn.close()
        
        return True, f"Importação bem-sucedida: {count_after} registros importados"
    
    except Exception as e:
        print(f"Erro na importação: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, f"Erro na importação: {str(e)}"

if __name__ == "__main__":
    # Caminho do arquivo CSV relativo à raiz do projeto
    csv_path = "dbautos.csv"
    
    # Verificar se o arquivo existe
    if not os.path.exists(csv_path):
        print(f"Erro: Arquivo {csv_path} não encontrado!")
    else:
        # Importar dados
        success, message = importar_csv_para_banco(csv_path)
        
        if success:
            print("\n✅ " + message)
        else:
            print("\n❌ " + message)
    
    print('=== FIM DA IMPORTAÇÃO ===')