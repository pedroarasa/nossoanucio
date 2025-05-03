-- Tabela principal de imagens
CREATE TABLE IF NOT EXISTS image (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    description TEXT,
    image_data BYTEA NOT NULL,
    image_type VARCHAR(20) NOT NULL,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    is_public BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Tabela para imagens adicionais
CREATE TABLE IF NOT EXISTS additional_images (
    id SERIAL PRIMARY KEY,
    main_image_id INTEGER NOT NULL,
    image_data BYTEA NOT NULL,
    image_type VARCHAR(20) NOT NULL,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (main_image_id) REFERENCES image(id) ON DELETE CASCADE
);

-- Tabela de reações
CREATE TABLE IF NOT EXISTS reactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    image_id INTEGER NOT NULL,
    is_like BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (image_id) REFERENCES image(id),
    UNIQUE(user_id, image_id)
); 