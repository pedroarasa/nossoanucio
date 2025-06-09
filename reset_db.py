from app import app, db

with app.app_context():
    # Apaga todas as tabelas
    db.drop_all()
    print("Tabelas apagadas com sucesso!")
    
    # Recria todas as tabelas
    db.create_all()
    print("Tabelas recriadas com sucesso!") 