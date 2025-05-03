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

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://neondb_owner:npg_izJKD7Qm0kEh@ep-wandering-resonance-a9e1300q-pooler.gwc.azure.neon.tech/neondb?sslmode=require'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    announcements = db.relationship('Announcement', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(200))
    category = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    images = db.relationship('Image', backref='announcement', lazy=True, cascade="all, delete-orphan")
    is_active = db.Column(db.Boolean, default=True)

class Image(db.Model):
    __tablename__ = 'images'
    id = db.Column(db.Integer, primary_key=True)
    image_data = db.Column(db.LargeBinary, nullable=False)
    image_type = db.Column(db.String(20), nullable=False)
    is_main = db.Column(db.Boolean, default=False)
    announcement_id = db.Column(db.Integer, db.ForeignKey('announcements.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    announcements = Announcement.query.filter_by(is_active=True).order_by(Announcement.created_at.desc()).all()
    return render_template('index.html', announcements=announcements)

@app.route('/announcement/<int:announcement_id>')
def view_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    return render_template('announcement.html', announcement=announcement)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['is_admin'] = user.is_admin
            flash('Login realizado com sucesso!')
            return redirect(url_for('index'))
        else:
            flash('Email ou senha incorretos')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            name = request.form.get('name')
            password = request.form.get('password')
            phone = request.form.get('phone')
            
            logger.debug(f'Tentativa de cadastro: {email}, {name}')
            
            # Verificar se o email já existe
            existing_user = User.query.filter(User.email == email).first()
            if existing_user:
                flash('Email já cadastrado')
                return redirect(url_for('register'))
            
            # Criar novo usuário
            user = User(email=email, name=name, phone=phone)
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            logger.debug(f'Usuário cadastrado com sucesso: {email}')
            flash('Cadastro realizado com sucesso!')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erro no cadastro: {str(e)}')
            flash(f'Erro ao realizar cadastro. Por favor, tente novamente.')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso!')
    return redirect(url_for('index'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        flash('Faça login antes de criar um anúncio')
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        return render_template('upload.html')
    
    if 'images' not in request.files:
        flash('Nenhuma imagem selecionada')
        return redirect(url_for('upload'))
    
    files = request.files.getlist('images')
    if not files or files[0].filename == '':
        flash('Nenhuma imagem selecionada')
        return redirect(url_for('upload'))
    
    if len(files) > 7:
        flash('Você pode adicionar no máximo 7 imagens')
        return redirect(url_for('upload'))
    
    try:
        # Criar o anúncio
        announcement = Announcement(
            title=request.form['title'],
            description=request.form['description'],
            price=float(request.form['price']),
            location=request.form['location'],
            category=request.form['category'],
            user_id=session['user_id']
        )
        db.session.add(announcement)
        db.session.commit()
        
        # Adicionar as imagens
        for i, file in enumerate(files):
            image_data = process_image(file)
            image_type = file.content_type
            
            new_image = Image(
                image_data=image_data,
                image_type=image_type,
                is_main=(i == 0),  # Primeira imagem é a principal
                announcement_id=announcement.id
            )
            db.session.add(new_image)
        
        db.session.commit()
        flash('Anúncio criado com sucesso!')
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao criar anúncio: {str(e)}')
        return redirect(url_for('upload'))

@app.route('/image/<int:image_id>')
def get_image(image_id):
    image = Image.query.get_or_404(image_id)
    return send_file(
        BytesIO(image.image_data),
        mimetype=image.image_type,
        as_attachment=False
    )

@app.route('/delete/<int:announcement_id>', methods=['POST'])
def delete_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    password = request.form.get('password')
    
    if password == '2020' or (session.get('user_id') == announcement.user_id):
        db.session.delete(announcement)
        db.session.commit()
        flash('Anúncio deletado com sucesso!')
    else:
        flash('Senha incorreta ou você não tem permissão para deletar este anúncio')
    
    return redirect(url_for('index'))

@app.route('/search')
def search():
    query = request.args.get('q', '')
    announcements = Announcement.query.filter(
        (Announcement.title.contains(query)) | 
        (Announcement.description.contains(query)) |
        (Announcement.location.contains(query)) |
        (Announcement.category.contains(query))
    ).filter_by(is_active=True).all()
    return render_template('index.html', announcements=announcements, query=query)

def process_image(file):
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
    
    # Converter para bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format=img.format or 'JPEG')
    img_byte_arr = img_byte_arr.getvalue()
    
    return img_byte_arr

# Adicionar handler de erro
@app.errorhandler(500)
def internal_error(error):
    logger.error(f'Erro interno do servidor: {error}')
    return render_template('error.html', error=error), 500

if __name__ == '__main__':
    app.run(debug=True) 