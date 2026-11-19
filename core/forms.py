from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Comentario, Etapa, Gasto, Obra, RegistroDiario, Usuario


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        super().__init__(format="%Y-%m-%d", **kwargs)


class CadastroForm(UserCreationForm):
    """RF01 — cadastro com escolha de perfil."""

    first_name = forms.CharField(label="Seu nome", max_length=150)
    email = forms.EmailField(label="E-mail")
    perfil = forms.ChoiceField(
        label="Eu sou", choices=Usuario.Perfil.choices, widget=forms.RadioSelect
    )
    empresa = forms.CharField(
        label="Nome da empresa (se for construtora)", max_length=120, required=False
    )
    telefone = forms.CharField(label="Telefone / WhatsApp", max_length=20, required=False)

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("first_name", "username", "email", "perfil", "empresa", "telefone")
        labels = {"username": "Usuário (para login)"}

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta com este e-mail.")
        return email


class ObraForm(forms.ModelForm):
    # RF03 — vincular dono da obra pelo e-mail
    email_dono = forms.EmailField(
        label="E-mail do dono da obra",
        required=False,
        help_text="O dono precisa ter uma conta no ObraCheck com perfil “Dono da obra”.",
    )

    class Meta:
        model = Obra
        fields = ["nome", "endereco", "descricao", "data_inicio", "data_prevista", "orcamento", "status"]
        widgets = {
            "data_inicio": DateInput(),
            "data_prevista": DateInput(),
            "descricao": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.dono:
            self.fields["email_dono"].initial = self.instance.dono.email

    def clean_email_dono(self):
        email = self.cleaned_data.get("email_dono")
        if not email:
            return None
        try:
            return Usuario.objects.get(email__iexact=email, perfil=Usuario.Perfil.DONO)
        except Usuario.DoesNotExist:
            raise forms.ValidationError(
                "Nenhum dono da obra cadastrado com esse e-mail. Peça para ele criar a conta primeiro."
            )

    def clean(self):
        dados = super().clean()
        inicio, fim = dados.get("data_inicio"), dados.get("data_prevista")
        if inicio and fim and fim < inicio:
            self.add_error("data_prevista", "A previsão de entrega não pode ser antes do início.")
        orc = dados.get("orcamento")
        if orc is not None and orc <= 0:
            self.add_error("orcamento", "Informe um orçamento maior que zero.")
        return dados

    def save(self, commit=True):
        obra = super().save(commit=False)
        obra.dono = self.cleaned_data.get("email_dono")
        if commit:
            obra.save()
        return obra


class EtapaForm(forms.ModelForm):
    class Meta:
        model = Etapa
        fields = ["titulo", "descricao", "prazo", "status"]
        widgets = {"prazo": DateInput(), "descricao": forms.Textarea(attrs={"rows": 2})}


class RegistroDiarioForm(forms.ModelForm):
    class Meta:
        model = RegistroDiario
        fields = ["data", "texto", "foto"]
        widgets = {"data": DateInput(), "texto": forms.Textarea(attrs={"rows": 3})}


class GastoForm(forms.ModelForm):
    class Meta:
        model = Gasto
        fields = ["descricao", "categoria", "valor", "data"]
        widgets = {"data": DateInput()}

    def clean_valor(self):
        valor = self.cleaned_data["valor"]
        if valor <= 0:
            raise forms.ValidationError("O valor precisa ser maior que zero.")
        return valor


class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ["texto"]
        widgets = {"texto": forms.Textarea(attrs={"rows": 2, "placeholder": "Escreva um comentário…"})}
        labels = {"texto": ""}
