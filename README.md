# 🏗️ ObraCheck — MVP

Aplicação web para organizar pequenas obras e reformas, conectando a **construtora/empreiteiro** e o **dono da obra**.

Trabalho acadêmico — Análise e Desenvolvimento de Sistemas · UNINASSAU Parnaíba · 2026
Autor: Nathan Moraes Almeida

## Tecnologias

- Python 3.11+ e Django 5 (MVC/MTV, ORM, autenticação)
- SQLite (banco de dados)
- HTML + CSS próprio (responsivo), templates do Django
- Pillow (upload de fotos do diário)

## Como rodar

```bash
# 1. criar e ativar o ambiente virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac

# 2. instalar dependências
pip install -r requirements.txt

# 3. criar o banco e popular com dados de demonstração
python manage.py migrate
python manage.py popular_demo

# 4. subir o servidor
python manage.py runserver
```

Acesse **http://127.0.0.1:8000**

### Usuários de demonstração (senha: `obra1234`)

| Usuário       | Perfil                        |
|---------------|-------------------------------|
| `construtora` | Construtora (Silva Construções) |
| `cliente`     | Dono da obra (Maria Oliveira) |
| `cliente2`    | Dono da obra (João Pereira)   |
| `admin`       | Administrador (`/admin`)      |

### Rodar os testes automatizados

```bash
python manage.py test core
```

15 testes cobrem as regras de negócio (progresso, atraso, alerta de orçamento, aprovação) e o controle de acesso por perfil.

## Perfis

| Ação                                   | Construtora | Dono da obra |
|----------------------------------------|:-----------:|:------------:|
| Criar / editar / excluir obra          | ✅ | ❌ |
| Vincular o dono pelo e-mail            | ✅ | ❌ |
| Criar e mover etapas no Kanban         | ✅ | ❌ |
| Registrar diário com foto              | ✅ | ❌ |
| Lançar gastos                          | ✅ | ❌ |
| Ver obras, etapas, diário e gastos     | ✅ (as suas) | ✅ (só as vinculadas a ele) |
| Aprovar etapa concluída                | ❌ | ✅ |
| Comentar em etapas                     | ✅ | ✅ |
| Gerar relatório (imprimir/PDF)         | ✅ | ✅ |

## Estrutura

```
obracheck/
├── config/              # configurações do projeto Django
├── core/
│   ├── models.py        # Usuario, Obra, Etapa, RegistroDiario, Gasto, Comentario
│   ├── views.py         # regras de acesso e telas
│   ├── forms.py         # validações dos formulários
│   ├── tests.py         # testes automatizados
│   ├── templates/       # telas (HTML)
│   └── management/commands/popular_demo.py
├── static/css/style.css # identidade visual (laranja #FF6B1A, grafite #2B2D33)
├── docs/REQUISITOS.md   # requisitos do MVP
└── requirements.txt
```

Requisitos completos em [`docs/REQUISITOS.md`](docs/REQUISITOS.md).
