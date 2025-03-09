import pandas as pd
import os
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.infracao import Infracao
from app.core.logger import logger

def importar_csv_para_db(db: Session, csv_path: str, force_update: bool = False) -> int:
    """
    Importa os dados do arquivo CSV para o banco de dados.
    
    Args:
        db: Sessão do banco de dados
        csv_path: Caminho para o arquivo CSV
        force_update: Se True, atualiza registros existentes
        
    Returns:
        int: Número de registros importados/atualizados
    """
    try:
        # Verificar se o arquivo existe
        if not os.path.exists(csv_path):
            logger.error(f"Arquivo CSV não encontrado: {csv_path}")
            raise FileNotFoundError(f"Arquivo CSV não encontrado: {csv_path}")
        
        # Ler o arquivo CSV com tratamento para espaços extras
        logger.info(f"Iniciando importação do arquivo CSV: {csv_path}")
        
        # Lendo o arquivo com opções para lidar com espaços extras
        df = pd.read_csv(csv_path, sep=';', encoding='latin1', skipinitialspace=True)
        
        # Verificar e mostrar as colunas encontradas para debug
        logger.info(f"Colunas encontradas no CSV: {', '.join(df.columns)}")
        
        # Renomear as colunas para corresponder ao modelo
        colunas_mapeadas = {
            'Código de infração': 'codigo',
            'Infração': 'descricao',
            'Responsável': 'responsavel',
            'Valor da multa': 'valor_multa',
            'Órgão Autuador': 'orgao_autuador',
            'Artigos do CTB': 'artigos_ctb',
            'Pontos': 'pontos',
            'Gravidade': 'gravidade'
        }
        
        # Verificar se todas as colunas esperadas existem
        colunas_faltantes = [col for col in colunas_mapeadas.keys() if col not in df.columns]
        if colunas_faltantes:
            logger.warning(f"Colunas não encontradas no CSV: {', '.join(colunas_faltantes)}")
        
        # Renomear apenas as colunas que existem
        colunas_para_renomear = {k: v for k, v in colunas_mapeadas.items() if k in df.columns}
        df = df.rename(columns=colunas_para_renomear)
        
        # Limpar e converter os dados com tratamento para valores não-string
        # Converter valor_multa para string antes de aplicar replace, depois para float
        df['valor_multa'] = df['valor_multa'].astype(str).str.replace(',', '.').astype(float)
        
        # Converter pontos para numérico, tratando valores não numéricos
        df['pontos'] = pd.to_numeric(df['pontos'], errors='coerce').fillna(0).astype(int)
        
        # Tratar o campo gravidade - remover espaços extras e garantir que é string
        if 'gravidade' in df.columns:
            df['gravidade'] = df['gravidade'].astype(str).str.strip()
            logger.info(f"Coluna 'gravidade' encontrada com valores: {df['gravidade'].unique()}")
        else:
            # Tentar encontrar a coluna com espaço extra no nome
            colunas_com_gravidade = [col for col in df.columns if 'Gravidade' in col or 'gravidade' in col]
            if colunas_com_gravidade:
                logger.info(f"Encontradas colunas similares a 'gravidade': {colunas_com_gravidade}")
                # Usar a primeira coluna encontrada
                df = df.rename(columns={colunas_com_gravidade[0]: 'gravidade'})
                df['gravidade'] = df['gravidade'].astype(str).str.strip()
            else:
                # Se a coluna não existir, criar com valor padrão baseado nos pontos
                logger.warning("Coluna 'gravidade' não encontrada no CSV. Determinando gravidade pelos pontos.")
                df['gravidade'] = df['pontos'].apply(lambda p: 
                    'Gravíssima' if p >= 7 else 
                    'Grave' if p >= 5 else 
                    'Média' if p >= 4 else 
                    'Leve')
        
        # Garantir que todos os campos sejam strings para evitar problemas de tipo
        df['codigo'] = df['codigo'].astype(str).str.strip()
        df['descricao'] = df['descricao'].astype(str).str.strip()
        df['responsavel'] = df['responsavel'].astype(str).str.strip()
        df['orgao_autuador'] = df['orgao_autuador'].astype(str).str.strip()
        df['artigos_ctb'] = df['artigos_ctb'].astype(str).str.strip()
        
        # Obter todos os códigos existentes no banco para otimizar a verificação
        codigos_existentes = {}
        if force_update:
            infracoes_existentes = db.query(Infracao).all()
            codigos_existentes = {infracao.codigo: infracao for infracao in infracoes_existentes}
            logger.info(f"Encontrados {len(codigos_existentes)} registros existentes no banco.")
        
        # Inserir ou atualizar os dados no banco
        registros_importados = 0
        registros_atualizados = 0
        registros_ignorados = 0
        
        # Processar em lotes para melhor desempenho
        lote_size = 100
        total_registros = len(df)
        
        for i in range(0, total_registros, lote_size):
            lote = df.iloc[i:min(i+lote_size, total_registros)]
            novos_registros = []
            
            for _, row in lote.iterrows():
                try:
                    codigo = str(row['codigo']).strip()
                    
                    if codigo in codigos_existentes and force_update:
                        # Atualizar registro existente
                        infracao_existente = codigos_existentes[codigo]
                        infracao_existente.descricao = str(row['descricao'])
                        infracao_existente.responsavel = str(row['responsavel'])
                        infracao_existente.valor_multa = float(row['valor_multa'])
                        infracao_existente.orgao_autuador = str(row['orgao_autuador'])
                        infracao_existente.artigos_ctb = str(row['artigos_ctb'])
                        infracao_existente.pontos = int(row['pontos'])
                        infracao_existente.gravidade = str(row['gravidade'])
                        registros_atualizados += 1
                    elif codigo not in codigos_existentes:
                        # Criar novo registro
                        infracao = Infracao(
                            codigo=codigo,
                            descricao=str(row['descricao']),
                            responsavel=str(row['responsavel']),
                            valor_multa=float(row['valor_multa']),
                            orgao_autuador=str(row['orgao_autuador']),
                            artigos_ctb=str(row['artigos_ctb']),
                            pontos=int(row['pontos']),
                            gravidade=str(row['gravidade'])
                        )
                        novos_registros.append(infracao)
                        registros_importados += 1
                    else:
                        # Registro existe mas não será atualizado
                        registros_ignorados += 1
                except Exception as e:
                    logger.error(f"Erro ao processar registro {codigo}: {e}")
                    continue
            
            # Adicionar novos registros em lote
            if novos_registros:
                try:
                    db.bulk_save_objects(novos_registros)
                    db.commit()
                except IntegrityError as e:
                    db.rollback()
                    logger.error(f"Erro de integridade ao inserir lote: {e}")
                    # Inserir um por um para identificar o registro problemático
                    for infracao in novos_registros:
                        try:
                            db.add(infracao)
                            db.commit()
                        except IntegrityError as e:
                            db.rollback()
                            logger.error(f"Erro ao inserir registro {infracao.codigo}: {e}")
                except Exception as e:
                    db.rollback()
                    logger.error(f"Erro ao inserir lote: {e}")
            
            # Commit das atualizações
            if registros_atualizados > 0:
                try:
                    db.commit()
                except Exception as e:
                    db.rollback()
                    logger.error(f"Erro ao atualizar registros: {e}")
            
            # Log de progresso
            if (i + lote_size) % 1000 == 0 or (i + lote_size) >= total_registros:
                logger.info(f"Progresso: {min(i + lote_size, total_registros)}/{total_registros} registros processados")
        
        # Log final
        logger.info(f"Importação concluída: {registros_importados} novos, {registros_atualizados} atualizados, {registros_ignorados} ignorados.")
        return registros_importados + registros_atualizados
    
    except Exception as e:
        db.rollback()
        logger.error(f"Erro durante a importação do CSV: {e}")
        raise 