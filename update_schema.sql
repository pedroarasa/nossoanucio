-- Adicionar coluna is_available na tabela announcements
ALTER TABLE announcements ADD COLUMN IF NOT EXISTS is_available BOOLEAN DEFAULT TRUE;

-- Criar tabela de likes
CREATE TABLE IF NOT EXISTS likes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    announcement_id INTEGER NOT NULL REFERENCES announcements(id),
    is_like BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, announcement_id)
);

-- Criar índices para melhorar a performance
CREATE INDEX IF NOT EXISTS idx_likes_user_id ON likes(user_id);
CREATE INDEX IF NOT EXISTS idx_likes_announcement_id ON likes(announcement_id); 