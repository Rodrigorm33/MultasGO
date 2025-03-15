import os
import subprocess
import sys
import webbrowser
from dotenv import load_dotenv
import time

# Carregar variáveis de ambiente
load_dotenv()

def iniciar_aplicacao():
    print("\n===== INICIANDO APLICAÇÃO MULTASGO =====")
    
    # Verificar conexão com o banco de dados primeiro
    print("Verificando conexão com o banco de dados...")
    try:
        # Importar o módulo de teste de conexão
        import testar_conexao
        if not testar_conexao.testar_conexao():
            print("\n❌ Não foi possível estabelecer conexão com o banco de dados.")
            print("Verifique as configurações no arquivo .env e tente novamente.")
            return
    except ImportError:
        print("Aviso: Módulo de teste de conexão não encontrado. Pulando verificação.")
    
    # Configurar variáveis de ambiente
    os.environ["PORT"] = "8080"
    
    print("\n🚀 Iniciando o servidor MultasGO...")
    print("URL: http://localhost:8080")
    print("Pressione CTRL+C para encerrar o servidor.")
    
    # Timer para abrir o navegador após 2 segundos
    def abrir_navegador():
        time.sleep(2)
        webbrowser.open("http://localhost:8080")
    
    # Iniciar o thread para abrir o navegador
    import threading
    thread = threading.Thread(target=abrir_navegador)
    thread.daemon = True
    thread.start()
    
    # Iniciar o servidor
    try:
        subprocess.run([sys.executable, "-m", "app.main"], check=True)
    except KeyboardInterrupt:
        print("\n⏹️  Servidor encerrado pelo usuário.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erro ao iniciar o servidor: {e}")
        print("Verifique os logs para mais detalhes.")

if __name__ == "__main__":
    iniciar_aplicacao()