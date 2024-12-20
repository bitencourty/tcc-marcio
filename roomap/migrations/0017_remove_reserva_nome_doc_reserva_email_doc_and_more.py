# Generated by Django 5.1.2 on 2024-11-28 11:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('roomap', '0016_remove_reserva_nome_doc_reserva_email_doc_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reserva',
            name='nome_doc',
        ),
        migrations.AddField(
            model_name='reserva',
            name='email_doc',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AlterField(
            model_name='reserva',
            name='id_reserva',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='reservaadm',
            name='turno',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='roomap.turno'),
        ),
    ]
