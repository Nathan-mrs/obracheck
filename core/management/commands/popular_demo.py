"""Cria dados de demonstração: python manage.py popular_demo"""
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Comentario, Etapa, Gasto, Obra, RegistroDiario, Usuario

SENHA = "obra1234"


def foto_demo(cor, texto):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    img = Image.new("RGB", (640, 420), cor)
    d = ImageDraw.Draw(img)
    for i in range(0, 640, 40):
        d.line([(i, 420), (i + 200, 0)], fill=tuple(max(c - 25, 0) for c in cor), width=6)
    d.rectangle([20, 340, 620, 400], fill=(43, 45, 51))
    d.text((36, 362), texto, fill=(255, 255, 255))
    buf = BytesIO()
    img.save(buf, "JPEG", quality=80)
    return ContentFile(buf.getvalue(), name="demo.jpg")


class Command(BaseCommand):
    help = "Popula o banco com usuários e obras de demonstração"

    def handle(self, *args, **opts):
        hoje = timezone.localdate()
        d = lambda dias: hoje + timedelta(days=dias)

        Usuario.objects.filter(username__in=["construtora", "cliente", "cliente2", "admin"]).delete()

        Usuario.objects.create_superuser("admin", "admin@obracheck.com", SENHA, perfil="construtora", first_name="Admin")
        cons = Usuario.objects.create_user(
            "construtora", "contato@silvaconstrucoes.com", SENHA, first_name="Carlos Silva",
            perfil="construtora", empresa="Silva Construções e Reformas", telefone="(86) 99999-1234",
        )
        dono = Usuario.objects.create_user(
            "cliente", "maria@email.com", SENHA, first_name="Maria Oliveira", perfil="dono", telefone="(86) 98888-5678",
        )
        dono2 = Usuario.objects.create_user(
            "cliente2", "joao@email.com", SENHA, first_name="João Pereira", perfil="dono",
        )

        # Obra 1 — reforma em andamento
        o1 = Obra.objects.create(
            construtora=cons, dono=dono, nome="Reforma da casa — Maria",
            endereco="Rua Projetada 120, Centro, Parnaíba - PI",
            descricao="Reforma completa de cozinha e banheiro social, troca do piso da sala.",
            data_inicio=d(-30), data_prevista=d(25), orcamento=Decimal("38000"), status="andamento",
        )
        etapas = [
            ("Demolição e retirada de entulho", -24, "concluida", True),
            ("Instalação hidráulica", -10, "concluida", False),
            ("Instalação elétrica", -3, "andamento", False),
            ("Contrapiso e assentamento de piso", 8, "a_fazer", False),
            ("Revestimento do banheiro", 14, "a_fazer", False),
            ("Pintura e acabamento", 22, "a_fazer", False),
        ]
        for i, (t, p, s, ap) in enumerate(etapas, 1):
            e = Etapa.objects.create(obra=o1, titulo=t, prazo=d(p), status=s, ordem=i)
            if ap:
                e.aprovada, e.aprovada_em = True, timezone.now() - timedelta(days=20)
                e.save()
        hidr = o1.etapas.get(titulo="Instalação hidráulica")
        Comentario.objects.create(etapa=hidr, autor=cons, texto="Trocamos todos os canos da cozinha por PVC novo.")
        Comentario.objects.create(etapa=hidr, autor=dono, texto="Ótimo! Vou passar aí amanhã para ver.")

        for desc, cat, val, dias in [
            ("Caçamba de entulho", "transporte", "650", -26),
            ("Equipe de demolição (3 diárias)", "mao_de_obra", "1800", -24),
            ("Tubos e conexões PVC", "material", "2350", -15),
            ("Encanador (empreitada)", "mao_de_obra", "3200", -11),
            ("Fios, disjuntores e quadro", "material", "2900", -5),
            ("Porcelanato 60x60 (45 m²)", "material", "5400", -2),
        ]:
            Gasto.objects.create(obra=o1, descricao=desc, categoria=cat, valor=Decimal(val), data=d(dias))

        for dias, txt, cor in [
            (-24, "Demolição da cozinha e do banheiro concluída. Entulho retirado.", (180, 140, 110)),
            (-12, "Nova tubulação de água fria e esgoto instalada no banheiro.", (120, 150, 170)),
            (-4, "Início da passagem de fios na cozinha. Quadro de distribuição trocado.", (200, 170, 90)),
        ]:
            r = RegistroDiario(obra=o1, autor=cons, data=d(dias), texto=txt)
            f = foto_demo(cor, txt[:60])
            if f:
                r.foto.save(f"diario_{abs(dias)}.jpg", f, save=False)
            r.save()

        # Obra 2 — perto de estourar o orçamento
        o2 = Obra.objects.create(
            construtora=cons, dono=dono2, nome="Construção de muro e garagem",
            endereco="Av. São Sebastião 845, Parnaíba - PI",
            data_inicio=d(-40), data_prevista=d(-2), orcamento=Decimal("15000"), status="andamento",
        )
        for i, (t, p, s) in enumerate([
            ("Fundação do muro", -30, "concluida"), ("Levantar alvenaria", -15, "concluida"),
            ("Cobertura da garagem", -5, "andamento"), ("Portão e pintura", 3, "a_fazer"),
        ], 1):
            Etapa.objects.create(obra=o2, titulo=t, prazo=d(p), status=s, ordem=i)
        for desc, cat, val in [("Blocos e cimento", "material", "6200"), ("Pedreiro e ajudante", "mao_de_obra", "5800"),
                               ("Telhas e madeiramento", "material", "2100")]:
            Gasto.objects.create(obra=o2, descricao=desc, categoria=cat, valor=Decimal(val), data=d(-10))

        # Obra 3 — planejamento, sem dono
        o3 = Obra.objects.create(
            construtora=cons, nome="Ampliação de loja — Centro", endereco="Rua Grande 300, Parnaíba - PI",
            data_inicio=d(10), data_prevista=d(70), orcamento=Decimal("52000"), status="planejamento",
        )
        Etapa.objects.create(obra=o3, titulo="Projeto e aprovação na prefeitura", prazo=d(15), ordem=1)

        self.stdout.write(self.style.SUCCESS(
            f"Dados criados! Logins (senha {SENHA}): construtora | cliente | cliente2 | admin"
        ))
