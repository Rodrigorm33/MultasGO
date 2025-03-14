Write-Host "Truncando tabela bdbautos..."
railway run "echo 'TRUNCATE TABLE bdbautos;' | psql $DATABASE_URL"

Write-Host "Criando tabela temporária..."
$create_temp = @"
CREATE TEMP TABLE temp_bdbautos (
  "Código de Infração" text,
  "Infração" text,
  "Responsável" text,
  "Valor da Multa" text,
  "Órgão Autuador" text,
  "Artigos do CTB" text,
  "pontos" text,
  "gravidade" text
);
"@

railway run "echo '$create_temp' | psql $DATABASE_URL"

Write-Host "Copiando CSV para tabela temporária..."
Get-Content .\dbautos.csv | railway run "cat > /tmp/dbautos.csv"

$copy_cmd = @"
\COPY temp_bdbautos FROM '/tmp/dbautos.csv' WITH DELIMITER ';' CSV HEADER;
"@

railway run "echo '$copy_cmd' | psql $DATABASE_URL"

Write-Host "Inserindo dados da tabela temporária na tabela principal..."
$insert_cmd = @"
INSERT INTO bdbautos SELECT * FROM temp_bdbautos;
DROP TABLE temp_bdbautos;
"@

railway run "echo '$insert_cmd' | psql $DATABASE_URL"

Write-Host "Verificando quantidade de registros importados..."
railway run "echo 'SELECT COUNT(*) FROM bdbautos;' | psql $DATABASE_URL"

Write-Host "Importação concluída."
