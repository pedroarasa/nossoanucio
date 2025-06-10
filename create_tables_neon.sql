-- Criação das tabelas
CREATE TABLE IF NOT EXISTS usuários (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password VARCHAR(120) NOT NULL,
    location VARCHAR(100),
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fotos_perfil (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES usuários(id) ON DELETE CASCADE,
    image_data BYTEA NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    price NUMERIC(10,2) NOT NULL,
    user_id INTEGER REFERENCES usuários(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fotos_anuncio (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    image_data BYTEA NOT NULL,
    is_main BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gosta (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES usuários(id) ON DELETE CASCADE,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, post_id)
);

CREATE TABLE IF NOT EXISTS nao_gosta (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES usuários(id) ON DELETE CASCADE,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, post_id)
);

CREATE TABLE IF NOT EXISTS comentarios (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    user_id INTEGER REFERENCES usuários(id) ON DELETE CASCADE,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS curriculos (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES usuários(id) ON DELETE CASCADE,
    nome_completo VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL,
    telefone VARCHAR(20),
    area_profissional VARCHAR(100) NOT NULL,
    experiencia TEXT NOT NULL,
    formacao TEXT NOT NULL,
    habilidades TEXT NOT NULL,
    objetivo TEXT NOT NULL,
    curriculo_pdf BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para melhorar a performance
CREATE INDEX IF NOT EXISTS idx_fotos_perfil_user_id ON fotos_perfil(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_fotos_post_id ON fotos_anuncio(post_id);
CREATE INDEX IF NOT EXISTS idx_gosta_user_id ON gosta(user_id);
CREATE INDEX IF NOT EXISTS idx_gosta_post_id ON gosta(post_id);
CREATE INDEX IF NOT EXISTS idx_nao_gosta_user_id ON nao_gosta(user_id);
CREATE INDEX IF NOT EXISTS idx_nao_gosta_post_id ON nao_gosta(post_id);
CREATE INDEX IF NOT EXISTS idx_comentarios_user_id ON comentarios(user_id);
CREATE INDEX IF NOT EXISTS idx_comentarios_post_id ON comentarios(post_id);
CREATE INDEX IF NOT EXISTS idx_curriculos_user_id ON curriculos(user_id);

-- Inserir usuário admin padrão (senha: admin123)
INSERT INTO usuários (username, password, is_admin)
VALUES ('admin', 'pbkdf2:sha256:600000$dQw4w9WgXcQ$8c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9c9', TRUE)
ON CONFLICT (username) DO NOTHING;

-- Função para deletar usuário (apenas para administradores)
CREATE OR REPLACE FUNCTION deletar_usuario(admin_id INTEGER, user_id INTEGER)
RETURNS BOOLEAN AS $$
BEGIN
    -- Verifica se o usuário que está tentando deletar é admin
    IF NOT EXISTS (SELECT 1 FROM usuários WHERE id = admin_id AND is_admin = TRUE) THEN
        RETURN FALSE;
    END IF;
    
    -- Verifica se não está tentando deletar a si mesmo
    IF admin_id = user_id THEN
        RETURN FALSE;
    END IF;
    
    -- Deleta o usuário
    DELETE FROM usuários WHERE id = user_id;
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql; 