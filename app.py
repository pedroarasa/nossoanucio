from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://neondb_owner:npg_izJKD7Qm0kEh@ep-wandering-resonance-a9e1300q-pooler.gwc.azure.neon.tech/neondb?sslmode=require'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

db = SQLAlchemy(app)

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    image_data = db.Column(db.LargeBinary, nullable=False)
    image_type = db.Column(db.String(20), nullable=False)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Image {self.name}>'

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
        image.image_data,
        mimetype=image.image_type,
        as_attachment=False
    )

@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        flash('Nenhum arquivo selecionado')
        return redirect(request.url)
    
    file = request.files['image']
    if file.filename == '':
        flash('Nenhum arquivo selecionado')
        return redirect(request.url)
    
    if file:
        image_data = file.read()
        image_type = file.content_type
        
        new_image = Image(
            name=request.form['name'],
            phone=request.form['phone'],
            description=request.form['description'],
            image_data=image_data,
            image_type=image_type
        )
        db.session.add(new_image)
        db.session.commit()
        
        flash('Imagem enviada com sucesso!')
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

@app.route('/search')
def search():
    query = request.args.get('q', '')
    images = Image.query.filter(
        (Image.name.contains(query)) | 
        (Image.description.contains(query))
    ).all()
    return render_template('index.html', images=images, query=query)

@app.route('/delete_all', methods=['POST'])
def delete_all():
    password = request.form.get('password')
    if password == '2121':
        Image.query.delete()
        db.session.commit()
        flash('Todas as imagens foram deletadas com sucesso!')
    else:
        flash('Senha incorreta!')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True) 