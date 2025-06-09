from app import app, db
from sqlalchemy import text

def update_database():
    with app.app_context():
        # Adiciona a coluna is_admin se ela não existir
        try:
            db.session.execute(text('ALTER TABLE "Usuários" ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE'))
            db.session.commit()
            print("Coluna is_admin adicionada com sucesso!")
        except Exception as e:
            print(f"Erro ao adicionar coluna is_admin: {e}")
            db.session.rollback()

if __name__ == '__main__':
    update_database() 