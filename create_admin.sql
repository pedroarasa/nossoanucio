-- Inserir usuário administrador
INSERT INTO users (email, password_hash, name, is_admin)
VALUES (
    'dono@dono',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', -- senha: 41313769p
    'Administrador',
    TRUE
)
ON CONFLICT (email) DO NOTHING; 