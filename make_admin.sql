-- Tornar o usuário administrador
UPDATE users
SET is_admin = TRUE
WHERE email = 'dono@dono'; 