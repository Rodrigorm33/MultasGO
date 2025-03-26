import os
import psycopg2
import time
from dotenv import load_dotenv
from app.core.config import settings

# Carregar variáveis de ambiente
load_dotenv()

def testar_conexao(max_tentativas=3, intervalo_tentativas=2):
    """
    Testa a conexão com o banco de dados PostgreSQL.
    
    Args:
        max_tentativas: Número máximo de tentativas de conexão
        intervalo_tentativas: Intervalo em segundos entre as tentativas
    
    Returns:
        bool: True se a conexão for bem-sucedida, False caso contrário
    """
    print("Testando conexão com o banco de dados PostgreSQL...")
    
    # Obter parâmetros de conexão
    host = os.getenv('PGHOST', settings.PGHOST)
    port = os.getenv('PGPORT', settings.PGPORT)
    user = os.getenv('PGUSER', settings.PGUSER)
    password = os.getenv('PGPASSWORD', settings.PGPASSWORD)
    database = os.getenv('PGDATABASE', settings.PGDATABASE)
    
    # Log de segurança (sem mostrar senha)
    print(f"Tentando conectar em: {host}:{port}, Usuário: {user}, Database: {database}")
    
    # Tentar conexão com múltiplas tentativas
    for tentativa in range(1, max_tentativas + 1):
        try:
            # Conectar ao PostgreSQL
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                connect_timeout=10
            )
            
            # Testar conexão executando uma consulta simples
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            # Fechar conexão
            conn.close()
            
            # Verificar resultado
            if result and result[0] == 1:
                print("✅ Conexão com o banco de dados estabelecida com sucesso!")
                return True
        
        except psycopg2.Error as e:
            # Formatar erro amigável para o usuário
            if "could not connect to server" in str(e) or "could not translate host name" in str(e):
                print(f"❌ Tentativa {tentativa}/{max_tentativas}: Não foi possível conectar ao servidor {host}:{port}")
            elif "password authentication failed" in str(e):
                print(f"❌ Tentativa {tentativa}/{max_tentativas}: Falha na autenticação. Verifique seu usuário e senha.")
            elif "database" in str(e) and "does not exist" in str(e):
                print(f"❌ Tentativa {tentativa}/{max_tentativas}: O banco de dados '{database}' não existe.")
            else:
                print(f"❌ Tentativa {tentativa}/{max_tentativas}: Erro ao conectar: {e}")
            
            # Se não for a última tentativa, aguardar antes de tentar novamente
            if tentativa < max_tentativas:
                print(f"Aguardando {intervalo_tentativas} segundos antes de tentar novamente...")
                time.sleep(intervalo_tentativas)
    
    # Se chegou aqui, todas as tentativas falharam
    print("\n⚠️ Não foi possível estabelecer conexão com o banco de dados após várias tentativas.")
    print("Verifique:")
    print("1. Se o servidor de banco de dados está em execução")
    print("2. Se as credenciais no arquivo .env estão corretas")
    print("3. Se existe algum firewall bloqueando a conexão")
    print("4. Se a URL do banco de dados está formatada corretamente")
    return False

if __name__ == "__main__":
    # Se o arquivo for executado diretamente, testar a conexão
    resultado = testar_conexao()
    print(f"Resultado do teste: {'Sucesso' if resultado else 'Falha'}")