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

        try:
            # Adiciona a coluna image_data se ela não existir
            db.session.execute(text("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (
                        SELECT 1 
                        FROM information_schema.columns 
                        WHERE table_name = 'posts' 
                        AND column_name = 'image_data'
                    ) THEN
                        ALTER TABLE posts ADD COLUMN image_data BYTEA;
                    END IF;
                END $$;
            """))
            
            db.session.commit()
            print("Banco de dados atualizado com sucesso!")
        except Exception as e:
            print(f"Erro ao atualizar o banco de dados: {e}")
            db.session.rollback()

if __name__ == '__main__':
    update_database() 