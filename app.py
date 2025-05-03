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

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://neondb_owner:npg_izJKD7Qm0kEh@ep-wandering-resonance-a9e1300q-pooler.gwc.azure.neon.tech/neondb?sslmode=require'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    images = db.relationship('Image', backref='owner', lazy=True)
    reactions = db.relationship('Reaction', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Image(db.Model):
    __tablename__ = 'image'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    image_data = db.Column(db.LargeBinary, nullable=False)
    image_type = db.Column(db.String(20), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    additional_images = db.relationship('AdditionalImage', backref='main_image', lazy=True, cascade="all, delete-orphan")
    reactions = db.relationship('Reaction', backref='image', lazy=True)
    is_public = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Image {self.name}>'

class AdditionalImage(db.Model):
    __tablename__ = 'additional_images'
    id = db.Column(db.Integer, primary_key=True)
    main_image_id = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)
    image_type = db.Column(db.String(20), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AdditionalImage {self.id}>'

class Reaction(db.Model):
    __tablename__ = 'reactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'), nullable=False)
    is_like = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash('Login realizado com sucesso!')
            return redirect(url_for('index'))
        else:
            flash('Email ou senha incorretos')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email já cadastrado')
            return redirect(url_for('register'))
        
        user = User(email=email, name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Cadastro realizado com sucesso!')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso!')
    return redirect(url_for('login'))

@app.route('/')
def index():
    images = Image.query.filter_by(is_public=True).order_by(Image.upload_date.desc()).all()
    return render_template('index.html', images=images)

@app.route('/image/<int:image_id>')
def get_image(image_id):
    image = Image.query.get_or_404(image_id)
    return send_file(
        BytesIO(image.image_data),
        mimetype=image.image_type,
        as_attachment=False
    )

@app.route('/additional_image/<int:image_id>/<int:index>')
def get_additional_image(image_id, index):
    additional_image = AdditionalImage.query.filter_by(main_image_id=image_id).offset(index).first_or_404()
    return send_file(
        BytesIO(additional_image.image_data),
        mimetype=additional_image.image_type,
        as_attachment=False
    )

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        flash('Você precisa estar logado para fazer upload de imagens')
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        return render_template('upload.html')
    
    if 'images' not in request.files:
        flash('Nenhum arquivo selecionado')
        return redirect(url_for('upload'))
    
    files = request.files.getlist('images')
    if not files or files[0].filename == '':
        flash('Nenhum arquivo selecionado')
        return redirect(url_for('upload'))
    
    if len(files) > 10:
        flash('Você pode adicionar no máximo 10 imagens')
        return redirect(url_for('upload'))
    
    main_image_index = int(request.form.get('main_image_index', 0))
    if main_image_index >= len(files):
        flash('Índice da imagem principal inválido')
        return redirect(url_for('upload'))
    
    # Criar o registro principal
    main_image = files[main_image_index]
    main_image_data = process_image(main_image)
    main_image_type = main_image.content_type
    
    new_image = Image(
        name=request.form['name'],
        phone=request.form['phone'],
        description=request.form['description'],
        image_data=main_image_data,
        image_type=main_image_type,
        user_id=session['user_id'],
        is_public=True
    )
    db.session.add(new_image)
    db.session.commit()
    
    # Adicionar imagens adicionais
    for i, file in enumerate(files):
        if i != main_image_index:
            image_data = process_image(file)
            image_type = file.content_type
            
            new_additional_image = AdditionalImage(
                main_image_id=new_image.id,
                image_data=image_data,
                image_type=image_type
            )
            db.session.add(new_additional_image)
    
    db.session.commit()
    flash('Imagens enviadas com sucesso!')
    return redirect(url_for('index'))

def process_image(file):
    # Ler a imagem
    img = PILImage.open(file)
    
    # Corrigir a orientação da imagem
    if hasattr(img, '_getexif'):
        exif = img._getexif()
        if exif is not None:
            orientation = exif.get(274)  # 274 é o código EXIF para orientação
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

@app.route('/add_images', methods=['POST'])
def add_images():
    image_id = request.form.get('image_id')
    if not image_id:
        flash('Selecione uma imagem principal')
        return redirect(url_for('index'))
    
    main_image = Image.query.get_or_404(image_id)
    
    if 'additional_images' not in request.files:
        flash('Nenhum arquivo selecionado')
        return redirect(url_for('index'))
    
    files = request.files.getlist('additional_images')
    if not files or files[0].filename == '':
        flash('Nenhum arquivo selecionado')
        return redirect(url_for('index'))
    
    if len(files) > 10:
        flash('Você pode adicionar no máximo 10 imagens extras')
        return redirect(url_for('index'))
    
    for file in files:
        if file:
            image_data = process_image(file)
            image_type = file.content_type
            
            new_additional_image = AdditionalImage(
                main_image_id=image_id,
                image_data=image_data,
                image_type=image_type
            )
            db.session.add(new_additional_image)
    
    db.session.commit()
    flash('Imagens extras adicionadas com sucesso!')
    return redirect(url_for('index'))

@app.route('/like/<int:image_id>', methods=['POST'])
def like(image_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Você precisa estar logado para reagir'}), 401
    
    image = Image.query.get_or_404(image_id)
    user_id = session['user_id']
    
    # Verifica se já existe uma reação
    reaction = Reaction.query.filter_by(user_id=user_id, image_id=image_id).first()
    
    if reaction:
        if reaction.is_like:
            return jsonify({'error': 'Você já curtiu esta imagem'}), 400
        reaction.is_like = True
    else:
        reaction = Reaction(user_id=user_id, image_id=image_id, is_like=True)
        db.session.add(reaction)
    
    db.session.commit()
    return jsonify({
        'likes': Reaction.query.filter_by(image_id=image_id, is_like=True).count(),
        'dislikes': Reaction.query.filter_by(image_id=image_id, is_like=False).count()
    })

@app.route('/dislike/<int:image_id>', methods=['POST'])
def dislike(image_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Você precisa estar logado para reagir'}), 401
    
    image = Image.query.get_or_404(image_id)
    user_id = session['user_id']
    
    # Verifica se já existe uma reação
    reaction = Reaction.query.filter_by(user_id=user_id, image_id=image_id).first()
    
    if reaction:
        if not reaction.is_like:
            return jsonify({'error': 'Você já não curtiu esta imagem'}), 400
        reaction.is_like = False
    else:
        reaction = Reaction(user_id=user_id, image_id=image_id, is_like=False)
        db.session.add(reaction)
    
    db.session.commit()
    return jsonify({
        'likes': Reaction.query.filter_by(image_id=image_id, is_like=True).count(),
        'dislikes': Reaction.query.filter_by(image_id=image_id, is_like=False).count()
    })

@app.route('/delete/<int:image_id>', methods=['POST'])
def delete_image(image_id):
    password = request.form.get('password')
    if password == '2121':
        image = Image.query.get_or_404(image_id)
        db.session.delete(image)
        db.session.commit()
        flash('Imagem deletada com sucesso!')
    else:
        flash('Senha incorreta!')
    return redirect(url_for('index'))

@app.route('/search')
def search():
    query = request.args.get('q', '')
    images = Image.query.filter(
        (Image.name.contains(query)) | 
        (Image.description.contains(query))
    ).all()
    return render_template('index.html', images=images, query=query)

if __name__ == '__main__':
    app.run(debug=True) 