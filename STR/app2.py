from flask import Flask, render_template, request, redirect, url_for, session, send_file
from pymongo import MongoClient
from datetime import datetime
import hashlib
import openpyxl
from io import BytesIO
import pytz

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
    if not funcionarios_collection.find_one({'usuario': admin_user}):
        admin = {
            'nome_completo': 'Administrador',
            'usuario': admin_user,
            'senha': criptografar_senha(admin_password),
            'data_cadastro': datetime.now().strftime('%Y-%m-%d'),
            'role': 'admin'
        }
        funcionarios_collection.insert_one(admin)
        print("Usuário administrador criado com sucesso.")
    else:
        print("Usuário administrador já existe.")

# Cria o administrador ao iniciar o aplicativo
criar_admin()

# Função para obter a data e hora no fuso horário local
def horario_local():
    fuso_br = pytz.timezone("America/Sao_Paulo")
    return datetime.now(fuso_br)

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

        if session['role'] == 'admin':
            return redirect(url_for('cadastro'))
        else:
            ano_mes = horario_local().strftime('%Y-%m')
            data_atual = horario_local().strftime('%Y-%m-%d')
            hora_atual = horario_local().strftime('%H:%M:%S')
            
            ponto_mensal = pontos_collection.find_one({'funcionario_id': funcionario['_id'], 'mes_ano': ano_mes})
            if not ponto_mensal:
                ponto_mensal = {
                    'funcionario_id': funcionario['_id'],
                    'mes_ano': ano_mes,
                    'dias': {}
                }
                pontos_collection.insert_one(ponto_mensal)

            ponto_dia = ponto_mensal['dias'].get(data_atual, {
                'hora_entrada': None,
                'hora_saida': None,
                'hora_entrada2': None,
                'hora_saida2': None
            })

            if not ponto_dia['hora_entrada']:
                ponto_dia['hora_entrada'] = hora_atual
            elif not ponto_dia['hora_saida']:
                ponto_dia['hora_saida'] = hora_atual
            elif not ponto_dia['hora_entrada2']:
                ponto_dia['hora_entrada2'] = hora_atual
            elif not ponto_dia['hora_saida2']:
                ponto_dia['hora_saida2'] = hora_atual

            ponto_mensal['dias'][data_atual] = ponto_dia
            pontos_collection.update_one({'_id': ponto_mensal['_id']}, {'$set': {'dias': ponto_mensal['dias']}})

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
        'data_cadastro': horario_local().strftime('%Y-%m-%d')
    }
    funcionarios_collection.insert_one(novo_funcionario)

    return redirect(url_for('login'))

@app.route('/gerar_relatorio')
def gerar_relatorio():
    ano_mes = request.args.get('mes')  # Exemplo: '2024-01' para janeiro de 2024
    if not ano_mes:
        return "Por favor, forneça um mês no formato AAAA-MM."

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = f"Relatório de Pontos - {ano_mes}"
    sheet.append(["Nome Completo", "Data", "Hora Entrada", "Hora Saída", "Hora Entrada 2", "Hora Saída 2"])

    funcionarios = funcionarios_collection.find({'role': {'$ne': 'admin'}})
    for funcionario in funcionarios:
        pontos = pontos_collection.find_one({'funcionario_id': funcionario['_id'], 'mes_ano': ano_mes})
        if pontos:
            for data, ponto in pontos['dias'].items():
                sheet.append([
                    funcionario['nome_completo'],
                    data,
                    ponto.get('hora_entrada', ''),
                    ponto.get('hora_saida', ''),
                    ponto.get('hora_entrada2', ''),
                    ponto.get('hora_saida2', '')
                ])

    file_stream = BytesIO()
    workbook.save(file_stream)
    file_stream.seek(0)

    return send_file(file_stream, as_attachment=True, download_name=f"relatorio_pontos_{ano_mes}.xlsx")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

#/gerar_relatorio?mes=2024-11
