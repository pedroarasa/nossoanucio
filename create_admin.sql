-- Primeiro, vamos garantir que a tabela users existe
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_admin BOOLEAN DEFAULT FALSE
);

-- Agora vamos inserir o usuário administrador
INSERT INTO users (email, password_hash, name, is_admin)
VALUES (
    'dono@dono',
    '41313769p', -- senha
    'Administrador',
    TRUE
)
ON CONFLICT (email) DO NOTHING; 