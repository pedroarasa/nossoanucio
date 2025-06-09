import os
import io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image as PILImage
from dotenv import load_dotenv
from sqlalchemy import or_
from sqlalchemy.sql import text

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
    dislikes = db.relationship('Dislike', backref='user', lazy=True)
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
    dislikes = db.relationship('Dislike', backref='post', lazy=True, cascade='all, delete-orphan')
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

class Dislike(db.Model):
    __tablename__ = 'nao_gosta'
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

# Rotas de autenticação
@app.route('/')
def index():
    try:
        posts = Post.query.order_by(Post.created_at.desc()).all()
        users = User.query.all()
        return render_template('index.html', posts=posts, users=users)
    except Exception as e:
        flash('Erro ao carregar a página. Por favor, tente novamente.')
        return render_template('index.html', posts=[], users=[])

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            location = request.form['location']
            
            if User.query.filter_by(username=username).first():
                flash('Nome de usuário já existe')
                return redirect(url_for('register'))
            
            profile_picture = None
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file.filename:
                    profile_picture = process_image(file.read())
            
            user = User(
                username=username,
                password=generate_password_hash(password),
                location=location,
                profile_picture=profile_picture
            )
            
            db.session.add(user)
            db.session.commit()
            
            flash('Registro realizado com sucesso!')
            return redirect(url_for('login'))
            
        except Exception as e:
            flash('Erro ao registrar. Por favor, tente novamente.')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso!')
    return redirect(url_for('index'))

# Rotas de conteúdo
@app.route('/create_post', methods=['POST'])
def create_post():
    if 'user_id' not in session:
        flash('Você precisa estar logado para criar um anúncio')
        return redirect(url_for('login'))
    
    content = request.form['content']
    price = float(request.form['price'])
    images = request.files.getlist('images')
    
    if not images:
        flash('Você precisa adicionar pelo menos uma imagem')
        return redirect(url_for('index'))
    
    post = Post(
        content=content,
        price=price,
        user_id=session['user_id']
    )
    db.session.add(post)
    db.session.commit()
    
    for i, image in enumerate(images):
        if image and image.filename:
            image_data = process_image(image.read())
            photo = PostPhoto(
                post_id=post.id,
                image_data=image_data,
                is_main=(i == 0)
            )
            db.session.add(photo)
    
    db.session.commit()
    flash('Anúncio criado com sucesso!')
    return redirect(url_for('index'))

@app.route('/post/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não está logado'}), 401
    
    post = Post.query.get_or_404(post_id)
    user_id = session['user_id']
    
    # Verifica se já existe like
    like = Like.query.filter_by(user_id=user_id, post_id=post_id).first()
    
    if like:
        # Remove o like
        db.session.delete(like)
        action = 'unliked'
    else:
        # Remove dislike se existir
        dislike = Dislike.query.filter_by(user_id=user_id, post_id=post_id).first()
        if dislike:
            db.session.delete(dislike)
        
        # Adiciona o like
        like = Like(user_id=user_id, post_id=post_id)
        db.session.add(like)
        action = 'liked'
    
    db.session.commit()
    
    return jsonify({
        'action': action,
        'likes_count': len(post.likes),
        'dislikes_count': len(post.dislikes)
    })

@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    if 'user_id' not in session:
        flash('Você precisa estar logado para comentar')
        return redirect(url_for('login'))
    
    content = request.form['content']
    comment = Comment(
        content=content,
        user_id=session['user_id'],
        post_id=post_id
    )
    db.session.add(comment)
    db.session.commit()
    
    flash('Comentário adicionado com sucesso!')
    return redirect(url_for('index'))

@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    if 'user_id' not in session:
        flash('Você precisa estar logado para excluir um anúncio')
        return redirect(url_for('login'))
    
    post = Post.query.get_or_404(post_id)
    if session['user_id'] != post.user_id and not session.get('is_admin'):
        flash('Você não tem permissão para excluir este anúncio')
        return redirect(url_for('index'))
    
    # Remove todas as fotos associadas
    PostPhoto.query.filter_by(post_id=post_id).delete()
    
    # Remove todos os likes associados
    Like.query.filter_by(post_id=post_id).delete()
    
    # Remove todos os comentários associados
    Comment.query.filter_by(post_id=post_id).delete()
    
    # Remove o post
    db.session.delete(post)
    db.session.commit()
    
    flash('Anúncio excluído com sucesso!')
    return redirect(url_for('index'))

# Rotas de perfil e busca
@app.route('/user/<int:user_id>')
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()
    return render_template('user_profile.html', user=user, posts=posts)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        # Busca por texto no conteúdo do anúncio
        posts = Post.query.filter(
            db.or_(
                Post.content.ilike(f'%{query}%'),
                User.username.ilike(f'%{query}%'),
                User.location.ilike(f'%{query}%')
            )
        ).order_by(Post.created_at.desc()).all()
    else:
        posts = []
    return render_template('search.html', posts=posts)

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
    # Imagem padrão em bytes
    default_image = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xdb\x00C\x01\t\t\t\x0c\x0b\x0c\x18\r\r\x182!\x1c!22222222222222222222222222222222222222222222222222\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x15\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x15\x10\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xf5\xff\xd9'
    return send_file(
        io.BytesIO(default_image),
        mimetype='image/jpeg'
    )

@app.route('/post_image/<int:photo_id>')
def post_image(photo_id):
    photo = PostPhoto.query.get_or_404(photo_id)
    if photo.image_data:
        return send_file(
            io.BytesIO(photo.image_data),
            mimetype='image/jpeg'
        )
    # Imagem padrão em bytes
    default_image = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xdb\x00C\x01\t\t\t\x0c\x0b\x0c\x18\r\r\x182!\x1c!22222222222222222222222222222222222222222222222222\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x15\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x15\x10\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xf5\xff\xd9'
    return send_file(
        io.BytesIO(default_image),
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

@app.route('/announcements')
def announcements():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('announcements.html', posts=posts)

@app.route('/post/<int:post_id>/dislike', methods=['POST'])
def dislike_post(post_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Usuário não está logado'}), 401
    
    post = Post.query.get_or_404(post_id)
    user_id = session['user_id']
    
    # Verifica se já existe dislike
    dislike = Dislike.query.filter_by(user_id=user_id, post_id=post_id).first()
    
    if dislike:
        # Remove o dislike
        db.session.delete(dislike)
        action = 'undisliked'
    else:
        # Remove like se existir
        like = Like.query.filter_by(user_id=user_id, post_id=post_id).first()
        if like:
            db.session.delete(like)
        
        # Adiciona o dislike
        dislike = Dislike(user_id=user_id, post_id=post_id)
        db.session.add(dislike)
        action = 'disliked'
    
    db.session.commit()
    
    return jsonify({
        'action': action,
        'likes_count': len(post.likes),
        'dislikes_count': len(post.dislikes)
    })

if __name__ == '__main__':
    app.run(debug=True) 