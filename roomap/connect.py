import mysql.connector
from mysql.connector import errorcode

try:
    # Conectar ao banco de dados
    db_connection = mysql.connector.connect(host='localhost',
                                            user='tecmysql',
                                            password='devmysql',
                                            database='roomap')
    print("Conexão realizada com sucesso!")

    # Criar cursor
    cursor = db_connection.cursor()

    # Comando SQL para inserção
    sql = "INSERT INTO reservas (data_hora_inicio, data_hora_fim, status_reserva, nome_doc, id_sala)  VALUES (%s, %s, %s, %s, %s)"
    reservas = ('2024-01-01 00:00:00', '2024-01-01 01:00:00', 'Confirmada', 'Teste', 1)

    # Executar a inserção
    cursor.execute(sql, reservas)

    # Confirmar a transação
    db_connection.commit()
    print("Registro inserido!")

except mysql.connector.Error as error:
    # Tratar erros específicos de banco de dados
    if error.errno == errorcode.ER_BAD_DB_ERROR:
        print("O banco de dados não existe")
    elif error.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("O user name ou o password está incorreto!")
    else:
        print(error)

finally:
    # Fechar a conexão com o banco de dados
    if 'db_connection' in locals() and db_connection.is_connected():
        cursor.close()
        db_connection.close()
        print("Conexão encerrada.")





