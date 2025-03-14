import os
import psycopg2
import re

print('=== TESTE DE BUSCA MULTASGO ===')

try:
    # Conectar ao banco
    DATABASE_URL = os.getenv('DATABASE_URL')
    print(f'Conectando ao banco de dados...')
    conn = psycopg2.connect(DATABASE_URL)
    print('Conexão estabelecida!')
    
    cursor = conn.cursor()
    
    # Testar busca por termo
    def testar_busca(termo):
        print(f'\nBuscando por: "{termo}"')
        
        # Detectar se é código ou texto
        is_codigo = re.match(r'^\d+', termo) is not None
        
        if is_codigo:
            print(f'Detectado como código numérico')
            query = """
            SELECT * FROM bdbautos 
            WHERE "Código de Infração" LIKE %s 
            LIMIT 5
            """
            cursor.execute(query, [f'%{termo}%'])
        else:
            print(f'Detectado como texto')
            query = """
            SELECT * FROM bdbautos 
            WHERE "Infração" ILIKE %s 
            OR "Artigos do CTB" ILIKE %s
            LIMIT 5
            """
            cursor.execute(query, [f'%{termo}%', f'%{termo}%'])
        
        resultados = cursor.fetchall()
        print(f'Resultados encontrados: {len(resultados)}')
        
        if resultados:
            col_names = [desc[0] for desc in cursor.description]
            print('\nPrimeiro resultado:')
            row = resultados[0]
            for i, val in enumerate(row):
                print(f'  {col_names[i]}: {val}')
    
    # Testar vários termos
    termos = ['estacionar', '54870', 'grave', 'recusa', 'inabilitado']
    for termo in termos:
        testar_busca(termo)
    
    conn.close()
    
except Exception as e:
    print(f'ERRO: {str(e)}')
    
print('\n=== TESTE CONCLUÍDO ===')