# Generated by Django 5.1.2 on 2024-11-28 12:02

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('roomap', '0017_remove_reserva_nome_doc_reserva_email_doc_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reservaadm',
            name='sala',
            field=models.ForeignKey(db_column='id_sala', on_delete=django.db.models.deletion.CASCADE, to='roomap.sala'),
        ),
        migrations.AlterField(
            model_name='reservaadm',
            name='turno',
            field=models.ForeignKey(blank=True, db_column='turno_id', null=True, on_delete=django.db.models.deletion.CASCADE, to='roomap.turno'),
        ),
    ]
