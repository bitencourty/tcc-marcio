# Generated by Django 5.1.3 on 2024-11-19 10:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('roomap', '0009_reservaultimasemanadocente'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReservaDiaAtualAdmin',
            fields=[
                ('id_reserva', models.AutoField(primary_key=True, serialize=False)),
                ('nome_adm', models.CharField(max_length=100)),
                ('data_hora_inicio', models.DateTimeField()),
                ('data_hora_fim', models.DateTimeField()),
                ('status_reserva', models.CharField(max_length=50)),
                ('id_sala', models.CharField(max_length=50)),
                ('nome_sala', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'reservas_dia_atual_admin',
                'managed': False,
            },
        ),
        migrations.DeleteModel(
            name='ViewReservasAdmin',
        ),
        migrations.AlterField(
            model_name='docente',
            name='email_doc',
            field=models.EmailField(max_length=254, unique=True),
        ),
        migrations.AlterField(
            model_name='reservaadm',
            name='id_reserva',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='reservaadm',
            name='sala',
            field=models.IntegerField(db_column='id_sala'),
        ),
        migrations.AlterModelTable(
            name='reservaadm',
            table='reservasadmin',
        ),
    ]