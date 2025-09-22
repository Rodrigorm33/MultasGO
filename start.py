#!/usr/bin/env python3
"""
Script simplificado para iniciar o servidor MultasGO
Uso: python start.py [--dev|--prod] [--port 8080]
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path

def setup_environment():
    """Configura o ambiente para execução."""
    # Verificar se está no diretório correto
    if not os.path.exists("app/main.py"):
        print("ERRO: Execute este script no diretorio raiz do projeto MultasGO")
        sys.exit(1)

    # Verificar se o ambiente virtual existe
    venv_paths = ["venv", ".venv", "env", ".env"]
    venv_path = None

    for path in venv_paths:
        if os.path.exists(path):
            venv_path = path
            break

    if venv_path:
        print(f"OK Ambiente virtual encontrado: {venv_path}")
    else:
        print("AVISO: Ambiente virtual nao encontrado. Criando...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        venv_path = "venv"
        print("OK Ambiente virtual criado")

    return venv_path

def install_dependencies(venv_path):
    """Instala dependências se necessário."""
    pip_path = os.path.join(venv_path, "Scripts", "pip.exe") if os.name == 'nt' else os.path.join(venv_path, "bin", "pip")

    # Verificar se FastAPI está instalado
    try:
        import fastapi
        print("OK Dependencias ja instaladas")
        return
    except ImportError:
        pass

    print("Instalando dependencias...")
    requirements = [
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "sqlalchemy>=2.0.0",
        "unidecode>=1.3.0",
        "rapidfuzz>=3.5.2",
        "pydantic>=2.5.0",
        "python-multipart>=0.0.6",
        "python-dotenv>=1.0.0",
        "jinja2>=3.1.0",
        "requests>=2.31.0"
    ]

    for req in requirements:
        try:
            subprocess.run([pip_path, "install", req], check=True, capture_output=True)
            print(f"OK {req.split('>=')[0]} instalado")
        except subprocess.CalledProcessError as e:
            print(f"ERRO ao instalar {req}: {e}")

def create_env_file():
    """Cria arquivo .env se não existir."""
    if os.path.exists(".env"):
        return

    print("Criando arquivo .env...")
    env_content = """# Configurações do MultasGO
DEBUG=True
PROJECT_NAME=MultasGO
PROJECT_VERSION=1.0.0
PORT=8080
LOG_LEVEL=INFO

# Banco de dados (padrão SQLite local)
DATABASE_URL=sqlite:///./multasgo.db

# Segurança (gere uma chave segura para produção)
SECRET_KEY=dev_temp_key_apenas_para_desenvolvimento

# CORS (configure domínios específicos em produção)
CORS_ORIGINS=*
ALLOWED_HOSTS=localhost,127.0.0.1,*.cfargotunnel.com

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
BLOCK_DURATION=300
ENABLE_BOT_PROTECTION=True

# Performance
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
CACHE_TTL=300
WORKERS=1

# SSL para produção (opcional)
# SSL_CERTFILE=/path/to/cert.pem
# SSL_KEYFILE=/path/to/key.pem
"""

    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)

    print("OK Arquivo .env criado")

def start_server(mode="dev", port=8080):
    """Inicia o servidor."""
    # Configurar variáveis de ambiente baseadas no modo
    env = os.environ.copy()

    if mode == "prod":
        env.update({
            "DEBUG": "False",
            "LOG_LEVEL": "WARNING",
            "WORKERS": str(max(1, os.cpu_count() - 1)),
        })
        print("Iniciando em modo PRODUCAO")
    else:
        env.update({
            "DEBUG": "True",
            "LOG_LEVEL": "INFO",
            "WORKERS": "1",
        })
        print("Iniciando em modo DESENVOLVIMENTO")

    env["PORT"] = str(port)

    print(f"Servidor sera iniciado na porta {port}")
    print(f"Acesse: http://localhost:{port}")
    print("Pressione Ctrl+C para parar")
    print("-" * 50)

    # Iniciar servidor
    try:
        subprocess.run([
            sys.executable, "-m", "app.main"
        ], env=env, check=True)
    except KeyboardInterrupt:
        print("\nServidor parado pelo usuario")
    except subprocess.CalledProcessError as e:
        print(f"ERRO ao iniciar servidor: {e}")
        sys.exit(1)

def main():
    """Função principal."""
    parser = argparse.ArgumentParser(description="Inicia o servidor MultasGO")
    parser.add_argument("--dev", action="store_true", help="Modo desenvolvimento (padrão)")
    parser.add_argument("--prod", action="store_true", help="Modo produção")
    parser.add_argument("--port", type=int, default=8080, help="Porta do servidor (padrão: 8080)")
    parser.add_argument("--setup-only", action="store_true", help="Apenas configurar ambiente")

    args = parser.parse_args()

    print("MultasGO - Inicializador")
    print("=" * 30)

    # Configurar ambiente
    venv_path = setup_environment()
    install_dependencies(venv_path)
    create_env_file()

    if args.setup_only:
        print("OK Ambiente configurado com sucesso!")
        print("Execute 'python start.py' para iniciar o servidor")
        return

    # Determinar modo
    mode = "prod" if args.prod else "dev"

    # Iniciar servidor
    start_server(mode, args.port)

if __name__ == "__main__":
    main()