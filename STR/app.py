from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from datetime import datetime
import hashlib

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Conectar ao MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client['sistema_ponto']
funcionarios_collection = db['funcionarios']
pontos_collection = db['pontos']

# Função para criptografar a senha
def criptografar_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

# Função para inserir o administrador se ele não existir
def criar_admin():
    admin_user = "AdminPV"
    admin_password = "Abacate123"
    # Verifica se o administrador já existe no banco
    if not funcionarios_collection.find_one({'usuario': admin_user}):
        admin = {
            'nome_completo': 'Administrador',
            'usuario': admin_user,
            'senha': criptografar_senha(admin_password),
            'data_cadastro': datetime.utcnow().strftime('%Y-%m-%d'),
            'role': 'admin'  # Papel específico para o administrador
        }
        funcionarios_collection.insert_one(admin)
        print("Usuário administrador criado com sucesso.")
    else:
        print("Usuário administrador já existe.")

# Cria o administrador ao iniciar o aplicativo
criar_admin()

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def do_login():
    usuario = request.form['username']
    senha = criptografar_senha(request.form['password'])

    funcionario = funcionarios_collection.find_one({'usuario': usuario, 'senha': senha})
    if funcionario:
        session['funcionario_id'] = str(funcionario['_id'])
        session['nome'] = funcionario['nome_completo']
        session['role'] = funcionario.get('role', 'funcionario')

        # Salva o ponto do login
        ponto = {
            'funcionario_id': funcionario['_id'],
            'data_ponto': datetime.utcnow().strftime('%Y-%m-%d'),
            'hora_entrada': datetime.utcnow().strftime('%H:%M:%S')
        }
        pontos_collection.insert_one(ponto)

        # Verifica se o usuário é administrador e redireciona para a página de cadastro
        if session['role'] == 'admin':
            return redirect(url_for('cadastro'))
        else:
            return redirect(url_for('index'))
    else:
        return "Login falhou. Verifique seu nome de usuário e senha."

@app.route('/index')
def index():
    if 'nome' in session:
        return f"Bem-vindo, {session['nome']}! Seu ponto foi registrado."
    else:
        return redirect(url_for('login'))

@app.route('/cadastro')
def cadastro():
    if 'role' in session and session['role'] == 'admin':
        return render_template('cadastro.html')
    return redirect(url_for('login'))

@app.route('/register', methods=['POST'])
def do_register():
    nome_completo = request.form['fullname']
    usuario = request.form['username']
    senha = criptografar_senha(request.form['password'])

    novo_funcionario = {
        'nome_completo': nome_completo,
        'usuario': usuario,
        'senha': senha,
        'data_cadastro': datetime.utcnow().strftime('%Y-%m-%d')
    }
    funcionarios_collection.insert_one(novo_funcionario)

    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
