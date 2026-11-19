from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Comentario, Etapa, Gasto, Obra, RegistroDiario, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "first_name", "email", "perfil", "empresa")
    list_filter = ("perfil",)
    fieldsets = UserAdmin.fieldsets + (("ObraCheck", {"fields": ("perfil", "empresa", "telefone")}),)


class EtapaInline(admin.TabularInline):
    model = Etapa
    extra = 0


@admin.register(Obra)
class ObraAdmin(admin.ModelAdmin):
    list_display = ("nome", "construtora", "dono", "status", "data_prevista", "orcamento")
    list_filter = ("status",)
    search_fields = ("nome", "endereco")
    inlines = [EtapaInline]


admin.site.register([Etapa, Gasto, RegistroDiario, Comentario])
admin.site.site_header = "ObraCheck — Administração"
