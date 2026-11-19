from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Etapa, Gasto, Obra, Usuario


class Base(TestCase):
    def setUp(self):
        self.hoje = timezone.localdate()
        self.cons = Usuario.objects.create_user("cons", "c@x.com", "senha12345", perfil="construtora")
        self.outra_cons = Usuario.objects.create_user("cons2", "c2@x.com", "senha12345", perfil="construtora")
        self.dono = Usuario.objects.create_user("dono", "d@x.com", "senha12345", perfil="dono")
        self.outro_dono = Usuario.objects.create_user("dono2", "d2@x.com", "senha12345", perfil="dono")
        self.obra = Obra.objects.create(
            construtora=self.cons, dono=self.dono, nome="Reforma", endereco="Rua A",
            data_inicio=self.hoje, data_prevista=self.hoje + timedelta(days=30), orcamento=Decimal("10000"),
        )


class RegrasDeNegocioTests(Base):
    def test_rn03_progresso_e_percentual_de_etapas_concluidas(self):
        self.assertEqual(self.obra.progresso, 0)
        Etapa.objects.create(obra=self.obra, titulo="A", prazo=self.hoje, status="concluida")
        Etapa.objects.create(obra=self.obra, titulo="B", prazo=self.hoje)
        Etapa.objects.create(obra=self.obra, titulo="C", prazo=self.hoje)
        Etapa.objects.create(obra=self.obra, titulo="D", prazo=self.hoje, status="concluida")
        self.assertEqual(self.obra.progresso, 50)

    def test_rn04_etapa_atrasada(self):
        vencida = Etapa.objects.create(obra=self.obra, titulo="X", prazo=self.hoje - timedelta(days=1))
        concluida = Etapa.objects.create(obra=self.obra, titulo="Y", prazo=self.hoje - timedelta(days=1), status="concluida")
        no_prazo = Etapa.objects.create(obra=self.obra, titulo="Z", prazo=self.hoje)
        self.assertTrue(vencida.atrasada)
        self.assertFalse(concluida.atrasada)
        self.assertFalse(no_prazo.atrasada)

    def test_rn05_alerta_de_orcamento_a_partir_de_90(self):
        Gasto.objects.create(obra=self.obra, descricao="a", categoria="material", valor=Decimal("8900"))
        self.assertFalse(self.obra.alerta_orcamento)
        Gasto.objects.create(obra=self.obra, descricao="b", categoria="material", valor=Decimal("100"))
        self.assertTrue(self.obra.alerta_orcamento)
        self.assertEqual(self.obra.saldo, Decimal("1000"))

    def test_rn06_aprovacao_some_se_etapa_sair_de_concluida(self):
        e = Etapa.objects.create(obra=self.obra, titulo="X", prazo=self.hoje, status="concluida", aprovada=True)
        e.status = "andamento"
        e.save()
        e.refresh_from_db()
        self.assertFalse(e.aprovada)


class PermissoesTests(Base):
    def test_rn01_dono_nao_pode_criar_obra(self):
        self.client.login(username="dono", password="senha12345")
        self.assertEqual(self.client.get(reverse("obra_nova")).status_code, 403)

    def test_rn02_dono_so_ve_suas_obras(self):
        self.client.login(username="dono2", password="senha12345")
        self.assertEqual(self.client.get(reverse("obra_detalhe", args=[self.obra.pk])).status_code, 404)
        self.client.login(username="dono", password="senha12345")
        self.assertEqual(self.client.get(reverse("obra_detalhe", args=[self.obra.pk])).status_code, 200)

    def test_construtora_nao_ve_obra_de_outra(self):
        self.client.login(username="cons2", password="senha12345")
        self.assertEqual(self.client.get(reverse("obra_detalhe", args=[self.obra.pk])).status_code, 404)

    def test_dono_nao_move_etapa(self):
        e = Etapa.objects.create(obra=self.obra, titulo="X", prazo=self.hoje)
        self.client.login(username="dono", password="senha12345")
        r = self.client.post(reverse("etapa_mover", args=[e.pk]), {"status": "concluida"})
        self.assertEqual(r.status_code, 403)
        e.refresh_from_db()
        self.assertEqual(e.status, "a_fazer")

    def test_rf09_dono_aprova_etapa_concluida(self):
        e = Etapa.objects.create(obra=self.obra, titulo="X", prazo=self.hoje, status="concluida")
        self.client.login(username="dono", password="senha12345")
        self.client.post(reverse("etapa_aprovar", args=[e.pk]))
        e.refresh_from_db()
        self.assertTrue(e.aprovada)

    def test_dono_nao_aprova_etapa_nao_concluida(self):
        e = Etapa.objects.create(obra=self.obra, titulo="X", prazo=self.hoje, status="andamento")
        self.client.login(username="dono", password="senha12345")
        self.client.post(reverse("etapa_aprovar", args=[e.pk]))
        e.refresh_from_db()
        self.assertFalse(e.aprovada)


class FluxoTests(Base):
    def test_rf01_cadastro_com_perfil(self):
        r = self.client.post(reverse("cadastro"), {
            "first_name": "Ana", "username": "ana", "email": "ana@x.com", "perfil": "dono",
            "password1": "Senha!Forte123", "password2": "Senha!Forte123",
        })
        self.assertRedirects(r, reverse("painel"))
        self.assertEqual(Usuario.objects.get(username="ana").perfil, "dono")

    def test_rf02_rf03_construtora_cria_obra_e_vincula_dono_por_email(self):
        self.client.login(username="cons", password="senha12345")
        r = self.client.post(reverse("obra_nova"), {
            "nome": "Nova", "endereco": "Rua B", "data_inicio": self.hoje, "data_prevista": self.hoje + timedelta(days=5),
            "orcamento": "5000", "status": "planejamento", "email_dono": "D2@X.COM",
        })
        obra = Obra.objects.get(nome="Nova")
        self.assertRedirects(r, reverse("obra_detalhe", args=[obra.pk]))
        self.assertEqual(obra.dono, self.outro_dono)
        self.assertEqual(obra.construtora, self.cons)

    def test_rf03_email_de_dono_inexistente_da_erro(self):
        self.client.login(username="cons", password="senha12345")
        r = self.client.post(reverse("obra_nova"), {
            "nome": "Nova", "endereco": "Rua B", "data_inicio": self.hoje, "data_prevista": self.hoje,
            "orcamento": "5000", "status": "planejamento", "email_dono": "ninguem@x.com",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Obra.objects.filter(nome="Nova").exists())

    def test_rf06_gasto_negativo_nao_e_aceito(self):
        self.client.login(username="cons", password="senha12345")
        self.client.post(reverse("gasto_novo", args=[self.obra.pk]), {
            "descricao": "x", "categoria": "material", "valor": "-10", "data": self.hoje,
        })
        self.assertEqual(self.obra.gastos.count(), 0)

    def test_paginas_principais_abrem(self):
        self.client.login(username="cons", password="senha12345")
        for aba in ["etapas", "diario", "gastos"]:
            self.assertEqual(self.client.get(reverse("obra_detalhe", args=[self.obra.pk]) + f"?aba={aba}").status_code, 200)
        self.assertEqual(self.client.get(reverse("painel")).status_code, 200)
        self.assertEqual(self.client.get(reverse("relatorio", args=[self.obra.pk])).status_code, 200)
        self.client.login(username="dono", password="senha12345")
        self.assertEqual(self.client.get(reverse("painel")).status_code, 200)
