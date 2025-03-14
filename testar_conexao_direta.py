import os
import psycopg2
import traceback

print('=== TESTE DE CONEXÃO DIRETA ===')

try:
    # Obter URL do banco
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Exibir apenas o início da URL (por segurança)
    prefix = DATABASE_URL.split('@')[0]
    prefix_safe = prefix[:15] + '...'
    print(f'URL encontrada. Início: {prefix_safe}')
    
    # Em vez de usar a URL diretamente, vamos extrair as partes
    # Formato normal de URL do Postgres: postgresql://user:password@host:port/dbname
    
    # Tentar extrair partes da URL manualmente
    print('\nTentando extrair partes da URL manualmente...')
    try:
        # Encontrar o host
        if '@' in DATABASE_URL:
            host_part = DATABASE_URL.split('@')[1]
            host = host_part.split('/')[0]
            if ':' in host:
                host = host.split(':')[0]
            print(f'Host extraído: {host}')
        else:
            print('Não foi possível extrair o host')
            host = 'localhost'
        
        # Encontrar o banco de dados
        if '/' in DATABASE_URL:
            parts = DATABASE_URL.split('/')
            dbname = parts[-1]
            print(f'Banco de dados extraído: {dbname}')
        else:
            print('Não foi possível extrair o banco de dados')
            dbname = 'postgres'
        
        # Encontrar o usuário e senha
        if '//' in DATABASE_URL and '@' in DATABASE_URL:
            user_pass = DATABASE_URL.split('//')[1].split('@')[0]
            if ':' in user_pass:
                user = user_pass.split(':')[0]
                password = user_pass.split(':')[1]
                print(f'Usuário extraído: {user}')
                print(f'Senha extraída: {"*" * len(password)}')
            else:
                user = user_pass
                password = ''
                print(f'Usuário extraído: {user}')
                print('Senha extraída: (vazia)')
        else:
            print('Não foi possível extrair usuário e senha')
            user = 'postgres'
            password = ''
        
        # Encontrar a porta
        port = '5432'  # Porta padrão do Postgres
        if '@' in DATABASE_URL and ':' in DATABASE_URL.split('@')[1]:
            port_part = DATABASE_URL.split('@')[1].split('/')[0]
            if ':' in port_part:
                port = port_part.split(':')[1]
                print(f'Porta extraída: {port}')
        
        # Tentar conectar com os parâmetros extraídos
        print('\nTentando conectar com parâmetros extraídos...')
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )
        print('Conexão bem-sucedida!')
        
        # Testar consulta básica
        cursor = conn.cursor()
        cursor.execute("SELECT current_database(), current_user")
        db, current_user = cursor.fetchone()
        print(f'Banco atual: {db}, Usuário atual: {current_user}')
        
        # Verificar se a tabela bdbautos existe
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'bdbautos')")
        exists = cursor.fetchone()[0]
        if exists:
            print('Tabela bdbautos encontrada!')
            
            # Verificar número de registros
            cursor.execute("SELECT COUNT(*) FROM bdbautos")
            count = cursor.fetchone()[0]
            print(f'Total de registros: {count}')
            
            # Verificar colunas da tabela
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'bdbautos'")
            columns = [row[0] for row in cursor.fetchall()]
            print(f'Colunas da tabela: {columns}')
            
            # Testar consulta simples
            cursor.execute("SELECT * FROM bdbautos LIMIT 1")
            row = cursor.fetchone()
            if row:
                print('Primeiro registro recuperado com sucesso!')
        else:
            print('Tabela bdbautos NÃO encontrada!')
            
            # Listar todas as tabelas
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [row[0] for row in cursor.fetchall()]
            print(f'Tabelas disponíveis: {tables}')
        
        conn.close()
        print('Conexão fechada.')
        
    except Exception as e:
        print(f'Erro ao processar URL ou conectar: {str(e)}')
        traceback.print_exc()
    
except Exception as e:
    print(f'Erro geral: {str(e)}')
    traceback.print_exc()

print('\n=== TESTE CONCLUÍDO ===')