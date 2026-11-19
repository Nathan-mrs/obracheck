from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (CadastroForm, ComentarioForm, EtapaForm, GastoForm,
                    ObraForm, RegistroDiarioForm)
from .models import Etapa, Gasto, Obra, RegistroDiario


# ---------------------------------------------------------------------------
# Controle de acesso por perfil (RNF03 / RN01 / RN02)
# ---------------------------------------------------------------------------

def somente_construtora(view):
    @wraps(view)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_construtora:
            raise PermissionDenied("Apenas a construtora pode fazer isso.")
        return view(request, *args, **kwargs)
    return _wrapped


def somente_dono(view):
    @wraps(view)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_dono:
            raise PermissionDenied("Apenas o dono da obra pode fazer isso.")
        return view(request, *args, **kwargs)
    return _wrapped


def obras_do_usuario(user):
    """RN02 — cada usuário só enxerga as obras ligadas a ele."""
    if user.is_construtora:
        return Obra.objects.filter(construtora=user)
    return Obra.objects.filter(dono=user)


def pegar_obra(user, pk):
    obra = obras_do_usuario(user).filter(pk=pk).first()
    if obra is None:
        raise Http404("Obra não encontrada.")
    return obra


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

def inicio(request):
    if request.user.is_authenticated:
        return redirect("painel")
    return render(request, "core/inicio.html")


def cadastro(request):
    form = CadastroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(request, f"Bem-vindo ao ObraCheck, {usuario.first_name}!")
        return redirect("painel")
    return render(request, "registration/cadastro.html", {"form": form})


# ---------------------------------------------------------------------------
# Painéis (RF07 e RF08)
# ---------------------------------------------------------------------------

@login_required
def painel(request):
    obras = obras_do_usuario(request.user).select_related("dono", "construtora")
    hoje = timezone.localdate()
    etapas_atrasadas = (
        Etapa.objects.filter(obra__in=obras, prazo__lt=hoje)
        .exclude(status=Etapa.Status.CONCLUIDA)
        .select_related("obra")
    )
    contexto = {
        "obras": obras,
        "ativas": obras.exclude(status=Obra.Status.CONCLUIDA).count(),
        "concluidas": obras.filter(status=Obra.Status.CONCLUIDA).count(),
        "etapas_atrasadas": etapas_atrasadas,
        "total_gasto": sum((o.total_gasto for o in obras), 0),
        "total_orcado": sum((o.orcamento for o in obras), 0),
    }
    if request.user.is_dono:
        contexto["aguardando_aprovacao"] = Etapa.objects.filter(
            obra__in=obras, status=Etapa.Status.CONCLUIDA, aprovada=False
        ).select_related("obra")
        contexto["ultimos_registros"] = (
            RegistroDiario.objects.filter(obra__in=obras).select_related("obra")[:5]
        )
        return render(request, "core/painel_dono.html", contexto)
    return render(request, "core/painel_construtora.html", contexto)


# ---------------------------------------------------------------------------
# Obras (RF02 / RF03)
# ---------------------------------------------------------------------------

@somente_construtora
def obra_nova(request):
    form = ObraForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obra = form.save(commit=False)
        obra.construtora = request.user
        obra.save()
        messages.success(request, "Obra cadastrada! Agora adicione as etapas.")
        return redirect("obra_detalhe", pk=obra.pk)
    return render(request, "core/form.html", {"form": form, "titulo": "Nova obra"})


@somente_construtora
def obra_editar(request, pk):
    obra = pegar_obra(request.user, pk)
    form = ObraForm(request.POST or None, instance=obra)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Obra atualizada.")
        return redirect("obra_detalhe", pk=obra.pk)
    return render(request, "core/form.html", {"form": form, "titulo": f"Editar obra — {obra.nome}", "obra": obra})


@somente_construtora
def obra_excluir(request, pk):
    obra = pegar_obra(request.user, pk)
    if request.method == "POST":
        obra.delete()
        messages.success(request, "Obra excluída.")
        return redirect("painel")
    return render(request, "core/confirmar.html", {"objeto": obra, "voltar": obra})


@login_required
def obra_detalhe(request, pk):
    obra = pegar_obra(request.user, pk)
    aba = request.GET.get("aba", "etapas")
    etapas = obra.etapas.prefetch_related("comentarios__autor")
    colunas = [
        (valor, rotulo, [e for e in etapas if e.status == valor])
        for valor, rotulo in Etapa.Status.choices
    ]
    gastos = obra.gastos.all()
    por_categoria = []
    for valor, rotulo in Gasto.Categoria.choices:
        total = sum((g.valor for g in gastos if g.categoria == valor), 0)
        if total:
            por_categoria.append((rotulo, total))
    return render(request, "core/obra_detalhe.html", {
        "obra": obra,
        "aba": aba,
        "colunas": colunas,
        "diario": obra.diario.select_related("autor"),
        "gastos": gastos,
        "por_categoria": por_categoria,
        "form_comentario": ComentarioForm(),
        "form_diario": RegistroDiarioForm(),
        "form_gasto": GastoForm(),
        "status_etapa": Etapa.Status,
    })


@login_required
def relatorio(request, pk):
    """RF10 — relatório da obra (download em PDF)."""
    obra = pegar_obra(request.user, pk)
    return render(request, "core/relatorio.html", {
        "obra": obra,
        "etapas": obra.etapas.all(),
        "gastos": obra.gastos.all(),
        "diario": obra.diario.all()[:10],
        "hoje": timezone.localdate(),
    })


# ---------------------------------------------------------------------------
# Etapas / Kanban (RF04)
# ---------------------------------------------------------------------------

@somente_construtora
def etapa_nova(request, pk):
    obra = pegar_obra(request.user, pk)
    form = EtapaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        etapa = form.save(commit=False)
        etapa.obra = obra
        etapa.ordem = obra.etapas.count() + 1
        etapa.save()
        messages.success(request, "Etapa adicionada.")
        return redirect("obra_detalhe", pk=obra.pk)
    return render(request, "core/form.html", {"form": form, "titulo": f"Nova etapa — {obra.nome}", "obra": obra})


def _etapa_da_construtora(user, pk):
    return get_object_or_404(Etapa, pk=pk, obra__construtora=user)


@somente_construtora
def etapa_editar(request, pk):
    etapa = _etapa_da_construtora(request.user, pk)
    form = EtapaForm(request.POST or None, instance=etapa)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Etapa atualizada.")
        return redirect("obra_detalhe", pk=etapa.obra_id)
    return render(request, "core/form.html", {"form": form, "titulo": f"Editar etapa — {etapa.titulo}", "obra": etapa.obra})


@somente_construtora
def etapa_excluir(request, pk):
    etapa = _etapa_da_construtora(request.user, pk)
    if request.method == "POST":
        obra_id = etapa.obra_id
        etapa.delete()
        messages.success(request, "Etapa excluída.")
        return redirect("obra_detalhe", pk=obra_id)
    return render(request, "core/confirmar.html", {"objeto": etapa, "voltar": etapa.obra})


@require_POST
@somente_construtora
def etapa_mover(request, pk):
    etapa = _etapa_da_construtora(request.user, pk)
    novo = request.POST.get("status")
    if novo in Etapa.Status.values:
        etapa.status = novo
        etapa.save()
    return redirect("obra_detalhe", pk=etapa.obra_id)


@require_POST
@somente_dono
def etapa_aprovar(request, pk):
    """RF09 / RN06 — o dono aprova uma etapa concluída."""
    etapa = get_object_or_404(Etapa, pk=pk, obra__dono=request.user)
    if etapa.status != Etapa.Status.CONCLUIDA:
        messages.error(request, "Só é possível aprovar etapas concluídas.")
    else:
        etapa.aprovada = True
        etapa.aprovada_em = timezone.now()
        etapa.save()
        messages.success(request, f"Etapa “{etapa.titulo}” aprovada.")
    return redirect("obra_detalhe", pk=etapa.obra_id)


@require_POST
@login_required
def comentario_novo(request, pk):
    etapa = get_object_or_404(
        Etapa, Q(obra__construtora=request.user) | Q(obra__dono=request.user), pk=pk
    )
    form = ComentarioForm(request.POST)
    if form.is_valid():
        c = form.save(commit=False)
        c.etapa = etapa
        c.autor = request.user
        c.save()
    return redirect("obra_detalhe", pk=etapa.obra_id)


# ---------------------------------------------------------------------------
# Diário (RF05) e gastos (RF06)
# ---------------------------------------------------------------------------

@require_POST
@somente_construtora
def diario_novo(request, pk):
    obra = pegar_obra(request.user, pk)
    form = RegistroDiarioForm(request.POST, request.FILES)
    if form.is_valid():
        r = form.save(commit=False)
        r.obra = obra
        r.autor = request.user
        r.save()
        messages.success(request, "Registro adicionado ao diário.")
    else:
        messages.error(request, "Não foi possível salvar o registro. Confira os campos.")
    return redirect(f"/obras/{obra.pk}/?aba=diario")


@require_POST
@somente_construtora
def gasto_novo(request, pk):
    obra = pegar_obra(request.user, pk)
    form = GastoForm(request.POST)
    if form.is_valid():
        g = form.save(commit=False)
        g.obra = obra
        g.save()
        messages.success(request, "Gasto registrado.")
        if obra.alerta_orcamento:
            messages.warning(request, f"Atenção: esta obra já usou {obra.percentual_gasto}% do orçamento.")
    else:
        for erros in form.errors.values():
            messages.error(request, erros[0])
    return redirect(f"/obras/{obra.pk}/?aba=gastos")


@require_POST
@somente_construtora
def gasto_excluir(request, pk):
    gasto = get_object_or_404(Gasto, pk=pk, obra__construtora=request.user)
    obra_id = gasto.obra_id
    gasto.delete()
    messages.success(request, "Gasto removido.")
    return redirect(f"/obras/{obra_id}/?aba=gastos")
