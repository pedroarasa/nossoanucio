-- Criar tabela de usuários
CREATE TABLE IF NOT EXISTS "usuários" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password VARCHAR(120) NOT NULL,
    location VARCHAR(100),
    profile_picture BYTEA,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar tabela de posts
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    user_id INTEGER REFERENCES "usuários"(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar tabela de fotos dos anúncios
CREATE TABLE IF NOT EXISTS fotos_anuncio (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    image_data BYTEA NOT NULL,
    is_main BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar tabela de likes
CREATE TABLE IF NOT EXISTS gosta (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES "usuários"(id) ON DELETE CASCADE,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, post_id)
);

-- Criar tabela de comentários
CREATE TABLE IF NOT EXISTS comentarios (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    user_id INTEGER REFERENCES "usuários"(id) ON DELETE CASCADE,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Criar índices para melhorar a performance
CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_fotos_post_id ON fotos_anuncio(post_id);
CREATE INDEX IF NOT EXISTS idx_gosta_user_id ON gosta(user_id);
CREATE INDEX IF NOT EXISTS idx_gosta_post_id ON gosta(post_id);
CREATE INDEX IF NOT EXISTS idx_comentarios_user_id ON comentarios(user_id);
CREATE INDEX IF NOT EXISTS idx_comentarios_post_id ON comentarios(post_id);

-- Inserir usuário administrador padrão (senha: admin123)
INSERT INTO "usuários" (username, password, location, is_admin)
VALUES ('dono@dono', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY.5AYzKxJ5qK8y', 'Administrador', TRUE)
ON CONFLICT (username) DO NOTHING; 