-- Tabela principal de imagens
CREATE TABLE IF NOT EXISTS image (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    description TEXT,
    image_data BYTEA NOT NULL,
    image_type VARCHAR(20) NOT NULL,
    likes INTEGER DEFAULT 0,
    dislikes INTEGER DEFAULT 0,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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