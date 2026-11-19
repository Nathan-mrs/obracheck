from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Usuario(AbstractUser):
    """Usuário do sistema com um dos dois perfis (RF01)."""

    class Perfil(models.TextChoices):
        CONSTRUTORA = "construtora", "Construtora / Empreiteiro"
        DONO = "dono", "Dono da obra"

    email = models.EmailField("e-mail", unique=True)
    perfil = models.CharField(max_length=20, choices=Perfil.choices)
    telefone = models.CharField(max_length=20, blank=True)
    empresa = models.CharField("nome da empresa", max_length=120, blank=True)

    @property
    def is_construtora(self):
        return self.perfil == self.Perfil.CONSTRUTORA

    @property
    def is_dono(self):
        return self.perfil == self.Perfil.DONO

    def __str__(self):
        return self.get_full_name() or self.username


class Obra(models.Model):
    """Obra ou reforma gerenciada por uma construtora (RF02)."""

    class Status(models.TextChoices):
        PLANEJAMENTO = "planejamento", "Planejamento"
        ANDAMENTO = "andamento", "Em andamento"
        PAUSADA = "pausada", "Pausada"
        CONCLUIDA = "concluida", "Concluída"

    construtora = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="obras_gerenciadas",
        limit_choices_to={"perfil": "construtora"},
    )
    dono = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="obras_contratadas", limit_choices_to={"perfil": "dono"},
    )
    nome = models.CharField(max_length=120)
    endereco = models.CharField("endereço", max_length=200)
    descricao = models.TextField("descrição", blank=True)
    data_inicio = models.DateField("data de início")
    data_prevista = models.DateField("previsão de entrega")
    orcamento = models.DecimalField("orçamento (R$)", max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANEJAMENTO)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criada_em"]

    def __str__(self):
        return self.nome

    # RN03 — progresso = etapas concluídas / total
    @property
    def progresso(self):
        total = self.etapas.count()
        if total == 0:
            return 0
        concluidas = self.etapas.filter(status=Etapa.Status.CONCLUIDA).count()
        return round(concluidas * 100 / total)

    @property
    def total_gasto(self):
        return self.gastos.aggregate(t=Sum("valor"))["t"] or Decimal("0")

    @property
    def percentual_gasto(self):
        if not self.orcamento:
            return 0
        return round(self.total_gasto * 100 / self.orcamento)

    # RN05 — alerta quando gastos passam de 90% do orçamento
    @property
    def alerta_orcamento(self):
        return self.percentual_gasto >= 90

    @property
    def saldo(self):
        return self.orcamento - self.total_gasto

    @property
    def etapas_atrasadas(self):
        hoje = timezone.localdate()
        return self.etapas.exclude(status=Etapa.Status.CONCLUIDA).filter(prazo__lt=hoje)

    @property
    def atrasada(self):
        return (
            self.status != self.Status.CONCLUIDA
            and self.data_prevista < timezone.localdate()
        )


class Etapa(models.Model):
    """Etapa da obra exibida no quadro Kanban (RF04)."""

    class Status(models.TextChoices):
        A_FAZER = "a_fazer", "A fazer"
        ANDAMENTO = "andamento", "Em andamento"
        CONCLUIDA = "concluida", "Concluída"

    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="etapas")
    titulo = models.CharField("título", max_length=120)
    descricao = models.TextField("descrição", blank=True)
    prazo = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.A_FAZER)
    ordem = models.PositiveIntegerField(default=0)
    # RN06 — etapa concluída precisa da aprovação do dono
    aprovada = models.BooleanField(default=False)
    aprovada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["ordem", "prazo"]

    def __str__(self):
        return self.titulo

    # RN04 — atrasada = prazo vencido e não concluída
    @property
    def atrasada(self):
        return self.status != self.Status.CONCLUIDA and self.prazo < timezone.localdate()

    def save(self, *args, **kwargs):
        # Se a etapa sair de "concluída", a aprovação deixa de valer.
        if self.status != self.Status.CONCLUIDA:
            self.aprovada = False
            self.aprovada_em = None
        super().save(*args, **kwargs)


class RegistroDiario(models.Model):
    """Diário de obra com texto e foto (RF05)."""

    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="diario")
    autor = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    data = models.DateField(default=timezone.localdate)
    texto = models.TextField("o que foi feito")
    foto = models.ImageField(upload_to="diario/", blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data", "-criado_em"]


class Gasto(models.Model):
    """Gasto da obra (RF06)."""

    class Categoria(models.TextChoices):
        MATERIAL = "material", "Material"
        MAO_DE_OBRA = "mao_de_obra", "Mão de obra"
        EQUIPAMENTO = "equipamento", "Equipamento"
        TRANSPORTE = "transporte", "Transporte"
        OUTROS = "outros", "Outros"

    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="gastos")
    descricao = models.CharField("descrição", max_length=150)
    categoria = models.CharField(max_length=20, choices=Categoria.choices)
    valor = models.DecimalField("valor (R$)", max_digits=12, decimal_places=2)
    data = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ["-data"]


class Comentario(models.Model):
    """Comentário do dono ou da construtora em uma etapa (RF09)."""

    etapa = models.ForeignKey(Etapa, on_delete=models.CASCADE, related_name="comentarios")
    autor = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    texto = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["criado_em"]
