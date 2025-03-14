import pandas as pd
import os

def gerar_sql_para_importacao(csv_path, encoding='cp1252', delimiter=';'):
    print('=== GERANDO SCRIPT SQL PARA IMPORTAÇÃO ===')
    try:
        # Ler o arquivo CSV com delimitador ponto e vírgula
        print(f"Lendo arquivo CSV: {csv_path} (delimitador: '{delimiter}')")
        df = pd.read_csv(csv_path, encoding=encoding, delimiter=delimiter)
        print(f"Registros no arquivo CSV: {len(df)}")
        print(f"Colunas detectadas: {df.columns.tolist()}")
        
        # Nome da tabela
        table_name = 'bdbautos'
        
        # Gerar arquivo SQL
        sql_filename = 'importar_dados.sql'
        with open(sql_filename, 'w', encoding='utf-8') as f:
            # Comando para limpar a tabela
            f.write(f"-- Limpar tabela existente\n")
            f.write(f"TRUNCATE TABLE {table_name};\n\n")
            
            # Comando para iniciar transação
            f.write(f"-- Iniciar transação\n")
            f.write(f"BEGIN;\n\n")
            
            # Inserir registros
            f.write(f"-- Inserir dados\n")
            
            # Inserir cada linha
            for i, row in df.iterrows():
                # Construir comando INSERT
                columns = ', '.join([f'"{col}"' for col in df.columns])
                values = []
                
                for val in row:
                    if pd.isna(val):
                        values.append('NULL')
                    elif isinstance(val, (int, float)):
                        values.append(str(val))
                    else:
                        # Escapar aspas simples em strings
                        val_str = str(val).replace("'", "''")
                        values.append(f"'{val_str}'")
                
                values_str = ', '.join(values)
                insert_cmd = f"INSERT INTO {table_name} ({columns}) VALUES ({values_str});\n"
                f.write(insert_cmd)
            
            # Commit da transação
            f.write(f"\n-- Commit da transação\n")
            f.write(f"COMMIT;\n")
        
        print(f"Script SQL gerado com sucesso: {sql_filename}")
        print(f"Total de {len(df)} registros no arquivo SQL")
        print("\nInstruções para importar:")
        print("1. Acesse o console do Railway")
        print("2. Vá para o serviço Postgres")
        print("3. Clique em 'Data' e depois no botão de console SQL")
        print("4. Copie e cole o conteúdo do arquivo gerado ou carregue o arquivo")
        print("5. Execute o script SQL")
        
        return True, f"Script SQL gerado com sucesso: {sql_filename}"
    
    except Exception as e:
        print(f"Erro ao gerar script SQL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, f"Erro ao gerar script SQL: {str(e)}"

if __name__ == "__main__":
    # Caminho do arquivo CSV relativo à raiz do projeto
    csv_path = "dbautos.csv"
    
    # Verificar se o arquivo existe
    if not os.path.exists(csv_path):
        print(f"Erro: Arquivo {csv_path} não encontrado!")
    else:
        # Gerar script SQL com delimitador ponto e vírgula
        success, message = gerar_sql_para_importacao(csv_path, delimiter=';')
        
        if success:
            print("\n✅ " + message)
        else:
            print("\n❌ " + message)
    
    print('=== FIM DA GERAÇÃO ===')