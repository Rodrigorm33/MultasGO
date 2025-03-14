import psycopg2
import traceback

print('=== TESTE DE CONEXÃO COM BYTES ===')

# Parâmetros da conexão
dbname = 'railway'
user = 'postgres'
# Senha em bytes (literal, sem conversão UTF-8)
password = b'aRREuAPWwcxirWfoGysVRQfNyCfPHDYk'.decode('latin1')
host = 'postgres.railway.internal'
port = '5432'

try:
    print(f'Tentando conexão com codificação alternativa...')
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    
    print('Conexão bem-sucedida!')
    
    # Testar consulta simples
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    print(f'Consulta de teste: {result}')
    
    conn.close()
    print('Conexão fechada com sucesso!')
    
except Exception as e:
    print(f'Erro na conexão: {str(e)}')
    traceback.print_exc()

print('\n=== TESTE CONCLUÍDO ===')