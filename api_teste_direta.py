from fastapi import FastAPI, Query
import psycopg2
import os
import re
import logging
import uvicorn
from typing import Optional, List, Dict, Any

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MultasGO-API-Teste")

# Criar aplicação FastAPI
app = FastAPI(title="MultasGO API de Teste")

# Função para obter conexão direta
def get_connection():
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Extrair partes da URL
    if '@' in DATABASE_URL:
        host_part = DATABASE_URL.split('@')[1]
        host = host_part.split('/')[0]
        if ':' in host:
            host = host.split(':')[0]
    else:
        host = 'localhost'
    
    if '/' in DATABASE_URL:
        parts = DATABASE_URL.split('/')
        dbname = parts[-1]
    else:
        dbname = 'postgres'
    
    if '//' in DATABASE_URL and '@' in DATABASE_URL:
        user_pass = DATABASE_URL.split('//')[1].split('@')[0]
        if ':' in user_pass:
            user = user_pass.split(':')[0]
            password = user_pass.split(':')[1]
        else:
            user = user_pass
            password = ''
    else:
        user = 'postgres'
        password = ''
    
    port = '5432'
    if '@' in DATABASE_URL and ':' in DATABASE_URL.split('@')[1]:
        port_part = DATABASE_URL.split('@')[1].split('/')[0]
        if ':' in port_part:
            port = port_part.split(':')[1]
    
    # Conectar com parâmetros extraídos
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    
    return conn

@app.get("/")
def read_root():
    return {"message": "API de teste MultasGO funcionando!"}

@app.get("/health")
def health_check():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"status": "ok", "database": "conectado"}
    except Exception as e:
        logger.error(f"Erro de conexão: {str(e)}")
        return {"status": "erro", "mensagem": str(e)}

@app.get("/busca")
def buscar_infracao(
    termo: str = Query(None, description="Termo para busca (código ou descrição)"),
    limite: int = Query(10, description="Número máximo de resultados"),
    pagina: int = Query(0, description="Página de resultados (0-based)")
):
    logger.info(f"Buscando por: '{termo}' (limite={limite}, pagina={pagina})")
    
    try:
        # Validação básica
        if not termo or len(termo.strip()) == 0:
            return {"status": "erro", "mensagem": "Termo de busca obrigatório"}
        
        # Conectar ao banco
        conn = get_connection()
        cursor = conn.cursor()
        
        # Calcular offset para paginação
        offset = pagina * limite
        
        # Verificar se o termo é um código numérico
        is_codigo = bool(re.match(r'^\d+', termo.strip()))
        
        if is_codigo:
            logger.info(f"Buscando por código: {termo}")
            query = """
            SELECT * FROM bdbautos 
            WHERE "Código de Infração" LIKE %s 
            LIMIT %s OFFSET %s
            """
            cursor.execute(query, [f"%{termo}%", limite, offset])
        else:
            logger.info(f"Buscando por texto: {termo}")
            query = """
            SELECT * FROM bdbautos 
            WHERE "Infração" ILIKE %s 
            OR "Artigos do CTB" ILIKE %s
            OR "Responsável" ILIKE %s
            LIMIT %s OFFSET %s
            """
            param = f"%{termo}%"
            cursor.execute(query, [param, param, param, limite, offset])
        
        # Processar resultados
        resultados = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description]
        
        # Formatar dados
        dados = []
        for row in resultados:
            item = {}
            for i, col in enumerate(colunas):
                if row[i] is not None:
                    item[col] = str(row[i])
                else:
                    item[col] = None
            dados.append(item)
        
        conn.close()
        logger.info(f"Encontrados {len(dados)} resultados")
        
        return {
            "status": "sucesso",
            "total": len(dados),
            "resultados": dados
        }
        
    except Exception as e:
        logger.error(f"Erro na busca: {str(e)}")
        return {
            "status": "erro",
            "mensagem": str(e)
        }

# Para execução local
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)