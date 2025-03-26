import os
import subprocess
import sys
import webbrowser
from dotenv import load_dotenv
import time
import threading


# Carregar variáveis de ambiente
load_dotenv()

def verificar_estrutura_pastas():
    """Verifica e cria a estrutura de pastas necessária para a aplicação."""
    import os
    
    # Caminhos importantes
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.join(base_dir, "app")
    static_dir = os.path.join(app_dir, "static")
    templates_dir = os.path.join(app_dir, "templates")
    
    # Verificar e criar diretório de templates se necessário
    if not os.path.exists(templates_dir):
        print(f"Criando diretório de templates em {templates_dir}")
        os.makedirs(templates_dir, exist_ok=True)
    
    # Verificar e criar diretório static se necessário
    if not os.path.exists(static_dir):
        print(f"Criando diretório de arquivos estáticos em {static_dir}")
        os.makedirs(static_dir, exist_ok=True)
    
    print("✅ Estrutura de diretórios verificada com sucesso!")

def iniciar_aplicacao():
    print("\n===== INICIANDO APLICAÇÃO MULTASGO =====")
    
    # Verificar estrutura de pastas
    verificar_estrutura_pastas()
    
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
    
    #desativa o autocomplete
    """
    # Inicializar e treinar o SymSpell com dados do banco
    try:
        print("Inicializando sistema de correção ortográfica e autocompletar...")
        # Inicializamos em um novo thread para não bloquear a inicialização
        import threading
        from app.db.database import get_db
        from app.services.search_service import treinar_symspell_com_banco, autocomplete_index
        
        def inicializar_servicos_pesquisa():
            try:
                print("Carregando dicionário de termos e sugestões...")
                db = next(get_db())
                # Treinar SymSpell com dados do banco
                treinar_symspell_com_banco(db)
                # Atualizar índice de autocompletar
                autocomplete_index.update_from_database(db)
                print("✅ Sistema de pesquisa inicializado com sucesso!")
            except Exception as e:
                print(f"⚠️ Aviso: Inicialização do sistema de pesquisa encontrou um erro: {e}")
                print("A aplicação continuará funcionando, mas algumas sugestões podem não estar disponíveis.")
        
        # Iniciar em um thread separado para não bloquear o inicialização
        inicializar_thread = threading.Thread(target=inicializar_servicos_pesquisa)
        inicializar_thread.daemon = True
        inicializar_thread.start()
    except Exception as e:
        print(f"⚠️ Aviso: Não foi possível inicializar o sistema de pesquisa: {e}")
        print("A aplicação continuará funcionando com recursos de pesquisa limitados.")
    """
    
    
    print("\n🚀 Iniciando o servidor MultasGO...")
    print("URL: http://localhost:8080")
    print("Pressione CTRL+C para encerrar o servidor.")
    
    # Timer para abrir o navegador após 2 segundos
    def abrir_navegador():
        time.sleep(2)
        webbrowser.open("http://localhost:8080")
    
    # Iniciar o thread para abrir o navegador
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