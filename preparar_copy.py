import os

def preparar_copy_comando():
    # Criar um arquivo para o comando COPY
    with open('importar_copy.ps1', 'w', encoding='utf-8') as f:
        f.write('Write-Host "Truncando tabela bdbautos..."\n')
        f.write('railway run "echo \'TRUNCATE TABLE bdbautos;\' | psql $DATABASE_URL"\n\n')
        
        f.write('Write-Host "Criando tabela temporária..."\n')
        f.write('$create_temp = @"\n')
        f.write('CREATE TEMP TABLE temp_bdbautos (\n')
        f.write('  "Código de Infração" text,\n')
        f.write('  "Infração" text,\n')
        f.write('  "Responsável" text,\n')
        f.write('  "Valor da Multa" text,\n')
        f.write('  "Órgão Autuador" text,\n')
        f.write('  "Artigos do CTB" text,\n')
        f.write('  "pontos" text,\n')
        f.write('  "gravidade" text\n')
        f.write(');\n')
        f.write('"@\n\n')
        
        f.write('railway run "echo \'$create_temp\' | psql $DATABASE_URL"\n\n')
        
        f.write('Write-Host "Copiando CSV para tabela temporária..."\n')
        f.write('Get-Content .\\dbautos.csv | railway run "cat > /tmp/dbautos.csv"\n\n')
        
        f.write('$copy_cmd = @"\n')
        f.write('\\COPY temp_bdbautos FROM \'/tmp/dbautos.csv\' WITH DELIMITER \';\' CSV HEADER;\n')
        f.write('"@\n\n')
        
        f.write('railway run "echo \'$copy_cmd\' | psql $DATABASE_URL"\n\n')
        
        f.write('Write-Host "Inserindo dados da tabela temporária na tabela principal..."\n')
        f.write('$insert_cmd = @"\n')
        f.write('INSERT INTO bdbautos SELECT * FROM temp_bdbautos;\n')
        f.write('DROP TABLE temp_bdbautos;\n')
        f.write('"@\n\n')
        
        f.write('railway run "echo \'$insert_cmd\' | psql $DATABASE_URL"\n\n')
        
        f.write('Write-Host "Verificando quantidade de registros importados..."\n')
        f.write('railway run "echo \'SELECT COUNT(*) FROM bdbautos;\' | psql $DATABASE_URL"\n\n')
        
        f.write('Write-Host "Importação concluída."\n')
    
    print("Arquivo para importação COPY criado: importar_copy.ps1")
    print("Execute-o abrindo o PowerShell e digitando: .\\importar_copy.ps1")

preparar_copy_comando()