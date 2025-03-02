from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.infracao import Infracao

def populate_db(db: Session):
    # Exemplo de dados para inserir
    infracoes = [
        Infracao(codigo="12345", descricao="Excesso de velocidade"),
        Infracao(codigo="67890", descricao="Estacionamento proibido"),
        # Adicione mais dados conforme necessário
    ]
    
    for infracao in infracoes:
        db.add(infracao)
    
    db.commit()

if __name__ == "__main__":
    db = next(get_db())
    populate_db(db)
    print("Dados inseridos com sucesso.")
