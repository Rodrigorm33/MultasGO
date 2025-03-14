import os
import psycopg2
import traceback

print('=== TESTE DE CONEXÃO COM BANCO DE DADOS ===')

try:
    # Obter URL do banco e imprimir parte dela (sem mostrar senha)
    DATABASE_URL = os.getenv('DATABASE_URL')
    print(f'URL do banco encontrada. Iniciando com: {DATABASE_URL[:30]}...')
    
    # Tentar diferentes codificações
    print('\nTentando com diferentes codificações:')
    
    for encoding in ['latin1', 'iso-8859-1', 'cp1252']:
        try:
            print(f'\nTentando codificação: {encoding}')
            # Tentar conectar com diferentes opções de codificação
            conn = psycopg2.connect(DATABASE_URL, client_encoding=encoding)
            print(f'Conexão bem-sucedida com codificação {encoding}!')
            
            # Testar consulta básica
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM bdbautos")
            count = cursor.fetchone()[0]
            print(f'Total de registros na tabela: {count}')
            
            # Verificar todas as tabelas
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = cursor.fetchall()
            print(f'Tabelas disponíveis: {tables}')
            
            # Testar consulta simples
            cursor.execute('SELECT * FROM bdbautos LIMIT 1')
            columns = [desc[0] for desc in cursor.description]
            print(f'Colunas da tabela bdbautos: {columns}')
            
            conn.close()
            print(f'Conexão fechada com sucesso.')
            
            # Se chegou até aqui, encontramos uma codificação que funciona!
            encoding_ok = encoding
            break
            
        except Exception as e:
            print(f'Falha com codificação {encoding}: {str(e)}')
            traceback.print_exc()
    
except Exception as e:
    print(f'Erro geral: {str(e)}')
    traceback.print_exc()

print('\n=== TESTE CONCLUÍDO ===')