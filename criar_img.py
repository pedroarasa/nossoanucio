from PIL import Image
import os

# Criar pasta
os.makedirs('static/img', exist_ok=True)

# Criar imagens
Image.new('RGB', (100, 100), 'gray').save('static/img/default_profile.png')
Image.new('RGB', (400, 300), 'gray').save('static/img/default_post.png')

print('Pronto!') 