from PIL import Image
import os

# Criar pasta se não existir
if not os.path.exists('static/img'):
    os.makedirs('static/img')

# Criar imagem de perfil padrão
img = Image.new('RGB', (100, 100), color='gray')
img.save('static/img/default_profile.png')

# Criar imagem de post padrão
img = Image.new('RGB', (400, 300), color='gray')
img.save('static/img/default_post.png')

print("Imagens criadas!") 