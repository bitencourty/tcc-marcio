from django import forms
from .models import Docente

class DocenteForm(forms.ModelForm):
    class Meta:
        model = Docente
        fields = ('nome_doc', 'email_doc', 'senha_doc', 'cargo_doc', 'tel_doc')
        labels = {
            'nome_doc': '',
            'email_doc': '',
            'senha_doc': '',
            'cargo_doc': '',
            'tel_doc': ''
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Customize form fields
        self.fields['nome_doc'].widget.attrs.update({'placeholder': 'Nome'})
        self.fields['email_doc'].widget.attrs.update({'placeholder': 'Email'})
        self.fields['senha_doc'].widget = forms.PasswordInput()
        self.fields['senha_doc'].widget.attrs.update({'placeholder': 'Senha (6 dígitos)'})
        self.fields['cargo_doc'].widget.attrs.update({'placeholder': 'Cargo'})
        self.fields['tel_doc'].widget.attrs.update({'placeholder': 'Telefone'})

    def clean_senha_doc(self):
        senha = self.cleaned_data.get('senha_doc')
        if len(senha) != 6:
            raise forms.ValidationError("A senha deve ter exatamente 6 dígitos.")
        return senha

    def clean_email_doc(self):
        email = self.cleaned_data.get('email_doc')
        if '@' not in email:
            raise forms.ValidationError("Por favor, insira um endereço de e-mail válido.")
        return email


