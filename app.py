from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import base64
from io import BytesIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://neondb_owner:npg_izJKD7Qm0kEh@ep-wandering-resonance-a9e1300q-pooler.gwc.azure.neon.tech/neondb?sslmode=require'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

db = SQLAlchemy(app)

class Image(db.Model):
    __tablename__ = 'image'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    image_data = db.Column(db.LargeBinary, nullable=False)
    image_type = db.Column(db.String(20), nullable=False)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    additional_images = db.relationship('AdditionalImage', backref='main_image', lazy=True, cascade="all, delete-orphan")

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

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    images = Image.query.order_by(Image.upload_date.desc()).all()
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

@app.route('/upload', methods=['POST'])
def upload():
    if 'images' not in request.files:
        flash('Nenhum arquivo selecionado')
        return redirect(url_for('index'))
    
    files = request.files.getlist('images')
    if not files or files[0].filename == '':
        flash('Nenhum arquivo selecionado')
        return redirect(url_for('index'))
    
    if len(files) > 10:
        flash('Você pode adicionar no máximo 10 imagens')
        return redirect(url_for('index'))
    
    main_image_index = int(request.form.get('main_image_index', 0))
    if main_image_index >= len(files):
        flash('Índice da imagem principal inválido')
        return redirect(url_for('index'))
    
    # Criar o registro principal
    main_image = files[main_image_index]
    main_image_data = main_image.read()
    main_image_type = main_image.content_type
    
    new_image = Image(
        name=request.form['name'],
        phone=request.form['phone'],
        description=request.form['description'],
        image_data=main_image_data,
        image_type=main_image_type
    )
    db.session.add(new_image)
    db.session.commit()
    
    # Adicionar imagens adicionais
    for i, file in enumerate(files):
        if i != main_image_index:
            image_data = file.read()
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
            image_data = file.read()
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
    image = Image.query.get_or_404(image_id)
    image.likes += 1
    db.session.commit()
    return jsonify({'likes': image.likes})

@app.route('/dislike/<int:image_id>', methods=['POST'])
def dislike(image_id):
    image = Image.query.get_or_404(image_id)
    image.dislikes += 1
    db.session.commit()
    return jsonify({'dislikes': image.dislikes})

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