import psycopg2
import traceback

print('=== TESTE DE CONEXÃO MANUAL ===')

# Parâmetros fixos baseados nas informações que vimos
dbname = 'railway'
user = 'postgres'
# Substitua pela senha real que você vê no Railway Dashboard
password = 'aRREuAPWWcxirWfoGysVRQHNyCfPHDYk'  # ⚠️ SUBSTITUA PELA SENHA REAL
host = 'postgres.railway.internal'
port = '5432'

try:
    print(f'Tentando conexão com host: {host}')
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    
    print('Conexão bem-sucedida!')
    
    # Testar funcionalidade básica
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