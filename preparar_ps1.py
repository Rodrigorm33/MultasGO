import os

def preparar_sql_para_powershell():
    # Criar um arquivo PowerShell
    with open('executar_sql.ps1', 'w', encoding='utf-8') as f:
        f.write('Write-Host "Executando script SQL para importar dados..."\n')
        f.write('$env:DATABASE_URL = railway run "echo $DATABASE_URL"\n')
        f.write('$query = "TRUNCATE TABLE bdbautos;"\n')
        f.write('railway run "echo \'$query\' | psql $DATABASE_URL"\n')
        
        # Adicionar os comandos INSERT em lotes menores
        with open('importar_dados.sql', 'r', encoding='utf-8') as sql_file:
            lines = sql_file.readlines()
            
            inserts = [line for line in lines if line.strip().startswith('INSERT')]
            
            f.write('Write-Host "Importando {0} registros..."\n'.format(len(inserts)))
            
            # Importar em lotes de 20 registros
            batch_size = 20
            for i in range(0, len(inserts), batch_size):
                batch = inserts[i:i+batch_size]
                batch_query = ''.join(batch).replace("'", "''")
                
                f.write('$batch_{0} = @"\n{1}"@\n'.format(i, batch_query))
                f.write('railway run "echo \'$batch_{0}\' | psql $DATABASE_URL"\n'.format(i))
                f.write('Write-Host "Processados {0} de {1} registros"\n'.format(min(i+batch_size, len(inserts)), len(inserts)))
        
        f.write('Write-Host "Importação concluída."\n')
    
    print("Arquivo PowerShell criado: executar_sql.ps1")
    print("Execute-o abrindo o PowerShell e digitando: .\\executar_sql.ps1")

preparar_sql_para_powershell()