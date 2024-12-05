from django.urls import path
from .views import (
    inicio_view,
    loginadmin_view, login_view, cadastro_view,
    homedocente_view, homeadmin_view,
    reservaadmin_view, reservadocente_view, reserva_sala_view, reserva_sala_view_docente, deletar_reservas_expiradas,
    reservas_do_dia_docente, reservas_do_dia_admin,
    inventariodocente_view, inventarioadmin_view, excluir_maquina,
    listafuncionarios_view, addmaquina_view, addfuncionario_view, excluir_docente,
    perfil_view, editarperfil_view,
    agenda_view, agendaadmin_view,
    salas_view, mapa_view,
    relatorio_admin, relatorio_docente,
    send_help_email,
)

urlpatterns = [
    # Páginas iniciais e login
    path('', inicio_view, name='inicio'),
    path('loginadmin/', loginadmin_view, name='loginadmin'),
    path('login/', login_view, name='login'),
    path('cadastro/', cadastro_view, name='cadastro'),

    # Home
    path('homedocente/', homedocente_view, name='homedocente'),
    path('homeadmin/', homeadmin_view, name='homeadmin'),

    # Reservas
    path('reservaadmin/', reservaadmin_view, name='reservaadmin'),
    path('reservadocente/', reservadocente_view, name='reservadocente'),
    path('reservasala/', reserva_sala_view, name='reservasala'),
    path('reservasaladocente/', reserva_sala_view_docente, name='reservasaladocente'),
    path('reservasdiadocente/', reservas_do_dia_docente, name='reservasdiadocente'),
    path('reservasdiaadm/', reservas_do_dia_admin, name='reservasdiaadm'),
    path('deletarexpiradas/', deletar_reservas_expiradas, name='deletarexpiradas'),

    # Inventário
    path('inventariodocente/', inventariodocente_view, name='inventariodocente'),
    path('inventarioadmin/', inventarioadmin_view, name='inventarioadmin'),
    path('addmaquina/', addmaquina_view, name='addmaquina'),
    path('delete_maquina/<int:id_equip>/', excluir_maquina, name='delete_maquina'),

    # Funcionários
    path('listafuncionarios/', listafuncionarios_view, name='listafuncionarios'),
    path('addfuncionario/', addfuncionario_view, name='addfuncionario'),
    path('delete_docente/<int:id_doc>/', excluir_docente, name='delete_docente'),

    # Perfil
    path('perfil/', perfil_view, name='perfil'),
    path('editarperfil/', editarperfil_view, name='editarperfil'),

    # Agenda
    path('agenda/', agenda_view, name='agenda'),
    path('agendadmin/', agendaadmin_view, name='agendadmin'),

    # Outras páginas
    path('salas/', salas_view, name='salas'),
    path('mapa/', mapa_view, name='mapa'),

    # Relatórios
    path('relatorioadmin/', relatorio_admin, name='relatorioadmin'),
    path('relatoriodocente/', relatorio_docente, name='relatoriodocente'),

    # Contato
    path("send-help-email/", send_help_email, name="send_help_email"),

]
