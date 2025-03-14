import os

def preparar_sql_para_cli():
    # Ler o arquivo SQL
    with open('importar_dados.sql', 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Criar um arquivo temporário com apenas o SQL
    with open('temp_import.sql', 'w', encoding='utf-8') as f:
        f.write(sql_content)
    
    # Criar um arquivo PowerShell
    with open('executar_sql.ps1', 'w', encoding='utf-8') as f:
        f.write('Write-Host "Executando script SQL para importar dados..."\n')
        f.write('$sql = Get-Content -Raw -Path "temp_import.sql"\n')
        f.write('$sql | railway run bash -c "cat > /tmp/import.sql && psql $DATABASE_URL -f /tmp/import.sql"\n')
        f.write('Write-Host "Importação concluída."\n')
    
    print("Arquivo PowerShell criado: executar_sql.ps1")
    print("Execute-o para importar os dados.")

preparar_sql_para_cli()