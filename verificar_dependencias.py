import os
import sys

print('=== VERIFICANDO DEPENDÊNCIAS ===')
try:
    import pandas
    print(f"pandas: {pandas.__version__}")
except ImportError:
    print("pandas não está instalado")

try:
    import sqlalchemy
    print(f"sqlalchemy: {sqlalchemy.__version__}")
except ImportError:
    print("sqlalchemy não está instalado")

print('=== FIM DA VERIFICAÇÃO ===')