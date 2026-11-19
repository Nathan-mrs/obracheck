# ObraCheck — Requisitos do MVP

**Projeto:** ObraCheck — gestão de pequenas obras e reformas
**Curso:** Análise e Desenvolvimento de Sistemas — UNINASSAU Parnaíba
**Versão:** 1.0 — novembro/2026

## 1. Objetivo do MVP

Validar a ideia central do ObraCheck: uma plataforma em que a construtora organiza a obra (etapas, diário e gastos) e o dono da obra acompanha tudo em tempo real e aprova as etapas, reduzindo ligações, desencontros e surpresas no orçamento.

## 2. Perfis de usuário

| Perfil | Quem é | O que faz |
|---|---|---|
| **Construtora / Empreiteiro** | Pequenas construtoras, empreiteiros e profissionais autônomos | Cadastra e gerencia as obras |
| **Dono da obra (cliente)** | Quem contratou a obra ou reforma | Acompanha, aprova etapas e comenta. Não edita dados |

## 3. Requisitos funcionais

| ID | Requisito | Perfil | Prioridade |
|---|---|---|---|
| RF01 | Cadastro e login com escolha de perfil (construtora ou dono da obra) | Ambos | Alta |
| RF02 | Cadastrar, editar e excluir obras (nome, endereço, descrição, datas de início e entrega, orçamento, status) | Construtora | Alta |
| RF03 | Vincular o dono à obra pelo e-mail da conta dele | Construtora | Alta |
| RF04 | Gerenciar etapas da obra em quadro Kanban (A fazer → Em andamento → Concluída), com prazo | Construtora | Alta |
| RF05 | Registrar diário de obra com data, descrição e foto | Construtora | Alta |
| RF06 | Lançar gastos (descrição, categoria, valor, data) e ver previsto x realizado e totais por categoria | Construtora | Alta |
| RF07 | Painel da construtora: obras ativas e concluídas, etapas atrasadas, total gasto x orçado | Construtora | Média |
| RF08 | Painel do dono: progresso das obras, etapas aguardando aprovação e últimas atualizações do diário | Dono | Alta |
| RF09 | Aprovar etapa concluída e comentar nas etapas | Dono (aprovar) / Ambos (comentar) | Alta |
| RF10 | Gerar relatório da obra para imprimir ou salvar em PDF | Ambos | Média |

## 4. Regras de negócio

| ID | Regra |
|---|---|
| RN01 | Somente a construtora cria, edita e exclui obras, etapas, registros de diário e gastos |
| RN02 | O dono da obra vê apenas as obras vinculadas a ele; a construtora vê apenas as obras que ela criou |
| RN03 | Progresso da obra = etapas concluídas ÷ total de etapas × 100 |
| RN04 | Uma etapa está atrasada quando o prazo já passou e ela não está concluída (destaque em vermelho) |
| RN05 | O sistema alerta quando os gastos atingem 90% ou mais do orçamento |
| RN06 | Só etapas concluídas podem ser aprovadas pelo dono; se a etapa voltar para "em andamento", a aprovação é desfeita |
| RN07 | Só é possível vincular como dono um e-mail que já tenha conta com perfil "Dono da obra" |
| RN08 | Valores de orçamento e gastos devem ser maiores que zero; a data de entrega não pode ser anterior à de início |

## 5. Requisitos não funcionais

| ID | Requisito |
|---|---|
| RNF01 | Desenvolvido em Python 3 com o framework Django e banco SQLite |
| RNF02 | Interface web responsiva (funciona no celular e no computador) |
| RNF03 | Senhas armazenadas com hash e controle de acesso por perfil em todas as telas |
| RNF04 | Proteção contra CSRF em todos os formulários |
| RNF05 | Interface em português do Brasil, com valores em R$ e datas no formato dd/mm/aaaa |
| RNF06 | Identidade visual do ObraCheck: laranja #FF6B1A e grafite #2B2D33 |
| RNF07 | Testes automatizados cobrindo as regras de negócio e as permissões |

## 6. Fora do escopo do MVP (versões futuras)

- Pagamento e planos de assinatura (Básico, Profissional, Empresarial)
- Aplicativo mobile nativo (Android/iOS)
- Chat em tempo real
- Notificações por WhatsApp, e-mail ou push
- Vários funcionários por construtora (equipes)
- Integração com fornecedores e orçamentos de material
- Emissão de nota fiscal

## 7. Critérios de aceite do MVP

1. Uma construtora consegue criar uma obra, vincular um dono, cadastrar etapas, registrar o diário com foto e lançar gastos.
2. O dono vinculado vê a obra, o progresso, as fotos e os gastos, mas não consegue editar nada.
3. O dono consegue aprovar uma etapa concluída e comentar.
4. Um usuário não consegue acessar obras de outras pessoas.
5. O sistema destaca etapas atrasadas e alerta quando o orçamento passa de 90%.
6. Todos os testes automatizados passam (`python manage.py test core`).
