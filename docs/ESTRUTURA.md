# ObraCheck — Como o projeto funciona, de cabo a rabo

> Guia para entender o sistema por dentro: primeiro o **back-end** (Python/Django e banco de dados), depois o **front-end** (telas, CSS e JavaScript), e por fim **o que o projeto tem de diferente** e **o que fazer para ele virar um sistema escalável**.

---

## Sumário

0. [Resumo em 1 minuto](#0-resumo-em-1-minuto)
1. [Arquitetura geral e o caminho de uma requisição](#1-arquitetura-geral-e-o-caminho-de-uma-requisição)
2. [Mapa de pastas e arquivos](#2-mapa-de-pastas-e-arquivos)

**Parte 1 — Back-end**

3. [Configuração do projeto (`config/`)](#3-configuração-do-projeto-config)
4. [Banco de dados: tem? como funciona?](#4-banco-de-dados-tem-como-funciona)
5. [Models: as tabelas e as regras de negócio](#5-models-as-tabelas-e-as-regras-de-negócio)
6. [URLs e views: o que acontece em cada endereço](#6-urls-e-views-o-que-acontece-em-cada-endereço)
7. [Segurança e permissões](#7-segurança-e-permissões)
8. [Formulários e validações](#8-formulários-e-validações)
9. [Painel administrativo (`/admin`)](#9-painel-administrativo-admin)
10. [Dados de demonstração (`popular_demo`)](#10-dados-de-demonstração-popular_demo)
11. [Testes automatizados](#11-testes-automatizados)

**Parte 2 — Front-end**

12. [Como as telas são geradas](#12-como-as-telas-são-geradas)
13. [Templates: herança, blocos e includes](#13-templates-herança-blocos-e-includes)
14. [Filtros próprios (`brl` e `iniciais`)](#14-filtros-próprios-brl-e-iniciais)
15. [CSS: o design system](#15-css-o-design-system)
16. [JavaScript: o pouco que existe e por quê](#16-javascript-o-pouco-que-existe-e-por-quê)
17. [Responsividade e acessibilidade](#17-responsividade-e-acessibilidade)

**Parte 3 — Visão de produto**

18. [O que o ObraCheck tem de diferente](#18-o-que-o-obracheck-tem-de-diferente)
19. [Limitações atuais (honestas)](#19-limitações-atuais-honestas)
20. [Como tornar o sistema escalável](#20-como-tornar-o-sistema-escalável)
21. [Glossário rápido](#21-glossário-rápido)

---

## 0. Resumo em 1 minuto

- **O que é:** um sistema web para pequenas obras e reformas que conecta **dois lados**: a **construtora** (que executa) e o **dono da obra** (que contratou).
- **Linguagem e framework:** **Python** com **Django 6** (instalado: 6.1.3). Tudo, do login ao cálculo de progresso, roda no servidor em Python.
- **Banco de dados:** **sim, tem.** É um **SQLite**, que fica em um único arquivo: `obracheck/db.sqlite3`. O Django conversa com ele pelo **ORM** (você escreve Python e o Django gera o SQL).
- **Telas:** HTML gerado no servidor pelos **templates do Django**, com **um único arquivo CSS** próprio (`static/css/style.css`) e quase nenhum JavaScript.
- **Arquitetura:** monolito Django no padrão **MTV** (Model, Template, View), com **um app** chamado `core`.
- **Qualidade:** 15 testes automatizados cobrem regras de negócio e permissões.

---

## 1. Arquitetura geral e o caminho de uma requisição

O Django segue o padrão **MTV**, que é o MVC com outros nomes:

| Camada | No Django se chama | No ObraCheck fica em | Responsabilidade |
|---|---|---|---|
| Dados | **Model** | `core/models.py` | Define as tabelas e as regras de negócio |
| Lógica | **View** | `core/views.py` | Recebe o pedido, checa permissão, busca dados, escolhe a tela |
| Apresentação | **Template** | `core/templates/` | O HTML que o usuário vê |

### O que acontece quando alguém abre uma obra

Exemplo: o dono da obra clica em "Reforma da casa — Maria" (`/obras/1/`).

```
 Navegador                    Servidor Django                                   Banco (SQLite)
 ─────────                    ──────────────                                    ──────────────
 GET /obras/1/  ───────────▶  1. Middlewares
  (com cookie                    • Sessão: lê o cookie e descobre QUEM é
   de sessão)                    • Autenticação: coloca o usuário em request.user
                                 • CSRF, segurança, mensagens
                              2. config/urls.py → core/urls.py
                                 "obras/<int:pk>/" → views.obra_detalhe(pk=1)
                              3. View obra_detalhe
                                 • @login_required: não logado? → vai pro login
                                 • pegar_obra(): busca SÓ entre as obras    ───▶  SELECT ... FROM core_obra
                                   do usuário (se não for dele → 404)       ◀───  WHERE dono_id = ... AND id = 1
                                 • busca etapas, comentários, gastos, diário ───▶  (mais SELECTs)
                              4. Template obra_detalhe.html
                                 • herda de base.html
                                 • preenche com os dados (progresso, R$...)
 HTML pronto  ◀────────────   5. Resposta HTTP 200 com o HTML
 + CSS (style.css)
```

Ponto importante: **o navegador recebe a página pronta.** Ele não monta nada. Isso se chama **renderização no servidor** (SSR).

### Quando o usuário envia um formulário (ex.: lançar gasto)

```
POST /obras/1/gastos/novo/  →  view gasto_novo
   ├─ @require_POST          (só aceita POST)
   ├─ @somente_construtora   (dono da obra recebe 403)
   ├─ pegar_obra()           (a obra precisa ser dessa construtora)
   ├─ GastoForm valida       (valor > 0, campos obrigatórios)
   ├─ salva no banco         (INSERT INTO core_gasto ...)
   ├─ checa RN05             (passou de 90%? mensagem de alerta)
   └─ redirect → /obras/1/?aba=gastos   (padrão Post/Redirect/Get)
```

O padrão **Post/Redirect/Get** evita que, ao apertar F5, o navegador reenvie o formulário e lance o gasto duas vezes.

---

## 2. Mapa de pastas e arquivos

```
TrabalhoRicardo/
└── obracheck/                      ← raiz do projeto Django
    ├── manage.py                   ← "controle remoto" do Django (runserver, migrate, test...)
    ├── requirements.txt            ← dependências Python: Django e Pillow
    ├── db.sqlite3                  ← O BANCO DE DADOS (um arquivo só)
    ├── README.md                   ← como instalar e rodar
    ├── .gitignore                  ← o que NÃO vai pro Git (banco, fotos, venv)
    │
    ├── config/                     ← configuração do PROJETO
    │   ├── settings.py             ← todas as configurações (banco, apps, idioma, fuso...)
    │   ├── urls.py                 ← roteador principal (/admin + rotas do core)
    │   ├── wsgi.py / asgi.py       ← ponto de entrada para servidores de produção
    │
    ├── core/                       ← o APP principal (toda a regra do ObraCheck)
    │   ├── models.py               ← tabelas + regras de negócio
    │   ├── views.py                ← lógica de cada tela + controle de acesso
    │   ├── urls.py                 ← lista de endereços do sistema
    │   ├── forms.py                ← formulários e validações
    │   ├── admin.py                ← configuração do /admin
    │   ├── tests.py                ← 15 testes automatizados
    │   ├── migrations/             ← histórico das mudanças no banco
    │   │   └── 0001_initial.py     ← cria todas as tabelas
    │   ├── management/commands/
    │   │   └── popular_demo.py     ← comando que cria dados de exemplo
    │   ├── templatetags/
    │   │   └── obracheck.py        ← filtros |brl e |iniciais
    │   └── templates/
    │       ├── core/               ← telas do sistema
    │       │   ├── base.html               ← esqueleto comum (topo, rodapé, mensagens)
    │       │   ├── inicio.html             ← landing page
    │       │   ├── painel_construtora.html ← painel da construtora
    │       │   ├── painel_dono.html        ← painel do dono
    │       │   ├── obra_detalhe.html       ← obra: Kanban, diário e gastos (abas)
    │       │   ├── relatorio.html          ← relatório + botão Baixar PDF
    │       │   ├── form.html               ← tela genérica de formulário
    │       │   ├── confirmar.html          ← "tem certeza que quer excluir?"
    │       │   ├── _campos.html            ← pedaço: desenha os campos de um form
    │       │   └── _obra_card.html         ← pedaço: card de obra
    │       └── registration/
    │           ├── login.html
    │           └── cadastro.html
    │
    ├── static/                     ← arquivos fixos servidos ao navegador
    │   ├── css/style.css           ← TODO o visual do sistema
    │   └── img/                    ← logo, capacete, favicon
    │
    ├── media/                      ← arquivos ENVIADOS pelos usuários (fotos do diário)
    │   └── diario/
    │
    └── docs/
        ├── REQUISITOS.md           ← requisitos funcionais e regras de negócio
        ├── ESTRUTURA.md            ← este documento
        └── telas/                  ← prints das telas
```

> **Projeto x App:** no Django, o *projeto* (`config/`) é a configuração geral e os *apps* são módulos de funcionalidade. O ObraCheck tem um app só (`core`), o que é adequado para um MVP.

---

# PARTE 1 — BACK-END

## 3. Configuração do projeto (`config/`)

### `settings.py`: as linhas que importam

| Configuração | Valor | O que significa |
|---|---|---|
| `INSTALLED_APPS` | admin, auth, sessions, messages, staticfiles, **core** | Módulos ligados. `auth` cuida de login e senha, `sessions` lembra quem está logado e `messages` mostra avisos como "Gasto registrado". |
| `DATABASES` | `sqlite3` → `BASE_DIR / "db.sqlite3"` | O banco é o arquivo `db.sqlite3` |
| `AUTH_USER_MODEL` | `"core.Usuario"` | O sistema usa um **usuário próprio** (com perfil, telefone e empresa), não o padrão do Django |
| `LOGIN_URL` / `LOGIN_REDIRECT_URL` / `LOGOUT_REDIRECT_URL` | `login` / `painel` / `login` | Para onde mandar o usuário antes e depois de entrar ou sair |
| `LANGUAGE_CODE` / `TIME_ZONE` | `pt-br` / `America/Fortaleza` | Mensagens em português e horário do Piauí. `USE_TZ = True` grava as datas em UTC no banco e converte na hora de mostrar. |
| `AUTH_PASSWORD_VALIDATORS` | 4 validadores | Senha não pode ser curta (mín. 8), comum, só números ou parecida com o nome |
| `STATIC_URL` / `STATICFILES_DIRS` | `static/` | Onde ficam CSS e imagens fixas |
| `MEDIA_URL` / `MEDIA_ROOT` | `/media/` → pasta `media/` | Onde ficam as fotos enviadas |
| `MIDDLEWARE` | sessão, CSRF, autenticação, mensagens, clickjacking | "Camadas" por onde toda requisição passa (seção 7) |
| `DEBUG` | `True` | Modo desenvolvimento: mostra erros detalhados. **Precisa ser `False` em produção.** |
| `SECRET_KEY` | escrita no código | Chave que assina sessões e tokens. **Em produção, precisa vir de variável de ambiente.** |

### `config/urls.py`

```python
urlpatterns = [
    path("admin/", admin.site.urls),      # painel administrativo
    path("", include("core.urls")),       # todo o resto vem do app core
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # serve as fotos
```

A última linha faz o próprio Django servir as fotos. Isso **só funciona com `DEBUG = True`**. Em produção, quem serve as fotos é outro serviço (seção 20).

---

## 4. Banco de dados: tem? como funciona?

### 4.1 Sim, tem banco, e é o SQLite

- **Onde está:** `obracheck/db.sqlite3`, hoje com uns 200 KB.
- **O que é o SQLite:** um banco **relacional e SQL de verdade** (tabelas, chaves estrangeiras, índices, transações), só que **embutido**. Não tem um servidor separado como MySQL ou PostgreSQL: o banco inteiro é um arquivo, e o Python o lê direto.
- **Por que foi escolhido:** não exige instalar nada, vem com o Python e é perfeito para desenvolvimento e MVP.
- **Está no Git?** Não. O `.gitignore` ignora o `db.sqlite3` e a pasta `media/`. Quem clona o projeto cria um banco novo com `migrate` + `popular_demo`.

### 4.2 Como o código conversa com o banco: o ORM

Você **não escreve SQL** no ObraCheck. Escreve Python e o **ORM do Django** traduz:

| Você escreve (Python) | O Django executa (SQL) |
|---|---|
| `Obra.objects.filter(dono=user)` | `SELECT * FROM core_obra WHERE dono_id = 5` |
| `obra.gastos.aggregate(t=Sum("valor"))` | `SELECT SUM(valor) FROM core_gasto WHERE obra_id = 1` |
| `Gasto.objects.create(obra=o, valor=650, ...)` | `INSERT INTO core_gasto (...) VALUES (...)` |
| `etapa.save()` | `UPDATE core_etapa SET status = ... WHERE id = 3` |
| `obra.delete()` | `DELETE FROM core_obra WHERE id = 1` (+ os filhos, em cascata) |

Vantagens: protege contra **SQL injection** (os valores nunca são colados no SQL como texto) e permite **trocar de banco** (SQLite → PostgreSQL) mudando só o `settings.py`.

### 4.3 Migrações: o "controle de versão" do banco

1. Você descreve as tabelas em `models.py`.
2. `python manage.py makemigrations` gera um arquivo em `core/migrations/` descrevendo a mudança (hoje existe só o `0001_initial.py`, que cria tudo).
3. `python manage.py migrate` aplica essas mudanças no banco de verdade.
4. O Django anota quais migrações já rodou na tabela `django_migrations` (hoje com 19 registros: as do Django + a do `core`).

Para criar um campo novo amanhã, basta alterar o model e rodar `makemigrations` e `migrate`. Ninguém mexe no banco à mão.

### 4.4 As tabelas que existem hoje

Tabelas do **ObraCheck** (app `core`):

| Tabela | Model | Registros hoje | Guarda |
|---|---|---|---|
| `core_usuario` | `Usuario` | 6 | Contas (construtoras, donos, admin) |
| `core_obra` | `Obra` | 4 | Obras/reformas |
| `core_etapa` | `Etapa` | 12 | Etapas do Kanban |
| `core_gasto` | `Gasto` | 9 | Lançamentos de gastos |
| `core_registrodiario` | `RegistroDiario` | 3 | Diário de obra (texto + caminho da foto) |
| `core_comentario` | `Comentario` | 2 | Comentários nas etapas |

Tabelas **do próprio Django** (criadas automaticamente):

| Tabela | Para que serve |
|---|---|
| `django_session` | **Sessões de login.** Quando você entra, o Django grava aqui uma linha e manda ao navegador um cookie `sessionid` com o código dessa linha. |
| `auth_permission`, `auth_group`, `core_usuario_groups`… | Sistema de permissões e grupos do Django (usado pelo `/admin`) |
| `django_content_type` | Catálogo interno dos models |
| `django_admin_log` | Histórico de ações feitas no `/admin` |
| `django_migrations` | Quais migrações já foram aplicadas |

### 4.5 Diagrama das tabelas e relacionamentos

```
                         ┌──────────────────────────────┐
                         │          core_usuario        │
                         │──────────────────────────────│
                         │ id (PK)                      │
                         │ username (único)             │
                         │ email (único)                │
                         │ password (hash, nunca texto) │
                         │ first_name                   │
                         │ perfil: construtora | dono   │
                         │ telefone, empresa            │
                         └──────────────────────────────┘
                     construtora_id │ 1         1 │ dono_id (opcional)
                         (CASCADE)  │             │ (SET_NULL)
                                    ▼ N         N ▼
                         ┌──────────────────────────────┐
                         │           core_obra          │
                         │──────────────────────────────│
                         │ id (PK)                      │
                         │ construtora_id (FK) ─────────┘ quem gerencia
                         │ dono_id (FK, pode ser nulo)    quem contratou
                         │ nome, endereco, descricao    │
                         │ data_inicio, data_prevista   │
                         │ orcamento (decimal 12,2)     │
                         │ status, criada_em            │
                         └──────────────────────────────┘
              ┌──────────────────┬──────────┴───────────┐
              │ 1:N CASCADE      │ 1:N CASCADE          │ 1:N CASCADE
              ▼                  ▼                      ▼
   ┌────────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
   │     core_etapa     │ │    core_gasto    │ │ core_registrodiario  │
   │────────────────────│ │──────────────────│ │──────────────────────│
   │ obra_id (FK)       │ │ obra_id (FK)     │ │ obra_id (FK)         │
   │ titulo, descricao  │ │ descricao        │ │ autor_id (FK usuário)│
   │ prazo, status      │ │ categoria        │ │ data, texto          │
   │ ordem              │ │ valor (decimal)  │ │ foto (caminho do     │
   │ aprovada,          │ │ data             │ │   arquivo em media/) │
   │ aprovada_em        │ └──────────────────┘ └──────────────────────┘
   └────────────────────┘
              │ 1:N CASCADE
              ▼
   ┌────────────────────┐
   │  core_comentario   │
   │────────────────────│
   │ etapa_id (FK)      │
   │ autor_id (FK)      │
   │ texto, criado_em   │
   └────────────────────┘
```

**O que acontece quando algo é excluído** (o `on_delete`):

| Se excluir… | Acontece com… | Regra |
|---|---|---|
| Uma **obra** | todas as etapas, gastos, registros do diário e (via etapas) comentários | **CASCADE**: tudo é apagado junto |
| Uma **construtora** (usuário) | todas as obras dela (e tudo dentro delas) | **CASCADE** |
| Um **dono** (usuário) | as obras **continuam**, só ficam "sem dono vinculado" | **SET_NULL** |
| Uma **etapa** | os comentários dela | **CASCADE** |

**Índices:** o Django cria um índice automaticamente para **cada chave estrangeira** (`obra_id`, `dono_id`, `construtora_id`, `autor_id`…) e para os campos únicos (`username`, `email`). Isso deixa rápidas as buscas do tipo "gastos da obra X".

### 4.6 Onde ficam as fotos? Não é no banco

O campo `foto` do diário é um `ImageField`. No banco vai **só o caminho** (ex.: `diario/diario_12.jpg`); o arquivo vai para a pasta `media/diario/`. É a prática correta, porque bancos não são bons para guardar arquivos grandes. A biblioteca **Pillow** confere se o arquivo enviado é mesmo uma imagem.

### 4.7 Senhas e sessões

- **Senhas** nunca são guardadas em texto. O Django salva um **hash PBKDF2-SHA256 com salt** e milhares de iterações (ex.: `pbkdf2_sha256$...$...`). Nem quem tem acesso ao banco descobre a senha.
- **Sessões** ficam na tabela `django_session`. O navegador só guarda o cookie com o ID da sessão.

### 4.8 Como inspecionar o banco

- Pelo **`/admin`** (logado como `admin`, senha `obra1234`).
- Pelo **shell do Django:** `python manage.py shell` e depois `from core.models import Obra; Obra.objects.all()`.
- Por um programa visual, como o **DB Browser for SQLite**: é só abrir o `db.sqlite3`.
- Pelo terminal: `python manage.py dbshell` (se o `sqlite3` estiver instalado).

---

## 5. Models: as tabelas e as regras de negócio

O `models.py` define as tabelas **e** concentra as regras de negócio. É o padrão "**fat models, thin views**": a regra mora no model, e qualquer tela que use o model já ganha a regra pronta.

### `Usuario` (herda de `AbstractUser`)
Herda tudo do usuário padrão do Django (username, senha, nome, `is_staff`…) e adiciona:
- `perfil`: `"construtora"` ou `"dono"` (um `TextChoices`, ou seja, uma lista fechada de opções).
- `email` **único**, porque é por ele que a construtora encontra o dono.
- `telefone`, `empresa`.
- Atalhos `is_construtora` e `is_dono`, usados nas views e nos templates.

### `Obra`
Campos de cadastro mais estes **cálculos (properties)**, que não são colunas no banco: são calculados na hora a partir dos dados.

| Property | Regra | Como calcula |
|---|---|---|
| `progresso` | **RN03** | etapas concluídas ÷ total × 100 (2 consultas) |
| `total_gasto` | — | `SUM(valor)` dos gastos |
| `percentual_gasto` | — | total gasto ÷ orçamento × 100 |
| `alerta_orcamento` | **RN05** | `percentual_gasto >= 90` |
| `saldo` | — | orçamento − total gasto |
| `etapas_atrasadas` | **RN04** | não concluídas com prazo < hoje |
| `atrasada` | — | obra não concluída e `data_prevista` < hoje |

> **Por que calcular e não guardar?** Assim o valor nunca fica desatualizado. O custo é refazer a conta toda vez (ver seção 19).

Valores de dinheiro usam **`DecimalField`** (12 dígitos, 2 casas) e **`Decimal`** no Python, nunca `float`. Isso evita erros de arredondamento como `0.1 + 0.2 = 0.30000000000000004`, que seriam inaceitáveis em valores financeiros.

### `Etapa`
- `status`: `a_fazer` → `andamento` → `concluida` (as colunas do Kanban).
- `ordem`: posição na coluna.
- `aprovada` / `aprovada_em`: aprovação do dono (**RN06**).
- Regra no **`save()`**: se a etapa sair de "concluída", a aprovação **é apagada automaticamente**. Se a construtora reabrir uma etapa aprovada, o dono vai precisar aprovar de novo. Como está no `save()`, a regra vale em qualquer lugar do sistema (views, admin, shell).
- `atrasada` (**RN04**): prazo vencido e não concluída.

### `RegistroDiario`, `Gasto`, `Comentario`
- `RegistroDiario`: obra, autor, data (padrão: hoje), texto e foto opcional.
- `Gasto`: descrição, **categoria** (material, mão de obra, equipamento, transporte, outros), valor e data.
- `Comentario`: etapa, autor, texto e data/hora.

Cada model tem `class Meta: ordering = [...]`, que define a ordem padrão (ex.: diário do mais novo para o mais antigo).

---

## 6. URLs e views: o que acontece em cada endereço

Todas as rotas ficam em `core/urls.py`:

| Endereço | View | Quem pode | O que faz |
|---|---|---|---|
| `/` | `inicio` | todos | Landing page (logado → vai para o painel) |
| `/entrar/` | `LoginView` (do Django) | todos | Login |
| `/sair/` | `LogoutView` (do Django) | logado | Logout (só por POST) |
| `/cadastro/` | `cadastro` | todos | Cria a conta e já faz login |
| `/painel/` | `painel` | logado | Mostra o painel **da construtora** ou **do dono**, conforme o perfil |
| `/obras/nova/` | `obra_nova` | construtora | Cadastrar obra |
| `/obras/<id>/` | `obra_detalhe` | dona da obra / dono vinculado | Abas: `?aba=etapas`, `?aba=diario`, `?aba=gastos` |
| `/obras/<id>/editar/` | `obra_editar` | construtora | Editar obra / vincular dono |
| `/obras/<id>/excluir/` | `obra_excluir` | construtora | Confirma (GET) e exclui (POST) |
| `/obras/<id>/relatorio/` | `relatorio` | ambos | Relatório + download em PDF |
| `/obras/<id>/etapas/nova/` | `etapa_nova` | construtora | Nova etapa |
| `/etapas/<id>/editar/` | `etapa_editar` | construtora | Editar etapa |
| `/etapas/<id>/excluir/` | `etapa_excluir` | construtora | Excluir etapa |
| `/etapas/<id>/mover/` | `etapa_mover` | construtora (POST) | Move no Kanban |
| `/etapas/<id>/aprovar/` | `etapa_aprovar` | **dono** (POST) | Aprova etapa concluída |
| `/etapas/<id>/comentar/` | `comentario_novo` | ambos (POST) | Comenta |
| `/obras/<id>/diario/novo/` | `diario_novo` | construtora (POST) | Novo registro com foto |
| `/obras/<id>/gastos/novo/` | `gasto_novo` | construtora (POST) | Lança gasto (+ alerta de 90%) |
| `/gastos/<id>/excluir/` | `gasto_excluir` | construtora (POST) | Remove gasto |
| `/admin/` | admin do Django | superusuário | Painel administrativo |

### Destaques das views

- **`painel`**: uma única URL que decide a tela pelo perfil. Calcula obras ativas e concluídas, etapas atrasadas e total gasto x orçado. Para o dono, também busca as **etapas aguardando aprovação** e os **5 últimos registros do diário**.
- **`obra_detalhe`**: monta as **3 colunas do Kanban** em Python (separa as etapas por status), soma os **gastos por categoria** e entrega formulários vazios para as abas. Usa `prefetch_related("comentarios__autor")` para trazer os comentários de todas as etapas em poucas consultas.
- **`etapa_mover`**: o Kanban **não usa arrastar e soltar**. Cada botão ("Iniciar →", "Concluir ✔", "←") é um mini-formulário POST com o novo status. A view confere se o status recebido é válido (`if novo in Etapa.Status.values`) antes de salvar.
- **`etapa_aprovar`**: só o **dono vinculado àquela obra** acha a etapa (`obra__dono=request.user`), e só aprova se ela estiver concluída.
- **Mensagens** (`messages.success/warning/error`): os avisos coloridos no topo da tela, como "Gasto registrado." ou "Atenção: esta obra já usou 94% do orçamento".

---

## 7. Segurança e permissões

### 7.1 Três camadas de controle de acesso (`views.py`)

1. **Está logado?** `@login_required`. Se não estiver, vai para `/entrar/`.
2. **Tem o perfil certo?** Decorators próprios:
   ```python
   @somente_construtora   # dono que tentar → erro 403 (Proibido)
   @somente_dono          # construtora que tentar → erro 403
   ```
3. **A obra é dele?** Esse é o ponto mais importante (**RN02**). Toda busca de obra passa por:
   ```python
   def obras_do_usuario(user):
       if user.is_construtora:
           return Obra.objects.filter(construtora=user)
       return Obra.objects.filter(dono=user)
   ```
   A view **nunca** busca "a obra 7". Ela busca "a obra 7 **entre as obras deste usuário**". Se a obra for de outra pessoa, o resultado é **404 (não encontrado)**, e não 403. Assim um intruso nem descobre se a obra existe. Etapas, gastos e comentários seguem a mesma lógica (`obra__construtora=request.user`).

> Isso impede o ataque mais comum em sistemas assim, o **IDOR**: trocar o número na URL (`/obras/1/` → `/obras/2/`) para ver dados de outra pessoa. Os testes `test_rn02_dono_so_ve_suas_obras` e `test_construtora_nao_ve_obra_de_outra` garantem isso.

### 7.2 Proteções que o Django dá de graça

| Ameaça | Proteção | Onde |
|---|---|---|
| **CSRF** (site falso enviando formulário em seu nome) | `{% csrf_token %}` em todo `<form method="post">` + `CsrfViewMiddleware` | todos os forms |
| **XSS** (injetar `<script>` num comentário) | Os templates **escapam** tudo automaticamente: `<script>` vira texto | todos os templates |
| **SQL injection** | O ORM nunca monta SQL juntando texto | todo acesso ao banco |
| **Clickjacking** (seu site dentro de um iframe invisível) | `XFrameOptionsMiddleware` | global |
| **Senha fraca / vazada** | 4 validadores + hash PBKDF2 | cadastro |
| **Ação por link (GET)** | `@require_POST` em mover, aprovar, comentar, lançar, excluir | views |

---

## 8. Formulários e validações

Os forms (`forms.py`) **validam os dados antes** de qualquer coisa chegar ao banco:

| Form | Validações especiais |
|---|---|
| `CadastroForm` | Herda do `UserCreationForm` (senha + confirmação + validadores). Escolha de perfil por botões de rádio. **E-mail duplicado não pode** (compara sem diferenciar maiúsculas). |
| `ObraForm` | Campo extra **`email_dono`**: procura um usuário **com perfil dono** com aquele e-mail e vincula (**RF03**). Se não achar, mostra erro claro. Data de entrega não pode ser antes do início. Orçamento > 0. |
| `EtapaForm` | Campos de data usam `<input type="date">` (calendário nativo). |
| `RegistroDiarioForm` | Aceita upload de foto (`request.FILES`). |
| `GastoForm` | Valor precisa ser > 0. |
| `ComentarioForm` | Só o texto. A etapa e o autor são preenchidos pela view, **nunca pelo usuário**. |

Repare no padrão `form.save(commit=False)`: a view cria o objeto, **completa os campos sensíveis no servidor** (`obra.construtora = request.user`, `gasto.obra = obra`, `comentario.autor = request.user`) e só então salva. Assim o usuário nunca escolhe "de quem" é o registro.

---

## 9. Painel administrativo (`/admin`)

Configurado em `admin.py`:
- **Usuários:** lista com username, nome, e-mail, perfil e empresa, com filtro por perfil.
- **Obras:** lista com construtora, dono, status, entrega e orçamento, com filtro e busca. As **etapas aparecem dentro da obra** (`EtapaInline`).
- Etapas, gastos, diário e comentários também podem ser editados.

Serve para suporte e manutenção, sem precisar abrir o banco.

---

## 10. Dados de demonstração (`popular_demo`)

`python manage.py popular_demo` é um **comando próprio** (`core/management/commands/popular_demo.py`) que:
1. Apaga e recria os usuários de demonstração (`admin`, `construtora`, `cliente`, `cliente2`), todos com senha `obra1234`.
2. Cria 3 obras pensadas para mostrar **cada regra funcionando**:
   - **Reforma da casa — Maria:** em andamento, com etapa aprovada, etapa aguardando aprovação, etapa atrasada, comentários, gastos em várias categorias e diário **com fotos geradas pelo Pillow**.
   - **Construção de muro e garagem:** com gasto em 94% do orçamento (dispara o **alerta de 90%**) e entrega atrasada.
   - **Ampliação de loja — Centro:** em planejamento e **sem dono vinculado**.
3. As datas são **relativas a hoje** (`hoje + timedelta(dias)`), então a demonstração parece atual em qualquer dia.

---

## 11. Testes automatizados

`python manage.py test core` roda **15 testes** (`core/tests.py`). O Django cria um **banco temporário só para os testes** e apaga no fim, então o seu `db.sqlite3` não é tocado.

| Grupo | Testes |
|---|---|
| **Regras de negócio** | progresso (RN03), etapa atrasada (RN04), alerta a partir de 90% (RN05), aprovação some se a etapa sair de concluída (RN06) |
| **Permissões** | dono não cria obra (RN01), dono só vê as suas (RN02), construtora não vê obra de outra, dono não move etapa, dono aprova etapa concluída, dono não aprova etapa não concluída |
| **Fluxos** | cadastro com perfil (RF01), criar obra e vincular dono por e-mail (RF02/RF03), e-mail de dono inexistente dá erro, gasto negativo é recusado (RF06), páginas principais abrem |

Cada teste leva no nome o requisito que ele comprova (ex.: `test_rn05_...`), ligando código e documentação de requisitos.

---

# PARTE 2 — FRONT-END

## 12. Como as telas são geradas

O ObraCheck **não é** um SPA (React, Vue, Angular). É **renderização no servidor**:

```
Dados do banco ──▶ View (Python) ──▶ Template (HTML + {{ variáveis }}) ──▶ HTML pronto ──▶ Navegador
```

- Navegar entre telas = **carregar uma página nova**.
- As abas da obra (Etapas / Diário / Gastos) são **links com `?aba=`**, não JavaScript.
- Mover etapa, aprovar e comentar são **formulários HTML comuns** (POST + redirect).

**Por que essa escolha:** menos código, nada de API para manter, funciona em celulares fracos, a segurança fica toda no servidor e o sistema funciona até com o JavaScript desligado. O "preço" é que cada ação recarrega a página (seção 20 mostra como evoluir isso).

---

## 13. Templates: herança, blocos e includes

### Herança: `base.html` é o esqueleto

Toda tela começa com `{% extends "core/base.html" %}` e preenche só os **blocos** que precisa:

```
base.html
├── <head>: fonte Inter, favicon, style.css
├── {% block titulo %}       → texto da aba do navegador
├── <header class="topo">    → logo + menu (muda se está logado ou não, e por perfil)
├── {% block hero %}         → área de largura total ANTES do conteúdo (usada na landing)
├── <main class="container">
│     ├── mensagens (avisos verdes/vermelhos/amarelos)
│     └── {% block conteudo %}   → o miolo de cada tela
├── {% block depois %}       → seções/scripts DEPOIS do conteúdo (landing, script do PDF)
└── <footer>
```

### Includes: pedaços reaproveitados

| Arquivo | Usado em | O que faz |
|---|---|---|
| `_campos.html` | form, login, cadastro | Desenha **qualquer** formulário: label, campo, ajuda e erros. Por isso um só `form.html` serve para criar/editar obra e etapa. |
| `_obra_card.html` | os dois painéis | O card de obra (status, barras de progresso e gasto, dono/construtora, entrega). Mostra "dono" para a construtora e "construtora" para o dono. |

### Lógica nos templates (pouca, de propósito)

- `{% if user.is_construtora %}`: mostra botões de editar/mover só para a construtora, e "Aprovar" só para o dono. **Atenção:** isso é só para a tela ficar limpa. A **proteção real** está nas views (seção 7). Mesmo que alguém forje o formulário, o servidor recusa.
- `{% for ... %}{% empty %}`: listas com mensagem de "vazio" ("Nenhuma etapa", "Nenhum gasto lançado").
- Filtros prontos do Django: `|date:"d/m/Y"`, `|truncatechars:110`, `|linebreaksbr`, `|default:`, `|slugify` (nome do arquivo PDF).

### Variáveis disponíveis em toda tela (context processors)

- `user`: o usuário logado (`user.is_authenticated`, `user.is_construtora`…).
- `messages`: os avisos.
- `request`: a requisição atual.

---

## 14. Filtros próprios (`brl` e `iniciais`)

Em `core/templatetags/obracheck.py`, carregados com `{% load obracheck %}`:

| Filtro | Entrada | Saída |
|---|---|---|
| `\|brl` | `16300.5` | `R$ 16.300,50` (formato brasileiro: ponto no milhar, vírgula nos centavos) |
| `\|iniciais` | `Carlos Silva` | `CS` (bolinha de avatar no topo) |

---

## 15. CSS: o design system

Um único arquivo, `static/css/style.css` (~525 linhas), **sem framework** (nada de Bootstrap ou Tailwind) e **sem etapa de build**.

### 15.1 Tokens (variáveis CSS)

No topo, em `:root`, ficam as "peças" do visual, reaproveitadas em tudo:

| Token | Valor | Uso |
|---|---|---|
| `--laranja` | `#FF6B1A` | cor da marca: botões, destaques |
| `--fundo` | `#120C09` | fundo marrom-grafite quase preto |
| `--grafite` | `#F4ECE6` | **cor do texto** (o nome ficou da versão clara) |
| `--cinza` | `#A2948A` | textos secundários |
| `--borda`, `--superficie` | brancos translúcidos | o efeito de **vidro** |
| `--verde`, `--vermelho`, `--amarelo` (+ `-claro`) | — | status: aprovado, atrasado, aguardando |
| `--raio` | `20px` | cantos arredondados |

Para mudar uma cor no sistema inteiro, basta alterar **uma linha**.

### 15.2 O estilo visual

- **Tema escuro com "vidro" (glassmorphism):** cards com fundo branco quase transparente, borda fina e `backdrop-filter: blur`.
- **Brilho laranja:** gradientes radiais suaves no fundo e sombras laranja nos botões principais.
- **Pílulas:** botões, selos de status e abas com cantos totalmente arredondados (`border-radius: 999px`).

### 15.3 Componentes (classes reaproveitáveis)

| Classe | O que é |
|---|---|
| `.btn`, `.btn-sec`, `.btn-ok`, `.btn-perigo`, `.btn-sm` | botões |
| `.card`, `.metrica`, `.obra-card` | caixas de vidro; cards de número; card de obra |
| `.barra` (+ `.verde` / `.vermelha`) | barra de progresso com brilho |
| `.selo-*` | etiquetas de status (`selo-andamento`, `selo-atraso`, `selo-aprovada`…) |
| `.abas` | seletor em "chips" (Etapas / Diário / Gastos) |
| `.kanban`, `.coluna`, `.tarefa` | quadro Kanban |
| `.msg-*` | avisos |
| `.aviso-vermelho` / `.aviso-amarelo` | card de alerta com faixa lateral |
| `.lp-*` | tudo da **landing page** (prefixo `lp` = *landing page*) |
| `.relatorio` | o relatório, que **redefine os tokens para cores claras** (fundo branco para PDF) |

As classes de status no HTML são montadas direto do banco: `class="selo selo-{{ obra.status }}"` vira `selo-andamento`. O CSS só precisa de uma regra para cada status.

### 15.4 Landing page (`inicio.html`)

Seções: **hero** (arco de luz girando, chips flutuantes, 3 cards de prévia do sistema com dados ilustrativos), faixa de diferenciais, **recursos** (card com gráfico SVG + 4 recursos), **"Obra não é sorte. É processo."** (passo a passo por perfil), **Planos** (Inicial grátis / Pro R$ 19,90 / Empresa R$ 49,90, os pagos marcados "Em breve") e CTA final.

Animações **só com CSS** (`@keyframes`): `flutuar`, `flutuar-lado`, `girar`, `pulsar`. Elas usam a propriedade `translate` (e não `transform`) para não conflitar com o efeito de hover.

### 15.5 Imagens (`static/img/`)

| Arquivo | Uso |
|---|---|
| `logo.png` | logo completa (capacete + "ObraCheck"), no relatório/PDF |
| `capacete-claro.png` | capacete com a faixa clareada para fundo escuro (topo, landing) |
| `capacete.png` | capacete original |
| `favicon.png` | ícone da aba do navegador |

---

## 16. JavaScript: o pouco que existe e por quê

Só **dois scripts pequenos**, cada um em um template:

1. **Landing (`inicio.html`) — revelar ao rolar:** usa `IntersectionObserver` para adicionar a classe `.visivel` quando um bloco entra na tela, e o CSS faz o "aparecer subindo". Se o JS não rodar, nada fica escondido, porque o efeito só liga quando o script adiciona a classe `anima` no `<html>`.
2. **Relatório (`relatorio.html`) — Baixar PDF:** usa a biblioteca **html2pdf.js** (carregada de um CDN) para "fotografar" o relatório e gerar um **PDF A4** que baixa como `relatorio-nome-da-obra.pdf`. Isso acontece **no navegador**, sem pesar no servidor. Precisa de internet para carregar a biblioteca.

Todo o resto (abas, Kanban, aprovar, comentar) funciona **sem JavaScript**.

---

## 17. Responsividade e acessibilidade

- **Responsivo:** `@media (max-width: 860px)` deixa Kanban, painéis e planos em **uma coluna**, as métricas em **2 por linha** e um topo mais enxuto. Abaixo de 1000px somem os chips flutuantes e o menu de âncoras da landing.
- **Movimento reduzido:** quem ativou "reduzir movimento" no sistema (`prefers-reduced-motion`) **não vê animações**.
- **Formulários:** todo campo tem `<label>` ligado ao input, e os erros aparecem embaixo de cada campo.
- **Impressão:** `@media print` esconde topo, botões e rodapé, e o relatório sai limpo (Ctrl+P ainda funciona).
- **Idioma:** `<html lang="pt-BR">`.

---

# PARTE 3 — VISÃO DE PRODUTO

## 18. O que o ObraCheck tem de diferente

1. **É uma plataforma de dois lados.** A maioria das ferramentas de obra é só para a construtora. Aqui o **cliente participa**: acompanha, comenta e **aprova** etapas. O valor está na transparência entre as duas partes.
2. **Aprovação formal de etapas (RN06), com data e hora registradas.** Vira um "aceite" documentado, útil em discussões de pagamento por etapa. E a aprovação **perde a validade sozinha** se a etapa for reaberta.
3. **Alerta automático de orçamento a partir de 90% (RN05)**, antes do estouro, não depois.
4. **Vínculo pelo e-mail (RF03):** sem convites complicados. O dono cria a conta e a construtora digita o e-mail dele.
5. **Isolamento de dados por usuário em todas as consultas.** Cada usuário só "existe" dentro das próprias obras, testado automaticamente.
6. **Leve e sem dependências pesadas:** 2 dependências Python (Django e Pillow), zero build de front-end e funciona em celular simples.
7. **Regras de negócio documentadas e testadas:** cada RN/RF tem teste com o mesmo código no nome.
8. **Relatório em PDF** para enviar ao cliente ou arquivar.

---

## 19. Limitações atuais (honestas)

Para um MVP acadêmico estão OK, mas é bom saber:

| Ponto | Situação hoje | Impacto |
|---|---|---|
| **Configuração de produção** | `DEBUG = True`, `SECRET_KEY` no código, `ALLOWED_HOSTS` vazio | **Não pode ir assim para a internet** |
| **Banco SQLite** | um arquivo, um "escritor" por vez | Ótimo para poucos usuários; trava com muitos acessos simultâneos |
| **Consultas repetidas (N+1)** | `progresso`, `total_gasto`, `percentual_gasto` e `alerta_orcamento` fazem consultas **cada vez que são chamados**. Cada card de obra dispara várias. O painel faz `sum(o.total_gasto for o in obras)`, uma consulta por obra. | Com 5 obras, imperceptível. Com 500, o painel fica lento. |
| **Sem paginação** | painel, diário e gastos listam **tudo** | Listas enormes com o tempo |
| **Fotos** | ficam no disco do servidor, sem limite de tamanho nem compressão | Disco enche; não funciona com vários servidores |
| **Fotos servidas pelo Django** | `static()` no `urls.py` | Só funciona em `DEBUG` |
| **PDF no navegador via CDN** | depende de internet e do navegador | Não dá para gerar o PDF automaticamente (ex.: enviar por e-mail) |
| **Sem notificações** | o dono só sabe que tem etapa para aprovar quando abre o sistema | Menos engajamento |
| **Um usuário = uma construtora** | não há "empresa com vários funcionários" | Construtora com equipe precisa dividir login |
| **Redirects com caminho fixo** | `redirect(f"/obras/{obra.pk}/?aba=gastos")` em vez de `reverse()` | Se a URL mudar, esses pontos quebram |

---

## 20. Como tornar o sistema escalável

"Escalável" = continuar rápido e estável quando passar de **10 para 10.000 usuários**. Aqui vai um roteiro **em fases**, do mais simples ao mais avançado.

### Fase 1 — Pronto para a internet (obrigatório antes de publicar)

1. **Variáveis de ambiente** para `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, credenciais do banco (biblioteca `django-environ` ou `os.environ`).
2. **Servidor de produção:** `gunicorn` (em vez do `runserver`, que é só para desenvolvimento) atrás de um **Nginx** ou de uma plataforma (Railway, Render, Fly.io, Azure…).
3. **Arquivos estáticos:** `python manage.py collectstatic` + **WhiteNoise** (serve o CSS e as imagens de forma eficiente).
4. **HTTPS** e as opções de segurança do Django: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`. O comando `python manage.py check --deploy` lista o que falta.
5. **Backup automático** do banco.

### Fase 2 — Banco de dados de verdade

6. **Trocar SQLite por PostgreSQL.** Graças ao ORM, muda **só o `DATABASES`** no `settings.py`; o resto do código fica igual. O PostgreSQL aguenta muitos acessos simultâneos, tem backups e réplicas e é o padrão do mercado com Django.
7. **Índices extras** nos campos mais filtrados: `Etapa.status`, `Etapa.prazo`, `Obra.status` (`class Meta: indexes = [...]`).
8. **Consultas otimizadas (acabar com o N+1):** calcular totais **no banco, de uma vez**, com `annotate`:
   ```python
   obras = obras_do_usuario(user).annotate(
       gasto_total=Coalesce(Sum("gastos__valor"), 0),
       total_etapas=Count("etapas", distinct=True),
       etapas_concluidas=Count("etapas", filter=Q(etapas__status="concluida"), distinct=True),
   )
   ```
   Assim o painel faz **poucas consultas**, não importa quantas obras existam. A ferramenta **django-debug-toolbar** mostra quantas consultas cada página faz.
9. **Paginação** (`django.core.paginator.Paginator`) em obras, diário e gastos.

### Fase 3 — Arquivos e desempenho

10. **Fotos em armazenamento de objetos** (Amazon S3, Cloudflare R2, Azure Blob) com `django-storages`. Os servidores ficam "sem estado" e podem ser multiplicados.
11. **Limitar e comprimir uploads** (ex.: máx. 5 MB, redimensionar para 1600px com Pillow, gerar miniatura).
12. **CDN** na frente dos estáticos e das fotos.
13. **Cache com Redis** para painéis e números agregados, invalidando quando entra um gasto ou muda uma etapa.
14. **Sessões no Redis** em vez do banco, se o tráfego crescer.

### Fase 4 — Trabalho em segundo plano

15. **Fila de tarefas** (**Celery** ou **Django-RQ** + Redis) para o que não precisa acontecer na hora do clique:
    - **e-mail/WhatsApp** "Tem etapa esperando sua aprovação" e "Obra passou de 90% do orçamento";
    - **gerar o PDF no servidor** (WeasyPrint ou ReportLab) e enviar ao cliente;
    - lembretes diários de etapas que vencem amanhã.

### Fase 5 — Produto maior

16. **Multiempresa (multi-tenant):** criar o model `Empresa`, com vários usuários (dono da empresa, engenheiro, mestre de obras) e permissões por papel. Hoje "construtora = 1 usuário".
17. **API REST** com **Django REST Framework**, para um **app de celular** (ex.: mestre de obras enviando foto do canteiro) e integrações.
18. **Interatividade sem virar SPA:** **HTMX** para mover etapas e lançar gastos **sem recarregar a página**, mantendo os templates Django. Arrastar e soltar no Kanban com SortableJS.
19. **Planos pagos de verdade:** model `Assinatura` + gateway (Stripe, Mercado Pago, Asaas) com webhooks, aplicando limites como "até 3 obras no plano Inicial".
20. **Auditoria/histórico:** registrar quem mudou o quê e quando (`django-simple-history`). Em obra, isso tem valor jurídico.

### Fase 6 — Operação

21. **Docker** (mesmo ambiente em todo lugar) + **CI** (GitHub Actions rodando os testes a cada push).
22. **Monitoramento de erros** (Sentry) e **logs** centralizados.
23. **Escala horizontal:** com banco PostgreSQL, fotos no S3 e sessões/cache no Redis, a aplicação Django fica **sem estado**, e dá para subir **vários servidores iguais** atrás de um balanceador de carga.

### Arquitetura alvo (resumo)

```
                    ┌──────────── CDN (CSS, imagens, fotos) ─────────────┐
                    │                                                     │
Usuários ──▶ HTTPS ──▶ Balanceador ──▶ Django + Gunicorn (N cópias) ──▶ PostgreSQL (+ réplica)
                                             │        │
                                             │        └──▶ Redis (cache, sessões, fila)
                                             │                    │
                                             └──▶ S3 (fotos)      └──▶ Workers Celery
                                                                       (e-mails, PDFs, lembretes)
```

> **Boa notícia:** a base do ObraCheck já está no formato certo para crescer. Regras nos models, permissões centralizadas, ORM (troca de banco fácil) e testes cobrindo o essencial. A evolução é **incremental**: não precisa reescrever nada.

---

## 21. Glossário rápido

| Termo | Significado |
|---|---|
| **Django** | Framework web em Python que já traz login, admin, ORM, formulários, segurança… |
| **MTV** | Model–Template–View, a divisão do Django (equivale ao MVC) |
| **ORM** | Camada que transforma código Python em SQL |
| **Migração** | Arquivo que descreve uma mudança no banco (criar tabela, adicionar campo) |
| **SQLite / PostgreSQL** | Bancos relacionais: o primeiro é um arquivo; o segundo é um servidor robusto |
| **FK (chave estrangeira)** | Coluna que aponta para outra tabela (ex.: `obra_id` no gasto) |
| **CASCADE / SET_NULL** | O que fazer com os "filhos" quando o "pai" é excluído |
| **Decorator** | `@algo` em cima de uma função para adicionar comportamento (ex.: exigir login) |
| **CSRF** | Ataque em que outro site envia formulários em seu nome; o token impede |
| **IDOR** | Ver dados alheios trocando o ID na URL; o filtro por usuário impede |
| **N+1** | Fazer 1 consulta para a lista + 1 para cada item; resolve-se com `annotate`, `select_related` e `prefetch_related` |
| **SSR** | Renderização no servidor: o HTML já chega pronto |
| **Post/Redirect/Get** | Após um POST, redirecionar, para o F5 não reenviar o formulário |
| **Glassmorphism** | Estilo visual de "vidro fosco" (transparência + desfoque) |
| **Escala horizontal** | Crescer adicionando mais servidores iguais, em vez de um servidor maior |

---

*Comandos úteis:* `python manage.py runserver` (rodar) · `python manage.py migrate` (criar/atualizar banco) · `python manage.py popular_demo` (dados de exemplo) · `python manage.py test core` (testes) · `python manage.py createsuperuser` (novo admin) · `python manage.py shell` (console Python com o projeto carregado).
