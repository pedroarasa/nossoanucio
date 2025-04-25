# Sistema de Upload de Imagens

Este é um sistema de upload de imagens com funcionalidades de curtir/não curtir, pesquisa e gerenciamento de conteúdo.

## Funcionalidades

- Upload de imagens com nome, telefone e descrição
- Sistema de curtidas e não curtidas
- Barra de pesquisa para encontrar imagens específicas
- Botão de deletar tudo com senha (2121)
- Armazenamento no banco de dados PostgreSQL Neon
- Interface responsiva e moderna

## Requisitos

- Python 3.8 ou superior
- PostgreSQL Neon (banco de dados)
- Dependências listadas no requirements.txt

## Instalação

1. Clone o repositório
2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Crie a pasta para uploads:
```bash
mkdir static/uploads
```

## Executando o Projeto

1. Ative o ambiente virtual (se ainda não estiver ativado)
2. Execute o aplicativo:
```bash
python app.py
```

3. Acesse o sistema em: http://localhost:5000

## Deploy no Render

1. Crie uma nova aplicação Web no Render
2. Conecte com seu repositório GitHub
3. Configure as seguintes variáveis de ambiente:
   - `FLASK_APP=app.py`
   - `FLASK_ENV=production`
   - `SECRET_KEY=sua_chave_secreta_aqui`

4. O Render irá automaticamente detectar o Python e instalar as dependências

## Uso

- Para fazer upload: Preencha o formulário com imagem, nome, telefone e descrição
- Para pesquisar: Use a barra de pesquisa no topo da página
- Para deletar tudo: Digite a senha 2121 no campo de senha
- Para curtir/não curtir: Use os botões abaixo de cada imagem 