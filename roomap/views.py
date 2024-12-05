from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages
from django.http import HttpResponse
from django.utils.timezone import now
from mysql.connector import errorcode
import mysql.connector
from .models import (
    Reserva, Reservaadm, Equipamento, Docente, Sala, SalaView, ViewDadosDocentes,
    ReservaMesAdmin, ReservaDiaAtualAdmin, Turno, ReservaMesDocente)
from django.contrib.auth.models import User
from .forms import DocenteForm
from django.db import connection, transaction
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
import json
from django.http import JsonResponse
from django.core.mail import send_mail
from django.utils.timezone import make_aware
from django.views.decorators.csrf import csrf_exempt

def inicio_view(request):
    if request.method == 'POST':
        if 'admin_button' in request.POST:
            return redirect('loginadmin')
        elif 'docente_button' in request.POST:
            return redirect('login')
    return render(request, 'roomap/inicio.html')


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            # Conexão com o banco de dados
            db_connection = mysql.connector.connect(
                host='localhost',
                user='tecmysql',
                password='devmysql',
                database='roomap'
            )
            cursor = db_connection.cursor(dictionary=True)

            # Consulta para verificar o e-mail e senha na tabela validacao
            query = "SELECT * FROM validacao WHERE email = %s AND senha = %s"
            cursor.execute(query, (email, password))
            valid_user = cursor.fetchone()

            if valid_user:
                # Armazena o e-mail na sessão para identificar o usuário logado
                request.session['email'] = valid_user['email']

                # Mensagem de sucesso e redirecionamento
                messages.success(request, f"Bem-vindo, {email}!")
                return redirect('homedocente')
            else:
                messages.error(request, "Email ou senha inválidos.")

        except mysql.connector.Error as err:
            messages.error(request, f"Erro ao acessar o banco de dados: {err}")
        finally:
            if 'db_connection' in locals():
                db_connection.close()

    return render(request, 'roomap/login.html')


def loginadmin_view(request):
    predefined_email = 'Admin@gmail.com'
    predefined_password = '1234'

    request.session['nome_adm'] = predefined_email
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Verifica se o email e a senha são os predefinidos
        if email == predefined_email and password == predefined_password:
            # Verifica se o usuário existe no banco de dados
            user, created = User.objects.get_or_create(username=email, email=email)

            if created:
                # Define uma senha padrão (não deve ser usada para autenticação real)
                user.set_password(predefined_password)
                user.save()

            # Autentica o usuário manualmente
            auth_login(request, user)
            messages.success(request, "Login bem-sucedido! Bem-vindo, admin.")
            return redirect('homeadmin')
        else:
            messages.error(request, "Falha no login. Email ou senha incorretos.")

    return render(request, 'roomap/loginadmin.html')


def cadastro_view(request):
    if request.method == 'POST':
        form = DocenteForm(request.POST)

        if form.is_valid():
            nome_doc = form.cleaned_data['nome_doc']
            email_doc = form.cleaned_data['email_doc']
            senha_doc = form.cleaned_data['senha_doc']
            cargo_doc = form.cleaned_data['cargo_doc']
            tel_doc = form.cleaned_data['tel_doc']

            try:
                # Conectar ao banco de dados
                db_connection = mysql.connector.connect(
                    host='localhost',
                    user='tecmysql',
                    password='devmysql',
                    database='roomap'
                )

                # Criar cursor
                cursor = db_connection.cursor()

                # Comando SQL para inserção
                sql = """
                        INSERT INTO docentes (nome_doc, email_doc, senha_doc, cargo_doc, tel_doc) 
                        VALUES (%s, %s, %s, %s, %s)
                    """
                docente = (nome_doc, email_doc, senha_doc, cargo_doc, tel_doc)

                # Executar a inserção
                cursor.execute(sql, docente)

                # Confirmar a transação
                db_connection.commit()

                messages.success(request, 'Docente cadastrado com sucesso!')

                # Redirecionar para a página de cadastro de reservas
                return redirect('login')

            except mysql.connector.Error as err:
                messages.error(request, f"Erro ao cadastrar docente: {err}")

            finally:
                if 'db_connection' in locals():
                    db_connection.close()

    else:
        form = DocenteForm()

    return render(request, 'roomap/cadastro.html', {'form': form})

def homedocente_view(request):
    # Função para deletar reservas expiradas (implementação não mostrada aqui)
    deletar_reservas_expiradas()

    # Obter a data atual
    hoje = now().date()

    # Obter o e-mail do docente da sessão
    email_docente = request.session.get('email')
    if not email_docente:
        # Caso o e-mail não esteja na sessão, redirecionar para a página de login
        return redirect('login')

    # Query SQL para buscar reservas apenas do dia atual para o docente logado
    query = """
            SELECT r.id_reserva, r.data_hora_inicio, r.data_hora_fim, r.status_reserva, r.email_doc, r.id_sala, s.nome_sala
            FROM reservas r
            JOIN salas s ON r.id_sala = s.id_sala
            WHERE DATE(r.data_hora_inicio) = %s AND r.email_doc = %s
        """
    with connection.cursor() as cursor:
        cursor.execute(query, [hoje, email_docente])
        reservas = cursor.fetchall()

    # Formatar os dados das reservas para uso no template
    reservas_formatadas = [
        {
            'id': reserva[0],
            'data_hora_inicio': reserva[1],
            'data_hora_fim': reserva[2],
            'status_reserva': reserva[3],
            'email_doc': reserva[4],
            'id_sala': reserva[5],  # Agora estamos mantendo o id_sala para controle de status
            'nome_sala': reserva[6]  # Nome da sala
        }
        for reserva in reservas
    ]

    # Obter todas as salas do banco de dados
    salas = Sala.objects.all()

    # Criar um dicionário para rastrear o status de cada sala
    salas_status = {}
    for reserva in reservas_formatadas:
        id_sala = reserva['id_sala']  # Agora temos o id_sala disponível
        salas_status[id_sala] = 'reservada'  # Se a sala tem uma reserva, marcamos como 'reservada'

    # Garantir que salas sem reservas sejam marcadas como 'disponível'
    total_salas = 27  # Atualize conforme o número de salas no banco
    for id_sala in range(1, total_salas + 1):
        if id_sala not in salas_status:
            salas_status[id_sala] = 'disponível'

    # Renderizar o template com os dados
    return render(request, 'roomap/homedocente.html', {
        'reservas': reservas_formatadas,  # Dados das reservas do dia atual do docente
        'salas': salas,                   # Todas as salas
        'salas_status': salas_status      # Status das salas (reservada ou disponível)
    })

def homeadmin_view(request):

    deletar_reservas_expiradas_admin()

    # Obter a data atual
    hoje = now().date()

    # Verificar se o nome do administrador está na sessão
    nome_adm = request.session.get('nome_adm')
    if not nome_adm:
        # Caso não esteja na sessão, redirecionar para a página de login
        return redirect('login')

    # Query SQL para buscar reservas do dia atual feitas pelos administradores
    query = """
            SELECT r.id_reserva, r.data_hora_inicio, r.data_hora_fim, r.status_reserva, r.nome_adm, r.id_sala, s.nome_sala, t.nome_turno
            FROM reservasadmin r
            JOIN salas s ON r.id_sala = s.id_sala
            JOIN turnos t ON r.turno_id = t.id_turno
            WHERE DATE(r.data_hora_inicio) = %s AND r.nome_adm = %s
        """
    with connection.cursor() as cursor:
        cursor.execute(query, [hoje, nome_adm])
        reservas = cursor.fetchall()

    # Formatar os dados das reservas para uso no template
    reservas_formatadas = [
        {
            'id': reserva[0],
            'data_hora_inicio': reserva[1],
            'data_hora_fim': reserva[2],
            'status_reserva': reserva[3],
            'nome_adm': reserva[4],
            'id_sala': reserva[5],
            'nome_sala': reserva[6],
            'nome_turno': reserva[7],
        }
        for reserva in reservas
    ]

    # Obter todas as salas do banco de dados
    salas = Sala.objects.all()

    # Criar um dicionário para rastrear o status de cada sala
    salas_status = {}
    for reserva in reservas_formatadas:
        id_sala = reserva['id_sala']
        salas_status[id_sala] = 'reservada'

    # Garantir que salas sem reservas sejam marcadas como 'disponível'
    total_salas = 27  # Atualize conforme o número de salas no banco
    for id_sala in range(1, total_salas + 1):
        if id_sala not in salas_status:
            salas_status[id_sala] = 'disponível'

    # Renderizar o template com os dados
    return render(request, 'roomap/homeadmin.html', {
        'reservas': reservas_formatadas,  # Dados das reservas do dia atual dos administradores
        'salas': salas,                   # Todas as salas
        'salas_status': salas_status      # Status das salas (reservada ou disponível)
    })


def reserva_sala_view(request):
    # Obtém o ID da sala a partir da URL
    sala_id = request.GET.get('sala_id')

    # Busca os dados da sala específica na view do MySQL
    sala = get_object_or_404(SalaView, id_sala=sala_id)
    # Renderiza o template com os dados da sala

    turnos = Turno.objects.all()
    return render(request, 'roomap/reservaadmin.html', {'sala': sala, 'turnos': turnos})

def reserva_sala_view_docente(request):
    sala_id = request.GET.get('sala_id')

    sala = get_object_or_404(SalaView, id_sala=sala_id)

    turnos = Turno.objects.all()
    return render(request, 'roomap/reservadocente.html', {'sala': sala, 'turnos': turnos})

def reservas_do_dia_admin(request):
    reservas = ReservaDiaAtualAdmin.objects.only('nome_sala', 'data_hora_inicio', 'data_hora_fim')
    return render(request, 'roomap/homeadmin.html', {'reservas': reservas})

def reservas_do_dia_docente(request):
    return render(request, 'roomap/homedocente.html')
def inventariodocente_view(request):
    equipamentos = Equipamento.objects.all()
    return render(request, 'roomap/inventariodocente.html', {'equipamentos': equipamentos})

def inventarioadmin_view(request):
    equipamentos = Equipamento.objects.all()
    return render(request, 'roomap/inventarioadmin.html', {'equipamentos': equipamentos})

def exluir_maquina_view(request):
    return render(request, 'roomap/inventarioadmin.html')

def listafuncionarios_view(request):
    docentes = Docente.objects.all()  # Busca todos os docentes do banco de dados
    return render(request, 'roomap/listafuncionarios.html', {'docentes': docentes})

#FUNÇÃO DA PÁGINA DE ADICIONAR UMA NOVA MAQUINA (ADMIN)
def addmaquina_view(request):
    if request.method == 'POST':
        nome_equip = request.POST.get('nome_equip')
        loc_equip = request.POST.get('loc_equip')
        desc_equip = request.POST.get('desc_equip')
        status_equip = request.POST.get('status_equip')
        quant_equip = request.POST.get('quant_equip')

        try:
            # Conectar ao banco de dados
            db_connection = mysql.connector.connect(
                host='localhost',
                user='tecmysql',
                password='devmysql',
                database='roomap'
            )
            print("Conexão realizada com sucesso!")

            # Criar cursor
            cursor = db_connection.cursor()

            # Comando SQL para inserir na tabela equipamentos
            sql_equipamento = """
                    INSERT INTO equipamentos (nome_equip, loc_equip, desc_equip, status_equip, quant_equip)
                    VALUES (%s, %s, %s, %s, %s)
                """
            equipamentos = (nome_equip, loc_equip, desc_equip, status_equip, quant_equip)

            # Executar a inserção de equipamento
            cursor.execute(sql_equipamento, equipamentos)
            db_connection.commit()
            print("Equipamento inserido!")

            messages.success(request, 'Equipamento registrado com sucesso!')

            # Redirecionar para a página de equipamentos
            return redirect('addmaquina')

        except mysql.connector.Error as err:
            print(f"Erro: {err}")
            messages.error(request, 'Ocorreu um erro ao tentar registrar o equipamento.')
            return redirect('addmaquina')
        finally:
            cursor.close()
            db_connection.close()
    return render(request, 'roomap/addmaquina.html')

def addfuncionario_view(request):
    if request.method == 'POST':
        nome_doc = request.POST.get('nome_doc')
        email_doc = request.POST.get('email_doc')
        senha_doc = request.POST.get('senha_doc')
        cargo_doc = request.POST.get('cargo_doc')
        tel_doc = request.POST.get('tel_doc')

        try:
            # Conectar ao banco de dados
            db_connection = mysql.connector.connect(
                host='localhost',
                user='tecmysql',
                password='devmysql',
                database='roomap'
            )
            print("Conexão realizada com sucesso!")

            # Criar cursor
            cursor = db_connection.cursor()

            # Comando SQL para inserir na tabela docentes
            sql_docente = """
                        INSERT INTO docentes (nome_doc, email_doc, senha_doc, cargo_doc, tel_doc)
                        VALUES (%s, %s, %s, %s, %s)
                    """
            docentes = (nome_doc, email_doc, senha_doc, cargo_doc, tel_doc)

            # Executar a inserção de docente
            cursor.execute(sql_docente, docentes)
            db_connection.commit()
            print("Docente inserido!")

            messages.success(request, 'Docente registrado com sucesso!')

            # Redirecionar para a página de adicionar docente
            return redirect('addfuncionario')

        except mysql.connector.Error as err:
            print(f"Erro: {err}")
            messages.error(request, 'Ocorreu um erro ao tentar registrar o docente.')
            return redirect('addfuncionario')
        finally:
            cursor.close()
            db_connection.close()

    return render(request, 'roomap/addfuncionario.html')

def perfil_view(request):
    # Verifica se o e-mail do usuário está na sessão
    email = request.session.get('email')
    if email:
        try:
            db_connection = mysql.connector.connect(
                host='localhost',
                user='tecmysql',
                password='devmysql',
                database='roomap'
            )
            cursor = db_connection.cursor(dictionary=True)
            query = "SELECT nome_doc, cargo_doc, email_doc FROM docentes WHERE email_doc = %s"
            cursor.execute(query, (email,))
            docente_info = cursor.fetchone()

        except mysql.connector.Error as err:
            docente_info = None
        finally:
            if 'db_connection' in locals():
                db_connection.close()
    else:
        docente_info = None

    return render(request, 'roomap/perfil.html', {
        'docente_info': docente_info,
    })

def editarperfil_view(request):
    # Recupera o e-mail do docente logado (usando sessão)
    email_logado = request.session.get('email')  # Assumindo que o email do login está salvo na sessão

    if not email_logado:
        messages.error(request, 'Você precisa estar logado para editar seu perfil.')
        return redirect('login')  # Redireciona para a página de login

    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='tecmysql',
            password='devmysql',
            database='roomap'
        )

        cursor = connection.cursor(dictionary=True)

        # Consulta para buscar os dados do docente logado
        select_query = "SELECT nome_doc, email_doc, cargo_doc, senha_doc FROM docentes WHERE email_doc = %s"
        cursor.execute(select_query, (email_logado,))
        docente = cursor.fetchone()

        if not docente:
            messages.error(request, 'Docente não encontrado.')
            return redirect('perfil')  # Redireciona para o perfil

        if request.method == 'POST':
            # Captura os dados enviados pelo formulário
            nome = request.POST.get('nome')
            email = request.POST.get('email')
            cargo = request.POST.get('cargo')
            senha = request.POST.get('senha')  # Captura a nova senha do formulário

            # Atualizando os dados na tabela 'docentes'
            update_docente_query = """UPDATE docentes 
                                       SET nome_doc = %s, email_doc = %s, cargo_doc = %s, senha_doc = %s 
                                       WHERE email_doc = %s"""
            cursor.execute(update_docente_query, (nome, email, cargo, senha, email_logado))

            # Atualizando os dados na tabela 'validacao'
            update_validacao_query = """UPDATE validacao 
                                        SET email = %s, senha = %s 
                                        WHERE email = %s"""
            cursor.execute(update_validacao_query, (email, senha, email_logado))

            connection.commit()

            if cursor.rowcount > 0:
                # Atualiza o email na sessão se ele for alterado
                request.session['email'] = email
                messages.success(request, 'Dados atualizados com sucesso!')
                return redirect('editarperfil')  # Redireciona para a mesma página
            else:
                messages.error(request, 'Nenhuma alteração feita.')

    except mysql.connector.Error as err:
        messages.error(request, f'Erro: {err}')
    finally:
        # Fechando a conexão com o banco
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

    return render(request, 'roomap/editarperfil.html', {'docente': docente})


def agendaadmin_view(request):
    # Buscar todas as reservas
    reservas = Reservaadm.objects.all()

    # Formatar os dados para enviar ao frontend
    reservas_formatadas = [
        {
            'data_inicio': reserva.data_hora_inicio.strftime('%Y-%m-%d'),  # Apenas a data
            'data_fim': reserva.data_hora_fim.strftime('%Y-%m-%d'),
            'status': reserva.status_reserva,
            'nome_adm': reserva.nome_adm,
            'id_sala': reserva.sala
        }
        for reserva in reservas
    ]

    return render(request, 'roomap/agendaadmin.html', {'reservas': reservas_formatadas})

def salas_view(request):
    salas = Sala.objects.all()
    return render(request, 'roomap/salas.html', {'salas': salas})

def mapa_view(request):
    deletar_reservas_expiradas()

    query = """
        SELECT id_reserva, data_hora_inicio, data_hora_fim, status_reserva, email_doc, id_sala
        FROM reservas
        UNION
        SELECT id_reserva, data_hora_inicio, data_hora_fim, status_reserva, nome_adm AS email_doc, id_sala
        FROM reservasadmin
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        reservas = cursor.fetchall()

    # Formatar as reservas em um dicionário
    reservas_formatadas = [
        {
            'id': reserva[0],
            'data_hora_inicio': reserva[1],
            'data_hora_fim': reserva[2],
            'status_reserva': reserva[3],
            'email_doc': reserva[4],  # Aqui pode ser o email do docente ou nome do admin
            'id_sala': reserva[5],
        }
        for reserva in reservas
    ]

    salas_status = {}
    for reserva in reservas_formatadas:
        id_sala = reserva['id_sala']
        salas_status[id_sala] = 'reservada'  # Se há uma reserva, marcamos como 'reservada'

    # Garantir que salas sem reservas sejam marcadas como 'disponível'
    total_salas = 27  # Atualize este número de acordo com a quantidade total de salas no mapa
    for id_sala in range(1, total_salas + 1):
        if id_sala not in salas_status:
            salas_status[id_sala] = 'disponível'

    return render(request, 'roomap/mapa.html', {
        'tabelas': reservas_formatadas,
        'salas_status': salas_status  # Passar o status das salas ao template
    })
def deletar_reservas_expiradas():
    agora = datetime.now()
    with connection.cursor() as cursor:
        # Excluir todas as reservas onde data_hora_fim já passou
        cursor.execute("DELETE FROM reservas WHERE data_hora_fim < %s", [agora]) # função que deleta as reservas inspiradas.

def relatorio_admin(request):
    # Verifica se o administrador está logado
    nome_adm_logado = request.session.get('nome_adm')
    print("Admin logado:", nome_adm_logado)

    if not nome_adm_logado:
        mensagem = """
        <html>
        <head>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f7f7f7;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }
                .message-container {
                    text-align: center;
                    background: #ffffff;
                    border-radius: 10px;
                    padding: 50px;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
                    max-width: 600px;
                    width: 90%;
                }
                .message-container h1 {
                    font-size: 32px;
                    color: #333;
                    margin-bottom: 20px;
                }
                .message-container p {
                    font-size: 18px;
                    color: #666;
                    margin-bottom: 30px;
                }
                .message-container a {
                    text-decoration: none;
                    color: #fff;
                    background: #007BFF;
                    padding: 15px 30px;
                    border-radius: 5px;
                    font-size: 16px;
                    font-weight: bold;
                }
                .message-container a:hover {
                    background: #0056b3;
                }
            </style>
        </head>
        <body>
            <div class="message-container">
                <h1>Acesso Negado</h1>
                <p>Você precisa estar logado como administrador para acessar esta funcionalidade.</p>
                <a href="/homeadmin/">Voltar para Home</a>
            </div>
        </body>
        </html>
        """
        return HttpResponse(mensagem)

    # Busca as reservas na view do MySQL
    reservas = ReservaMesAdmin.objects.all()  # Teste sem filtro
    print("Todas as reservas:", list(reservas))

    # Debug: Verifique o queryset no terminal
    print("Reservas encontradas:", list(reservas))

    if not reservas.exists():
        mensagem = """
        <html>
        <head>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f7f7f7;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }
                .message-container {
                    text-align: center;
                    background: #ffffff;
                    border-radius: 10px;
                    padding: 50px;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
                    max-width: 600px;
                    width: 90%;
                }
                .message-container h1 {
                    font-size: 32px;
                    color: #333;
                    margin-bottom: 20px;
                }
                .message-container p {
                    font-size: 18px;
                    color: #666;
                    margin-bottom: 30px;
                }
                .message-container a {
                    text-decoration: none;
                    color: #fff;
                    background: #007BFF;
                    padding: 15px 30px;
                    border-radius: 5px;
                    font-size: 16px;
                    font-weight: bold;
                }
                .message-container a:hover {
                    background: #0056b3;
                }
            </style>
        </head>
        <body>
            <div class="message-container">
                <h1>Nenhuma Reserva Encontrada</h1>
                <p>Não há reservas registradas para este administrador no último mês.</p>
                <a href="/homeadmin/">Voltar para Home</a>
            </div>
        </body>
        </html>
        """
        return HttpResponse(mensagem)

    # Caso existam reservas, gere o PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="relatorio_admin.pdf"'

    # Configura o PDF
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    title_style = styles['Title']

    elements.append(Paragraph("Relatório de Reservas - Último Mês", title_style))

    data = [["ID", "Administrador", "Data Início", "Data Fim", "Status", "Sala", "Turno"]]
    for reserva in reservas:
        turno = reserva.turno_id if hasattr(reserva, 'turno_id') else "N/A"
        data.append([
            reserva.id_reserva,
            reserva.nome_adm,
            reserva.data_hora_inicio.strftime("%d/%m/%Y %H:%M"),
            reserva.data_hora_fim.strftime("%d/%m/%Y %H:%M"),
            reserva.status_reserva,
            reserva.id_sala,
            turno
        ])

    table = Table(data, hAlign='LEFT')
    elements.append(table)

    doc.build(elements)
    return response



def relatorio_docente(request):
    email_docente_logado = request.session.get('email_doc')
    print("Sessão atual:", request.session.items())  # Depuração

    if not email_docente_logado:
        print("Nenhum email_doc na sessão.")  # Mensagem para depuração
        mensagem = """
        <html>
        <head>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f7f7f7;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }
                .message-container {
                    text-align: center;
                    background: #ffffff;
                    border-radius: 10px;
                    padding: 50px;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
                    max-width: 600px;
                    width: 90%;
                }
                .message-container h1 {
                    font-size: 32px;
                    color: #333;
                    margin-bottom: 20px;
                }
                .message-container p {
                    font-size: 18px;
                    color: #666;
                    margin-bottom: 30px;
                }
                .message-container a {
                    text-decoration: none;
                    color: #fff;
                    background: #007BFF;
                    padding: 15px 30px;
                    border-radius: 5px;
                    font-size: 16px;
                    font-weight: bold;
                }
                .message-container a:hover {
                    background: #0056b3;
                }
            </style>
        </head>
        <body>
            <div class="message-container">
                <h1>Acesso Negado</h1>
                <p>Você precisa estar logado como docente para acessar esta funcionalidade.</p>
                <a href="/homedocente/">Voltar para Home</a>
            </div>
        </body>
        </html>
        """
        return HttpResponse(mensagem)

    # Prossiga com a lógica do relatório se `email_doc` estiver correto
    reservas = ReservaMesDocente.objects.filter(email_doc=email_docente_logado)
    print("Reservas encontradas:", list(reservas))

    if not reservas.exists():
        mensagem = """
        <html>
        <head>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f7f7f7;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                }
                .message-container {
                    text-align: center;
                    background: #ffffff;
                    border-radius: 10px;
                    padding: 50px;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
                    max-width: 600px;
                    width: 90%;
                }
                .message-container h1 {
                    font-size: 32px;
                    color: #333;
                    margin-bottom: 20px;
                }
                .message-container p {
                    font-size: 18px;
                    color: #666;
                    margin-bottom: 30px;
                }
                .message-container a {
                    text-decoration: none;
                    color: #fff;
                    background: #007BFF;
                    padding: 15px 30px;
                    border-radius: 5px;
                    font-size: 16px;
                    font-weight: bold;
                }
                .message-container a:hover {
                    background: #0056b3;
                }
            </style>
        </head>
        <body>
            <div class="message-container">
                <h1>Nenhuma Reserva Encontrada</h1>
                <p>Não há reservas registradas para este docente no último mês.</p>
                <a href="/homedocente/">Voltar para Home</a>
            </div>
        </body>
        </html>
        """
        return HttpResponse(mensagem)

    # Caso existam reservas, gere o PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="relatorio_docente.pdf"'

    # Configura o PDF
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    title_style = styles['Title']

    elements.append(Paragraph("Relatório de Reservas - Último Mês", title_style))

    data = [["ID", "Docente", "Data Início", "Data Fim", "Status", "Sala", "Turno"]]
    for reserva in reservas:
        turno = reserva.turno_id if hasattr(reserva, 'turno_id') else "N/A"
        data.append([
            reserva.id_reserva,
            reserva.email_doc,
            reserva.data_hora_inicio.strftime("%d/%m/%Y %H:%M"),
            reserva.data_hora_fim.strftime("%d/%m/%Y %H:%M"),
            reserva.status_reserva,
            reserva.id_sala,
            turno
        ])

    table = Table(data, hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                               ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                               ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                               ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                               ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                               ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                               ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                               ('GRID', (0, 0), (-1, -1), 1, colors.black),
                              ]))
    elements.append(table)

    doc.build(elements)
    return response

def send_help_email(request):
    if request.method == "POST":
        data = json.loads(request.body)
        message = data.get("message", "")

        if message.strip():
            send_mail(
                subject="Ajuda Solicitada",
                message=message,
                from_email="lucasbrazao@aluno.senai.br",  # Substitua pelo seu e-mail
                recipient_list=["lucasbrazao@aluno.senai.br"],  # Substitua pelo e-mail que receberá a mensagem
            )
            return JsonResponse({"success": True}, status=200)
        else:
            return JsonResponse({"error": "Mensagem vazia"}, status=400)
    return JsonResponse({"error": "Método não permitido"}, status=405)


def reservadocente_view(request):
    if request.method == 'GET':
        sala_id = request.GET.get('sala_id')
        sala = get_object_or_404(Sala, id_sala=sala_id)

        turnos = Turno.objects.all()

        email_doc = request.session.get('email', '')

        return render(request, 'roomap/reservadocente.html', {'turnos': turnos, 'sala': sala, 'email_doc': email_doc})

    if request.method == 'POST':
        email_doc = request.session.get('email', '')
        data_hora_inicio = request.POST.get('data_hora_inicio')
        data_hora_fim = request.POST.get('data_hora_fim')
        id_sala = request.POST.get('id_sala')
        turno_id = request.POST.get('turno')

        if not email_doc or not data_hora_inicio or not data_hora_fim or not turno_id:
            messages.error(request, "Todos os campos são obrigatórios.")
            return redirect(f'/reservadocente/?sala_id={id_sala}')

        try:
            turno = Turno.objects.get(id_turno=turno_id)
        except Turno.DoesNotExist:
            messages.error(request, "Turno inválido.")
            return redirect(f'/reservadocente/?sala_id={id_sala}')

        try:
            horario_inicio = make_aware(datetime.strptime(data_hora_inicio, "%Y-%m-%dT%H:%M"))
            horario_fim = make_aware(datetime.strptime(data_hora_fim, "%Y-%m-%dT%H:%M"))
        except ValueError:
            messages.error(request, "Horário inválido.")
            return redirect(f'/reservadocente/?sala_id={id_sala}')

        conflitos = Reserva.objects.filter(
            sala_id=id_sala,
            data_hora_inicio__lt=horario_fim,
            data_hora_fim__gt=horario_inicio
        )
        if conflitos.exists():
            messages.error(request, "Conflito com outra reserva.")
            return redirect(f'/reservadocente/?sala_id={id_sala}')

        try:
            reserva = Reserva.objects.create(
                data_hora_inicio=horario_inicio,
                data_hora_fim=horario_fim,
                status_reserva='Confirmada',
                email_doc=email_doc,  # Use o campo como string, não ForeignKey
                sala_id=id_sala,
                turno_id=turno_id
            )
            messages.success(request, 'Reserva feita com sucesso!')
            return redirect('homedocente')

        except Exception as error:
            messages.error(request, f"Erro ao salvar a reserva: {error}")
            return redirect(f'/reservadocente/?sala_id={id_sala}')

def agenda_view(request):
    # Recupera todas as reservas
    reservas = Reserva.objects.select_related('sala').all()

    # Serializa os eventos para o calendário
    eventos = [
        {
            "title": f"Sala: {reserva.sala.nome_sala}",
            "start": reserva.data_hora_inicio.strftime('%Y-%m-%dT%H:%M:%S'),
            "end": reserva.data_hora_fim.strftime('%Y-%m-%dT%H:%M:%S'),
            "status": reserva.status_reserva,
            "sala": reserva.sala.nome_sala,
            "docente": reserva.email_doc,
        }
        for reserva in reservas
    ]
    print(eventos)

    # Renderiza o template com os eventos
    return render(request, 'roomap/agenda.html', {"eventos": eventos})

def agendaadmin_view(request):
    # Recupera todas as reservas
    reservas = Reservaadm.objects.select_related('sala').all()

    # Serializa os eventos para o calendário
    eventos = [
        {
            "title": f"Sala: {reserva.sala.nome_sala}",
            "start": reserva.data_hora_inicio.strftime('%Y-%m-%dT%H:%M:%S'),
            "end": reserva.data_hora_fim.strftime('%Y-%m-%dT%H:%M:%S'),
            "status": reserva.status_reserva,
            "sala": reserva.sala.nome_sala,
            "admin": reserva.nome_adm,
        }
        for reserva in reservas
    ]
    print(eventos)

    # Renderiza o template com os eventos
    return render(request, 'roomap/agendaadmin.html', {"eventos": eventos})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from datetime import datetime
from .models import Sala, Turno, Reservaadm

def reservaadmin_view(request):
    if request.method == 'GET':
        sala_id = request.GET.get('sala_id')
        sala = get_object_or_404(Sala, id_sala=sala_id)
        turnos = Turno.objects.all()

        return render(request, 'roomap/reservaadmin.html', {'turnos': turnos, 'sala': sala})

    if request.method == 'POST':
        sala_id = request.POST.get('id_sala')
        nome_adm = request.POST.get('nome_adm')  # Certifique-se de que esse campo esteja no seu HTML
        turno_id = request.POST.get('turno')
        data_hora_inicio = request.POST.get('data_hora_inicio')
        data_hora_fim = request.POST.get('data_hora_fim')

        # Verificação básica
        if not sala_id or not nome_adm or not turno_id or not data_hora_inicio or not data_hora_fim:
            messages.error(request, "Todos os campos são obrigatórios.")
            return redirect(f'/reservaadmin/?sala_id={sala_id}')

        try:
            turno = Turno.objects.get(id_turno=turno_id)
        except Turno.DoesNotExist:
            messages.error(request, "Turno inválido.")
            return redirect(f'/reservaadmin/?sala_id={sala_id}')

        try:
            # Convertendo os horários sem aplicar fuso horário
            horario_inicio = datetime.strptime(data_hora_inicio, "%Y-%m-%dT%H:%M")
            horario_fim = datetime.strptime(data_hora_fim, "%Y-%m-%dT%H:%M")
            print(f"Horário início: {horario_inicio}")  # Depuração
            print(f"Horário fim: {horario_fim}")  # Depuração
        except ValueError as e:
            print(f"Erro de conversão: {e}")
            messages.error(request, "Horário inválido.")
            return redirect(f'/reservaadmin/?sala_id={sala_id}')

        # Verifica se já existe uma reserva com conflito de horários
        conflitos = Reservaadm.objects.filter(
            sala_id=sala_id,
            data_hora_inicio__lt=horario_fim,
            data_hora_fim__gt=horario_inicio
        )
        if conflitos.exists():
            messages.error(request, "Conflito com outra reserva.")
            return redirect(f'/reservaadmin/?sala_id={sala_id}')

        # Criar a reserva
        try:
            reserva = Reservaadm.objects.create(
                data_hora_inicio=horario_inicio,
                data_hora_fim=horario_fim,
                status_reserva='Confirmada',
                nome_adm=nome_adm,
                sala_id=sala_id,
                turno_id=turno_id
            )
            messages.success(request, 'Reserva feita com sucesso!')
            return redirect('homeadmin')

        except Exception as error:
            messages.error(request, f"Erro ao salvar a reserva: {error}")
            return redirect(f'/reservaadmin/?sala_id={sala_id}')


def excluir_maquina(request, id_equip):
    equipamento = get_object_or_404(Equipamento, id_equip=id_equip)  # Altere para usar 'id_doc'
    equipamento.delete()  # Deleta o docente do banco de dados
    return redirect('inventarioadmin')

def excluir_docente(request, id_doc):
    # Obtém o docente pelo ID ou retorna 404 caso não seja encontrado
    docente = get_object_or_404(Docente, id_doc=id_doc)

    # Exclui todas as reservas associadas ao docente antes de excluí-lo
    reservas_excluidas = Reserva.objects.filter(email_doc=docente.email_doc).delete()

    # Exclui o registro de validação associado ao docente
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM validacao WHERE email = %s", [docente.email_doc])

    # Exclui o docente
    docente.delete()

    # Mensagens de feedback ao usuário
    if reservas_excluidas[0] > 0:
        messages.success(
            request,
            f"Docente {docente.nome_doc} e suas {reservas_excluidas[0]} reservas foram excluídos com sucesso!"
        )
    else:
        messages.success(
            request,
            f"Docente {docente.nome_doc} foi excluído com sucesso!"
        )

    return redirect('listafuncionarios')

def deletar_reservas_expiradas_admin():
    agora = datetime.now()
    with connection.cursor() as cursor:
        # Excluir todas as reservas onde data_hora_fim já passou
        cursor.execute("DELETE FROM reservasadmin WHERE data_hora_fim < %s", [agora]) # função que deleta as reservas inspiradas.