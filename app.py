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

# Configuração do banco de dados Neon
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

db = SQLAlchemy(app)

# Criar pasta de uploads se não existir
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    profile_picture = db.Column(db.String(200))
    bio = db.Column(db.Text)
    location = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('Post', backref='author', lazy=True)

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text)
    image_url = db.Column(db.String(200))
    price = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.relationship('Like', backref='post', lazy=True)
    comments = db.relationship('Comment', backref='post', lazy=True)

class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    users = User.query.all()
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', users=users, posts=posts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
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
            
            # Criar pasta de uploads se não existir
            upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            # Salvar foto de perfil
            profile_picture = request.files.get('profile_picture')
            if profile_picture and profile_picture.filename:
                filename = secure_filename(profile_picture.filename)
                file_path = os.path.join(upload_folder, filename)
                profile_picture.save(file_path)
            else:
                filename = 'default_profile.png'
            
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                location=location,
                profile_picture=filename
            )
            
            db.session.add(user)
            db.session.commit()
            
            flash('Cadastro realizado com sucesso!')
            return redirect(url_for('login'))
        
        return render_template('register.html')
    except Exception as e:
        logger.error(f'Erro no registro: {str(e)}')
        flash('Erro ao realizar cadastro. Por favor, tente novamente.')
        return redirect(url_for('register'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        
        flash('Usuário ou senha inválidos')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/post', methods=['POST'])
def create_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    content = request.form.get('content')
    price = request.form.get('price')
    image = request.files.get('image')
    
    post = Post(
        user_id=session['user_id'],
        content=content,
        price=float(price) if price else None
    )
    
    if image:
        filename = secure_filename(image.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(image_path)
        post.image_url = filename
    
    db.session.add(post)
    db.session.commit()
    
    return redirect(url_for('index'))

@app.route('/like/<int:post_id>', methods=['POST'])
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

@app.route('/comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    content = request.form.get('content')
    
    comment = Comment(
        user_id=session['user_id'],
        post_id=post_id,
        content=content
    )
    
    db.session.add(comment)
    db.session.commit()
    
    return redirect(url_for('index'))

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        posts = Post.query.filter(Post.content.ilike(f'%{query}%')).all()
    else:
        posts = []
    return render_template('search.html', posts=posts, query=query)

@app.route('/random')
def random_posts():
    posts = Post.query.order_by(db.func.random()).limit(10).all()
    return render_template('random.html', posts=posts)

@app.route('/user/<int:user_id>')
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()
    return render_template('user_profile.html', user=user, posts=posts)

def process_image(file):
    try:
        # Lista de formatos de imagem suportados
        supported_formats = ['JPEG', 'PNG', 'GIF', 'BMP', 'TIFF', 'WEBP', 'HEIC']
        
        # Abrir a imagem
        img = PILImage.open(file)
        
        # Corrigir a orientação da imagem
        if hasattr(img, '_getexif'):
            exif = img._getexif()
            if exif is not None:
                orientation = exif.get(274)
                if orientation == 3:
                    img = img.rotate(180, expand=True)
                elif orientation == 6:
                    img = img.rotate(270, expand=True)
                elif orientation == 8:
                    img = img.rotate(90, expand=True)
        
        # Redimensionar a imagem se for muito grande
        max_size = (1920, 1920)
        img.thumbnail(max_size, PILImage.LANCZOS)
        
        # Verificar se o formato é suportado
        if img.format not in supported_formats:
            # Converter para JPEG se o formato não for suportado
            img = img.convert('RGB')
            format_to_save = 'JPEG'
        else:
            format_to_save = img.format
        
        # Converter para bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format=format_to_save, quality=85, optimize=True)
        img_byte_arr = img_byte_arr.getvalue()
        
        return img_byte_arr
    except Exception as e:
        logger.error(f'Erro ao processar imagem: {str(e)}')
        raise

# Adicionar handler de erro
@app.errorhandler(500)
def internal_error(error):
    logger.error(f'Erro interno do servidor: {error}')
    return render_template('error.html', error=error), 500

@app.route('/admin')
def admin_login():
    return render_template('admin_login.html')

@app.route('/admin/secret', methods=['GET', 'POST'])
def admin_secret():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == '41313769p':  # Senha do administrador
            session['is_admin'] = True
            return redirect(url_for('admin_panel'))
        flash('Senha incorreta')
        return redirect(url_for('admin_login'))
    return redirect(url_for('admin_login'))

@app.route('/admin/panel')
def admin_panel():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('admin_panel.html', announcements=posts)

@app.route('/admin/delete/<int:announcement_id>', methods=['POST'])
def admin_delete(announcement_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    post = Post.query.get_or_404(announcement_id)
    db.session.delete(post)
    db.session.commit()
    
    flash('Anúncio excluído com sucesso!')
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(debug=True) 