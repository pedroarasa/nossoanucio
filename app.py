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

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'Usuários'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    profile_picture = db.Column(db.LargeBinary)
    bio = db.Column(db.Text)
    location = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('Post', backref='author', lazy=True)
    likes = db.relationship('Like', backref='user', lazy=True)
    comments = db.relationship('Comment', backref='user', lazy=True)

class Post(db.Model):
    __tablename__ = 'Posts'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    image_data = db.Column(db.LargeBinary)
    price = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('Usuários.id'), nullable=False)
    likes = db.relationship('Like', backref='post', lazy=True)
    comments = db.relationship('Comment', backref='post', lazy=True)

class Like(db.Model):
    __tablename__ = 'Gosta'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Usuários.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('Posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    __tablename__ = 'Comentários'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('Usuários.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('Posts.id'), nullable=False)

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
            flash('Login realizado com sucesso!')
            return redirect(url_for('index'))
        
        flash('Usuário ou senha inválidos')
    
    return render_template('login.html')

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
            
            # Processar foto de perfil
            profile_picture = request.files.get('profile_picture')
            if profile_picture and profile_picture.filename:
                try:
                    # Ler a imagem como bytes
                    image_bytes = profile_picture.read()
                    # Redimensionar a imagem
                    img = PILImage.open(io.BytesIO(image_bytes))
                    img.thumbnail((200, 200))
                    # Converter de volta para bytes
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format=img.format)
                    img_byte_arr = img_byte_arr.getvalue()
                except Exception as e:
                    logger.error(f'Erro ao processar imagem: {str(e)}')
                    flash('Erro ao processar a imagem. Por favor, tente novamente.')
                    return redirect(url_for('register'))
            else:
                # Criar uma imagem padrão em branco
                img = PILImage.new('RGB', (200, 200), color='gray')
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
            
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                location=location,
                profile_picture=img_byte_arr
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

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logout realizado com sucesso!')
    return redirect(url_for('login'))

# Rotas de conteúdo
@app.route('/post/new', methods=['POST'])
def create_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        content = request.form['content']
        price = float(request.form['price'])
        image = request.files.get('image')
        
        if not image:
            flash('Por favor, selecione uma imagem')
            return redirect(url_for('index'))
        
        # Processar imagem
        image_bytes = image.read()
        img = PILImage.open(io.BytesIO(image_bytes))
        img.thumbnail((800, 800))  # Redimensionar para 800x800
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format=img.format)
        img_byte_arr = img_byte_arr.getvalue()
        
        post = Post(
            content=content,
            price=price,
            image_data=img_byte_arr,
            user_id=session['user_id']
        )
        
        db.session.add(post)
        db.session.commit()
        
        flash('Anúncio publicado com sucesso!')
    except Exception as e:
        logger.error(f'Erro ao criar post: {str(e)}')
        flash('Erro ao publicar anúncio')
    
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

@app.route('/post_image/<int:post_id>')
def post_image(post_id):
    post = Post.query.get_or_404(post_id)
    if post.image_data:
        return send_file(
            io.BytesIO(post.image_data),
            mimetype='image/jpeg'
        )
    return send_file('static/default_post.png')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 