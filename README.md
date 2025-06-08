# Rede Social

Uma rede social simples onde os usuários podem criar posts com fotos, curtir e comentar em posts de outros usuários.

## Funcionalidades

- Cadastro e login de usuários
- Criação de posts com texto e imagens
- Curtir posts
- Comentar em posts
- Pesquisar posts
- Feed aleatório de posts
- Perfil de usuário com foto

## Requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

## Instalação

1. Clone o repositório:
```bash
git clone [URL_DO_REPOSITÓRIO]
cd [NOME_DO_DIRETÓRIO]
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
```

3. Ative o ambiente virtual:
- Windows:
```bash
venv\Scripts\activate
```
- Linux/Mac:
```bash
source venv/bin/activate
```

4. Instale as dependências:
```bash
pip install -r requirements.txt
```

5. Crie o banco de dados:
```bash
flask db init
flask db migrate
flask db upgrade
```

6. Crie a pasta para uploads:
```bash
mkdir static/uploads
```

## Executando a aplicação

1. Ative o ambiente virtual (se ainda não estiver ativo)

2. Execute o servidor:
```bash
flask run
```

3. Acesse a aplicação em seu navegador:
```
http://localhost:5000
```

## Estrutura do Projeto

```
.
├── app.py              # Arquivo principal da aplicação
├── requirements.txt    # Dependências do projeto
├── schema.sql         # Schema do banco de dados
├── static/            # Arquivos estáticos
│   └── uploads/       # Pasta para uploads de imagens
└── templates/         # Templates HTML
    ├── base.html      # Template base
    ├── index.html     # Página inicial
    ├── login.html     # Página de login
    ├── register.html  # Página de registro
    ├── search.html    # Página de pesquisa
    └── random.html    # Página de posts aleatórios
```

## Contribuindo

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Faça commit das suas alterações (`git commit -m 'Adiciona nova feature'`)
4. Faça push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para mais detalhes. "# nossoanucio" 
