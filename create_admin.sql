-- Inserir usuário administrador
INSERT INTO users (email, password_hash, name, is_admin)
VALUES (
    'admin@admin.com',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', -- senha: admin123
    'Administrador',
    TRUE
)
ON CONFLICT (email) DO NOTHING; 