import os
import psycopg2

print('=== LISTAGEM DA TABELA BDBAUTOS ===')

try:
    # Conectar ao banco de dados
    DATABASE_URL = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Contar total de registros
    cursor.execute("SELECT COUNT(*) FROM bdbautos")
    total = cursor.fetchone()[0]
    print(f"Total de registros na tabela: {total}")
    
    # Listar colunas
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'bdbautos'")
    colunas = [col[0] for col in cursor.fetchall()]
    print(f"Colunas da tabela: {colunas}")
    
    # Verificar se os códigos específicos existem
    codigos_teste = ['7579', '7579-0', '54870', '5010']
    for codigo in codigos_teste:
        cursor.execute(f"SELECT COUNT(*) FROM bdbautos WHERE \"Código de Infração\"::text = %s", [codigo])
        count = cursor.fetchone()[0]
        print(f"Registros com código '{codigo}': {count}")
    
    # Verificar se os termos específicos existem
    termos_teste = ['chinelo', 'recusa', 'estacionar']
    for termo in termos_teste:
        cursor.execute(f"SELECT COUNT(*) FROM bdbautos WHERE \"Infração\" ILIKE %s OR \"Artigos do CTB\" ILIKE %s OR \"Responsável\" ILIKE %s", 
                      [f'%{termo}%', f'%{termo}%', f'%{termo}%'])
        count = cursor.fetchone()[0]
        print(f"Registros com termo '{termo}': {count}")
    
    # Listar alguns registros para exemplo
    print("\nExemplos de registros (primeiros 10):")
    cursor.execute("SELECT * FROM bdbautos LIMIT 10")
    registros = cursor.fetchall()
    for i, registro in enumerate(registros):
        print(f"Registro #{i+1}:")
        for j, coluna in enumerate(colunas):
            print(f"  {coluna}: {registro[j]}")
    
    # Fechar conexão
    conn.close()
    
except Exception as e:
    print(f"Erro ao acessar o banco de dados: {str(e)}")

print('=== FIM DA LISTAGEM ===')