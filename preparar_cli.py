import os

def preparar_sql_para_cli():
    # Ler o arquivo SQL
    with open('importar_dados.sql', 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Criar um arquivo para o comando da CLI
    with open('executar_sql.cmd', 'w', encoding='utf-8') as f:
        f.write('@echo off\n')
        f.write('echo Executando script SQL para importar dados...\n')
        f.write('railway run bash -c "psql $DATABASE_URL << EOF\n')
        f.write(sql_content)
        f.write('\nEOF"\n')
        f.write('echo Importação concluída.\n')
    
    print("Arquivo de comando criado: executar_sql.cmd")
    print("Execute-o para importar os dados.")

preparar_sql_para_cli()