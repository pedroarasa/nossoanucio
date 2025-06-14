import os
import io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image as PILImage
from dotenv import load_dotenv
from sqlalchemy import or_
from functools import wraps
from PIL import Image
from models import db, User, ProfilePhoto, Post, Photo, Like, Dislike, Comment, Curriculo

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chave-secreta-padrao')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

db.init_app(app)

# Criar imagens padrão se não existirem
def create_default_images():
    try:
        if not os.path.exists('static/img'):
            os.makedirs('static/img')
        
        # Criar imagem de perfil padrão
        if not os.path.exists('static/img/default_profile.png'):
            img = Image.new('RGB', (100, 100), 'gray')
            img.save('static/img/default_profile.png')
        
        # Criar imagem de post padrão
        if not os.path.exists('static/img/default_post.png'):
            img = Image.new('RGB', (400, 300), 'gray')
            img.save('static/img/default_post.png')
    except Exception as e:
        app.logger.error(f"Erro ao criar imagens padrão: {str(e)}")

# Criar imagens padrão ao iniciar
create_default_images()

def process_image(image_data, max_size=(800, 800)):
    try:
        img = Image.open(io.BytesIO(image_data))
        
        # Converte para RGB se necessário
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Calcula as novas dimensões mantendo a proporção
        width, height = img.size
        ratio = min(max_size[0]/width, max_size[1]/height)
        new_size = (int(width * ratio), int(height * ratio))
        
        # Redimensiona a imagem
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Salva em um buffer
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85, optimize=True)
        buffer.seek(0)
        
        return buffer.getvalue()
    except Exception as e:
        app.logger.error(f"Erro ao processar imagem: {str(e)}")
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    users = User.query.all()
    return render_template('index.html', posts=posts, users=users)

@app.route('/post/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    like = Like.query.filter_by(
        user_id=session['user_id'],
        post_id=post_id
    ).first()
    
    if like:
        db.session.delete(like)
        db.session.commit()
        return jsonify({'action': 'unliked'})
    
    like = Like(user_id=session['user_id'], post_id=post_id)
    db.session.add(like)
    db.session.commit()
    return jsonify({'action': 'liked'})

@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    if 'user_id' not in session:
        flash('Você precisa estar logado para comentar')
        return redirect(url_for('login'))
    
    content = request.form.get('content')
    if not content:
        flash('O comentário não pode estar vazio')
        return redirect(url_for('index'))
    
    comment = Comment(
        content=content,
        user_id=session['user_id'],
        post_id=post_id
    )
    db.session.add(comment)
    db.session.commit()
    
    flash('Comentário adicionado com sucesso!')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        location = request.form['location']
        
        # Verifica se o usuário já existe
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Nome de usuário já existe!', 'danger')
            return redirect(url_for('register'))
        
        # Cria novo usuário
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, location=location)
        
        # Se for o usuário dono@dono, define como admin
        if username == 'dono@dono':
            new_user.is_admin = True
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Cadastro realizado com sucesso! Faça login para continuar.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            flash('Login realizado com sucesso!')
            return redirect(url_for('index'))
        else:
            flash('Usuário ou senha inválidos')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso!')
    return redirect(url_for('index'))

@app.route('/create_post', methods=['POST'])
def create_post():
    if 'user_id' not in session:
        flash('Você precisa estar logado para criar um anúncio')
        return redirect(url_for('login'))
    
    content = request.form.get('content')
    price = request.form.get('price')
    images = request.files.getlist('images')
    
    if not content or not price or not images:
        flash('Todos os campos são obrigatórios')
        return redirect(url_for('index'))
    
    try:
        price = float(price)
        post = Post(content=content, price=price, user_id=session['user_id'])
        db.session.add(post)
        db.session.flush()
        
        for i, image in enumerate(images):
            if image and image.filename:
                image_data = image.read()
                photo = Photo(
                    post_id=post.id,
                    image_data=process_image(image_data),
                    is_main=(i == 0)
                )
                db.session.add(photo)
        
        db.session.commit()
        flash('Anúncio criado com sucesso!')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao criar anúncio. Por favor, tente novamente.')
    
    return redirect(url_for('index'))

@app.route('/profile_image/<int:user_id>')
def profile_image(user_id):
    try:
        profile_photo = ProfilePhoto.query.filter_by(user_id=user_id).first()
        if profile_photo:
            return send_file(
                io.BytesIO(profile_photo.image_data),
                mimetype='image/jpeg',
                cache_timeout=0
            )
        return send_file('static/img/default_profile.png', mimetype='image/png', cache_timeout=0)
    except Exception as e:
        app.logger.error(f"Erro ao carregar imagem do perfil: {str(e)}")
        return send_file('static/img/default_profile.png', mimetype='image/png', cache_timeout=0)

@app.route('/post_image/<int:photo_id>')
def post_image(photo_id):
    try:
        photo = Photo.query.get_or_404(photo_id)
        return send_file(
            io.BytesIO(photo.image_data),
            mimetype='image/jpeg',
            cache_timeout=0
        )
    except Exception as e:
        app.logger.error(f"Erro ao carregar imagem do post: {str(e)}")
        return send_file('static/img/default_post.png', mimetype='image/png', cache_timeout=0)

@app.route('/user/<int:user_id>')
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    user_posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()
    return render_template('user_profile.html', user=user, posts=user_posts)

@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    if 'user_id' not in session:
        flash('Você precisa estar logado para excluir um anúncio')
        return redirect(url_for('login'))
    
    post = Post.query.get_or_404(post_id)
    
    if post.user_id != session['user_id'] and not session.get('is_admin'):
        flash('Você não tem permissão para excluir este anúncio')
        return redirect(url_for('index'))
    
    db.session.delete(post)
    db.session.commit()
    flash('Anúncio excluído com sucesso!')
    return redirect(url_for('index'))

@app.route('/announcements')
def announcements():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('announcements.html', posts=posts)

@app.route('/user/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    if not session.get('is_admin'):
        flash('Apenas administradores podem excluir usuários')
        return redirect(url_for('index'))
    
    if user_id == session.get('user_id'):
        flash('Você não pode excluir seu próprio usuário')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Usuário excluído com sucesso!')
    return redirect(url_for('index'))

@app.route('/post/<int:post_id>/dislike', methods=['POST'])
def dislike_post(post_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    post = Post.query.get_or_404(post_id)
    user_id = session['user_id']
    
    # Verifica se já existe um dislike
    dislike = Dislike.query.filter_by(user_id=user_id, post_id=post_id).first()
    
    if dislike:
        # Se já existe, remove o dislike
        db.session.delete(dislike)
        db.session.commit()
        return jsonify({'action': 'undisliked'})
    else:
        # Remove like se existir
        like = Like.query.filter_by(user_id=user_id, post_id=post_id).first()
        if like:
            db.session.delete(like)
        
        # Adiciona o dislike
        new_dislike = Dislike(user_id=user_id, post_id=post_id)
        db.session.add(new_dislike)
        db.session.commit()
        return jsonify({'action': 'disliked'})

@app.route('/curriculos')
def curriculos():
    curriculos = Curriculo.query.order_by(Curriculo.created_at.desc()).all()
    return render_template('curriculos.html', curriculos=curriculos)

@app.route('/curriculo/create', methods=['POST'])
@login_required
def create_curriculo():
    if request.method == 'POST':
        nome_completo = request.form['nome_completo']
        email = request.form['email']
        telefone = request.form.get('telefone')
        area_profissional = request.form['area_profissional']
        experiencia = request.form['experiencia']
        formacao = request.form['formacao']
        habilidades = request.form['habilidades']
        objetivo = request.form['objetivo']
        
        curriculo_pdf = None
        if 'curriculo_pdf' in request.files:
            file = request.files['curriculo_pdf']
            if file and file.filename:
                curriculo_pdf = file.read()
        
        new_curriculo = Curriculo(
            user_id=session['user_id'],
            nome_completo=nome_completo,
            email=email,
            telefone=telefone,
            area_profissional=area_profissional,
            experiencia=experiencia,
            formacao=formacao,
            habilidades=habilidades,
            objetivo=objetivo,
            curriculo_pdf=curriculo_pdf
        )
        
        db.session.add(new_curriculo)
        db.session.commit()
        
        flash('Currículo cadastrado com sucesso!', 'success')
        return redirect(url_for('curriculos'))

@app.route('/curriculo/<int:curriculo_id>/download')
def download_curriculo(curriculo_id):
    curriculo = Curriculo.query.get_or_404(curriculo_id)
    if not curriculo.curriculo_pdf:
        flash('Este currículo não possui arquivo PDF.', 'warning')
        return redirect(url_for('curriculos'))
    
    return send_file(
        io.BytesIO(curriculo.curriculo_pdf),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'curriculo_{curriculo.nome_completo}.pdf'
    )

@app.route('/upload_profile_picture', methods=['POST'])
@login_required
def upload_profile_picture():
    if 'profile_picture' not in request.files:
        flash('Nenhuma imagem selecionada', 'error')
        return redirect(url_for('user_profile', user_id=session['user_id']))
    
    file = request.files['profile_picture']
    if file.filename == '':
        flash('Nenhuma imagem selecionada', 'error')
        return redirect(url_for('user_profile', user_id=session['user_id']))
    
    if file:
        try:
            # Lê a imagem
            image_data = file.read()
            
            # Processa a imagem para o perfil (400x400 para melhor qualidade)
            processed_image = process_image(image_data, max_size=(400, 400))
            
            if processed_image:
                # Atualiza ou cria a foto de perfil
                profile_photo = ProfilePhoto.query.filter_by(user_id=session['user_id']).first()
                if profile_photo:
                    profile_photo.image_data = processed_image
                    profile_photo.updated_at = datetime.utcnow()
                else:
                    profile_photo = ProfilePhoto(
                        user_id=session['user_id'],
                        image_data=processed_image
                    )
                    db.session.add(profile_photo)
                
                db.session.commit()
                flash('Foto de perfil atualizada com sucesso!', 'success')
            else:
                flash('Erro ao processar a imagem', 'error')
        except Exception as e:
            flash('Erro ao processar a imagem', 'error')
            app.logger.error(f'Erro ao processar imagem: {str(e)}')
    
    return redirect(url_for('user_profile', user_id=session['user_id']))

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

if __name__ == '__main__':
    app.run(debug=True) 