import os
import psycopg2
import re

print('=== DIAGNÓSTICO DO SISTEMA MULTASGO ===')

# 1. Verificar arquivos principais
try:
    print('\n1. VERIFICANDO MODELOS E ESQUEMAS')
    
    # Verificar modelo Infracao
    with open('app/models/infracao.py', 'r', encoding='utf-8') as f:
        model_content = f.read()
        print('\nModelo Infracao encontrado:')
        print(model_content[:300] + '...')  # Primeiras 300 letras
    
    # Verificar schema
    with open('app/schemas/infracao.py', 'r', encoding='utf-8') as f:
        schema_content = f.read()
        print('\nSchema Infracao encontrado:')
        print(schema_content[:300] + '...')  # Primeiras 300 letras
    
    # Verificar serviço de busca
    with open('app/services/search_service.py', 'r', encoding='utf-8') as f:
        search_content = f.read()
        print('\nServiço de busca encontrado:')
        print(search_content[:300] + '...')  # Primeiras 300 letras
except Exception as e:
    print(f'Erro ao verificar arquivos: {e}')

# 2. Testar conexão com o banco
try:
    print('\n\n2. TESTANDO CONEXÃO COM O BANCO DE DADOS')
    DATABASE_URL = os.getenv('DATABASE_URL')
    print('Conectando ao banco...')
    conn = psycopg2.connect(DATABASE_URL)
    print('Conexão bem-sucedida!')
    
    cursor = conn.cursor()
    
    # Listar tabelas
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    tables = cursor.fetchall()
    print(f'Tabelas encontradas: {tables}')
    
    # Verificar estrutura da tabela bdbautos
    print('\nEstrutura da tabela bdbautos:')
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'bdbautos'")
    columns = cursor.fetchall()
    print(f'Colunas: {[col[0] for col in columns]}')
    
    # Testar consulta simples
    print('\nTestando consulta simples:')
    cursor.execute('SELECT * FROM bdbautos LIMIT 1')
    result = cursor.fetchone()
    col_names = [desc[0] for desc in cursor.description]
    print(f'Colunas: {col_names}')
    if result:
        print('Primeiro registro encontrado!')
    
except Exception as e:
    print(f'Erro no banco de dados: {e}')

# 3. Testar função de busca
try:
    print('\n\n3. TESTANDO FUNCIONALIDADE DE BUSCA')
    
    def testar_busca(termo):
        print(f'\nPesquisando por: "{termo}"')
        
        try:
            cursor = conn.cursor()
            
            # Verificar se é código numérico
            is_codigo = bool(re.match(r'^\d+', termo))
            
            if is_codigo:
                query = 'SELECT * FROM bdbautos WHERE "Código de Infração" LIKE %s LIMIT 3'
                cursor.execute(query, [f'%{termo}%'])
            else:
                query = '''
                SELECT * FROM bdbautos 
                WHERE "Infração" ILIKE %s 
                OR "Artigos do CTB" ILIKE %s
                LIMIT 3
                '''
                cursor.execute(query, [f'%{termo}%', f'%{termo}%'])
            
            results = cursor.fetchall()
            print(f'Resultados encontrados: {len(results)}')
            
            if results:
                print('Primeiro resultado:')
                for i, val in enumerate(results[0]):
                    if i < len(col_names):
                        print(f'  {col_names[i]}: {val}')
            
            return True
        except Exception as e:
            print(f'Erro na busca: {e}')
            return False
    
    # Testar diferentes termos
    testar_busca('estacionar')
    testar_busca('54870')
    testar_busca('grave')
    testar_busca('recusa')
    
    conn.close()
    
except Exception as e:
    print(f'Erro nos testes de busca: {e}')

print('\n=== DIAGNÓSTICO CONCLUÍDO ===')