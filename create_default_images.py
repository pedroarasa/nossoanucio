from PIL import Image
import os

def create_default_images():
    # Criar diretório se não existir
    os.makedirs('static/img', exist_ok=True)
    
    # Criar imagem de perfil padrão (200x200)
    profile = Image.new('RGB', (200, 200), color='gray')
    profile.save('static/img/default_profile.png')
    
    # Criar imagem de post padrão (800x600)
    post = Image.new('RGB', (800, 600), color='gray')
    post.save('static/img/default_post.png')
    
    print("Imagens padrão criadas com sucesso!")

if __name__ == '__main__':
    create_default_images() 