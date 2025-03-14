import os
from fastapi import FastAPI, APIRouter
import psycopg2
import re
import logging
import traceback

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MultasGO-TestAPI")

# Criar uma mini API para testes
app = FastAPI(title="MultasGO-TestAPI")
router = APIRouter(prefix="/api/test")

# Encontrar a codificação correta (baseado nos resultados do script anterior)
# Substitua 'latin1' pela codificação que funcionou no teste anterior
ENCODING = 'latin1'  # Pode ser 'latin1', 'iso-8859-1', 'cp1252', etc.

@router.get("/search")
async def search_test(termo: str = ""):
    logger.info(f"Testando busca com termo: {termo}")
    
    try:
        # Conectar ao banco com a codificação correta
        DATABASE_URL = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(DATABASE_URL, client_encoding=ENCODING)
        cursor = conn.cursor()
        
        # Verificar se o termo parece um código numérico
        is_codigo = bool(re.match(r'^\d+', termo))
        
        if is_codigo:
            # Buscar por código
            logger.info(f"Buscando código: {termo}")
            query = """
            SELECT * FROM bdbautos 
            WHERE "Código de Infração" LIKE %s 
            LIMIT 10
            """
            cursor.execute(query, [f"%{termo}%"])
        else:
            # Buscar por texto
            logger.info(f"Buscando texto: {termo}")
            query = """
            SELECT * FROM bdbautos 
            WHERE "Infração" ILIKE %s 
            OR "Artigos do CTB" ILIKE %s
            OR "Responsável" ILIKE %s
            LIMIT 10
            """
            param = f"%{termo}%"
            cursor.execute(query, [param, param, param])
        
        # Processar resultados
        resultados = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description]
        
        # Formatar para JSON
        dados = []
        for row in resultados:
            item = {}
            for i, col in enumerate(colunas):
                item[col] = str(row[i])  # Converter para string para evitar problemas de codificação
            dados.append(item)
        
        logger.info(f"Encontrados {len(dados)} resultados")
        conn.close()
        
        return {
            "status": "success",
            "total": len(dados),
            "resultados": dados
        }
        
    except Exception as e:
        logger.error(f"Erro na busca: {str(e)}")
        traceback.print_exc()
        return {
            "status": "error",
            "mensagem": str(e),
            "traceback": traceback.format_exc()
        }

@router.get("/health")
async def health():
    return {"status": "ok", "message": "API de teste funcionando"}

app.include_router(router)

# Para execução local
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)