from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image as PILImage
import io
import logging
import random
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chave_secreta_123')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/rede_social')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    profile_picture = db.Column(db.LargeBinary)
    location = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('Post', backref='author', lazy=True)
    likes = db.relationship('Like', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    likes = db.relationship('Like', backref='post', lazy=True)
    comments = db.relationship('Comment', backref='post', lazy=True)
    photos = db.relationship('PostPhoto', backref='post', lazy=True)

class PostPhoto(db.Model):
    __tablename__ = 'fotos_anuncio'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)
    is_main = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Like(db.Model):
    __tablename__ = 'gosta'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    __tablename__ = 'comentarios'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)

def process_image(image_data, max_size=(800, 800)):
    try:
        img = PILImage.open(io.BytesIO(image_data))
        img.thumbnail(max_size)
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85)
        return output.getvalue()
    except Exception as e:
        print(f"Erro ao processar imagem: {e}")
        return None

# Rotas de autenticação
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    posts = Post.query.order_by(Post.created_at.desc()).all()
    users = User.query.all()
    return render_template('index.html', posts=posts, users=users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            flash('Login realizado com sucesso!')
            return redirect(url_for('index'))
        
        flash('Usuário ou senha inválidos')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        location = request.form['location']
        
        if User.query.filter_by(username=username).first():
            flash('Nome de usuário já existe')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email já cadastrado')
            return redirect(url_for('register'))
        
        profile_picture = request.files.get('profile_picture')
        if profile_picture:
            image_data = profile_picture.read()
            processed_image = process_image(image_data, max_size=(200, 200))
            if processed_image:
                image_data = processed_image
        else:
            # Criar uma imagem padrão em branco
            img = PILImage.new('RGB', (200, 200), color='gray')
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            image_data = img_byte_arr.getvalue()
        
        # Verifica se é o usuário admin
        is_admin = username == 'dono@dono'
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            location=location,
            profile_picture=image_data,
            is_admin=is_admin
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Cadastro realizado com sucesso!')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('is_admin', None)
    flash('Logout realizado com sucesso!')
    return redirect(url_for('login'))

# Rotas de conteúdo
@app.route('/create_post', methods=['POST'])
def create_post():
    if 'user_id' not in session:
        flash('Você precisa estar logado para criar um anúncio!')
        return redirect(url_for('login'))
    
    content = request.form['content']
    price = float(request.form['price'])
    images = request.files.getlist('images')
    
    if not images:
        flash('É necessário enviar pelo menos uma imagem!')
        return redirect(url_for('index'))
    
    # Verifica o limite de 10 imagens
    if len(images) > 10:
        flash('Você pode enviar no máximo 10 imagens por anúncio!')
        return redirect(url_for('index'))
    
    post = Post(
        content=content,
        price=price,
        user_id=session['user_id']
    )
    db.session.add(post)
    db.session.flush()  # Para obter o ID do post
    
    # Processa e salva as imagens
    for i, image in enumerate(images):
        if image:
            image_data = image.read()
            processed_image = process_image(image_data)
            if processed_image:
                photo = PostPhoto(
                    post_id=post.id,
                    image_data=processed_image,
                    is_main=(i == 0)  # A primeira imagem é a principal
                )
                db.session.add(photo)
    
    db.session.commit()
    flash('Anúncio publicado com sucesso!')
    return redirect(url_for('index'))

@app.route('/post/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    post = Post.query.get_or_404(post_id)
    existing_like = Like.query.filter_by(
        user_id=session['user_id'],
        post_id=post_id
    ).first()
    
    if existing_like:
        db.session.delete(existing_like)
        action = 'unliked'
    else:
        like = Like(user_id=session['user_id'], post_id=post_id)
        db.session.add(like)
        action = 'liked'
    
    db.session.commit()
    return jsonify({'action': action})

@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    if 'user_id' not in session:
        flash('Você precisa estar logado para comentar!')
        return redirect(url_for('login'))
    
    content = request.form['content']
    if content:
        comment = Comment(
            content=content,
            user_id=session['user_id'],
            post_id=post_id
        )
        db.session.add(comment)
        db.session.commit()
    
    return redirect(url_for('index'))

@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Verifica se o usuário é o autor do post ou é admin
    if 'user_id' not in session or (post.user_id != session['user_id'] and not session.get('is_admin')):
        flash('Você não tem permissão para excluir este anúncio!')
        return redirect(url_for('index'))
    
    # Remove todos os likes e comentários associados
    Like.query.filter_by(post_id=post_id).delete()
    Comment.query.filter_by(post_id=post_id).delete()
    
    # Remove o post
    db.session.delete(post)
    db.session.commit()
    
    flash('Anúncio excluído com sucesso!')
    return redirect(url_for('index'))

# Rotas de perfil e busca
@app.route('/user/<int:user_id>')
def user_profile(user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(user_id)
    posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()
    return render_template('user_profile.html', user=user, posts=posts)

@app.route('/search')
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    query = request.args.get('q', '')
    if query:
        posts = Post.query.filter(Post.content.ilike(f'%{query}%')).all()
        users = User.query.filter(User.username.ilike(f'%{query}%')).all()
    else:
        posts = []
        users = []
    
    return render_template('search.html', posts=posts, users=users, query=query)

@app.route('/random')
def random_posts():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    posts = Post.query.all()
    if posts:
        random_post = random.choice(posts)
        return redirect(url_for('user_profile', user_id=random_post.user_id))
    
    flash('Nenhum post encontrado')
    return redirect(url_for('index'))

# Rotas de mídia
@app.route('/profile_image/<int:user_id>')
def profile_image(user_id):
    user = User.query.get_or_404(user_id)
    if user.profile_picture:
        return send_file(
            io.BytesIO(user.profile_picture),
            mimetype='image/jpeg'
        )
    return send_file('static/default_profile.png')

@app.route('/post_image/<int:photo_id>')
def post_image(photo_id):
    photo = PostPhoto.query.get_or_404(photo_id)
    return send_file(
        io.BytesIO(photo.image_data),
        mimetype='image/jpeg'
    )

@app.route('/post/<int:post_id>/photos')
def get_post_photos(post_id):
    photos = PostPhoto.query.filter_by(post_id=post_id).all()
    return jsonify([{
        'id': photo.id,
        'is_main': photo.is_main
    } for photo in photos])

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('login'))
    
    location = request.form.get('location')
    profile_picture = request.files.get('profile_picture')
    
    if location:
        user.location = location
    
    if profile_picture:
        image_data = profile_picture.read()
        processed_image = process_image(image_data, max_size=(200, 200))
        if processed_image:
            user.profile_picture = processed_image
    
    db.session.commit()
    flash('Perfil atualizado com sucesso!')
    return redirect(url_for('user_profile', user_id=user.id))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Apenas cria as tabelas se não existirem
    app.run(debug=True) 