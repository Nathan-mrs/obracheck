from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("entrar/", auth_views.LoginView.as_view(), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("cadastro/", views.cadastro, name="cadastro"),
    path("painel/", views.painel, name="painel"),
    path("obras/nova/", views.obra_nova, name="obra_nova"),
    path("obras/<int:pk>/", views.obra_detalhe, name="obra_detalhe"),
    path("obras/<int:pk>/editar/", views.obra_editar, name="obra_editar"),
    path("obras/<int:pk>/excluir/", views.obra_excluir, name="obra_excluir"),
    path("obras/<int:pk>/relatorio/", views.relatorio, name="relatorio"),
    path("obras/<int:pk>/etapas/nova/", views.etapa_nova, name="etapa_nova"),
    path("obras/<int:pk>/diario/novo/", views.diario_novo, name="diario_novo"),
    path("obras/<int:pk>/gastos/novo/", views.gasto_novo, name="gasto_novo"),
    path("etapas/<int:pk>/editar/", views.etapa_editar, name="etapa_editar"),
    path("etapas/<int:pk>/excluir/", views.etapa_excluir, name="etapa_excluir"),
    path("etapas/<int:pk>/mover/", views.etapa_mover, name="etapa_mover"),
    path("etapas/<int:pk>/aprovar/", views.etapa_aprovar, name="etapa_aprovar"),
    path("etapas/<int:pk>/comentar/", views.comentario_novo, name="comentario_novo"),
    path("gastos/<int:pk>/excluir/", views.gasto_excluir, name="gasto_excluir"),
]
