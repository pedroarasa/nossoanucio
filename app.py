import os
import io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image as PILImage
from dotenv import load_dotenv
from sqlalchemy import or_

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'chave-secreta-padrao')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'usuários'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(100))
    profile_picture = db.Column(db.LargeBinary)
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
    user_id = db.Column(db.Integer, db.ForeignKey('usuários.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    photos = db.relationship('PostPhoto', backref='post', lazy=True, cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='post', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='post', lazy=True, cascade='all, delete-orphan')

class PostPhoto(db.Model):
    __tablename__ = 'fotos_anuncio'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)
    is_main = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Like(db.Model):
    __tablename__ = 'gosta'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuários.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    __tablename__ = 'comentarios'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('usuários.id', ondelete='CASCADE'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def process_image(image_data, max_size=(800, 800)):
    img = PILImage.open(io.BytesIO(image_data))
    img.thumbnail(max_size)
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85)
    return output.getvalue()

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
        
        if User.query.filter_by(username=username).first():
            flash('Nome de usuário já existe')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password, location=location)
        
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename:
                image_data = file.read()
                user.profile_picture = process_image(image_data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registro realizado com sucesso!')
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
                photo = PostPhoto(
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
    user = User.query.get_or_404(user_id)
    if user.profile_picture:
        return send_file(
            io.BytesIO(user.profile_picture),
            mimetype='image/jpeg'
        )
    return send_file('static/default_profile.jpg', mimetype='image/jpeg')

@app.route('/post_image/<int:photo_id>')
def post_image(photo_id):
    photo = PostPhoto.query.get_or_404(photo_id)
    return send_file(
        io.BytesIO(photo.image_data),
        mimetype='image/jpeg'
    )

@app.route('/user/<int:user_id>')
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()
    return render_template('user_profile.html', user=user, posts=posts)

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

if __name__ == '__main__':
    app.run(debug=True) 