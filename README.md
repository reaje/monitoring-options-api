# Monitoring Options Backend API

API REST para monitoramento de operações com opções, desenvolvida com Python e Sanic.

## 📋 Requisitos

- Python 3.11+
- PostgreSQL (via Supabase)
- pip

## 🚀 Setup Rápido

### 1. Criar ambiente virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar .env com suas credenciais
# As credenciais do Supabase já estão configuradas
```

### 4. Rodar o servidor

```bash
python -m app.main
```

O servidor estará disponível em: `http://localhost:8000`

## 📚 Documentação da API

### 🎨 Documentação Interativa (Scalar)

Acesse a documentação completa e interativa com interface moderna:

**URL**: http://localhost:8000/scalar

**Recursos**:
- ✨ Interface moderna com dark mode
- 🔍 Busca rápida (atalho: `k`)
- 🧪 Try-it-out integrado
- 🔐 Autenticação JWT
- 📖 Schemas e exemplos

### 📄 Especificação OpenAPI

Para importar em Postman, Insomnia ou outras ferramentas:

**URL**: http://localhost:8000/api/docs/openapi.json

### 📝 Documentação Detalhada

- [DOCUMENTATION.md](./DOCUMENTATION.md) - Guia completo da documentação
- [API_ENDPOINTS.md](./API_ENDPOINTS.md) - Lista de todos os 58 endpoints

## 📚 Endpoints

### Health Check
```
GET /health
```

Retorna o status da API e da conexão com banco de dados.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "timestamp": "2025-01-22T10:30:00Z",
  "checks": {
    "database": "ok"
  }
}
```

### Root
```
GET /
```

Informações da API.

## 🏗️ Estrutura do Projeto

```
backend/
├── app/
│   ├── core/              # Utilitários core (logger, exceptions)
│   ├── database/          # Clientes de banco de dados
│   ├── routes/            # Endpoints da API
│   ├── services/          # Lógica de negócio
│   ├── workers/           # Background workers
│   ├── middleware/        # Middleware (auth, error handling)
│   ├── utils/             # Utilitários gerais
│   ├── config.py          # Configurações
│   └── main.py            # Entry point
├── tests/                 # Testes
├── requirements.txt       # Dependências
└── Dockerfile            # Container Docker
```

## 🧪 Testes

### Rodar Todos os Testes

```bash
# Instalar dependências de desenvolvimento
pip install -r requirements-dev.txt

# Rodar todos os testes
pytest

# Com output verbose
pytest -v

# Com coverage
pytest --cov=app --cov-report=html

# Abrir relatório de coverage
# No navegador: backend/htmlcov/index.html
```

### Rodar Testes Específicos

```bash
# Apenas testes unitários
pytest tests/unit/

# Apenas testes de integração
pytest tests/integration/

# Apenas testes de um arquivo
pytest tests/integration/test_auth_api.py

# Apenas testes de uma classe
pytest tests/integration/test_auth_api.py::TestAuthLogin

# Apenas um teste específico
pytest tests/integration/test_auth_api.py::TestAuthLogin::test_login_success
```

### Estrutura de Testes

```
tests/
├── conftest.py              # Fixtures compartilhados
├── unit/                    # Testes unitários
│   └── test_security.py     # Testes de segurança (JWT, bcrypt)
└── integration/             # Testes de integração (API)
    ├── test_auth_api.py     # Testes de autenticação
    ├── test_accounts_api.py # Testes de contas
    └── test_assets_api.py   # Testes de ativos
```

### Fixtures Disponíveis

- `test_user` - Cria usuário de teste
- `auth_token` - Token JWT para autenticação
- `auth_headers` - Headers com Bearer token
- `test_account` - Cria conta de teste
- `test_asset` - Cria ativo de teste
- `multiple_accounts` - Cria 3 contas
- `multiple_assets` - Cria 3 ativos (PETR4, VALE3, ITUB4)

## 🐳 Docker

### Build da imagem

```bash
docker build -t monitoring-options-api .
```

### Rodar container

```bash
docker run -p 8000:8000 --env-file .env monitoring-options-api
```

## 📖 Documentação da API

A documentação completa da API estará disponível em:
- OpenAPI/Scalar: `http://localhost:8000/docs` (em desenvolvimento)

## 🔧 Desenvolvimento

### Estrutura de branches
- `main` - Produção
- `develop` - Desenvolvimento
- `feature/*` - Novas funcionalidades
- `fix/*` - Correções de bugs

### Code Style

O projeto usa:
- **Black** para formatação
- **Flake8** para linting
- **MyPy** para type checking

```bash
# Formatar código
black app/

# Lint
flake8 app/

# Type check
mypy app/
```

## 📝 Variáveis de Ambiente

Principais variáveis (veja `.env.example` para lista completa):

```bash
# Supabase
SUPABASE_URL=https://yzhqgoofrxixndfcfucz.supabase.co
SUPABASE_KEY=your_service_role_key
DATABASE_URL=postgresql://...

# CommunicationsAPI
COMM_API_URL=https://api.communications.com
COMM_CLIENT_ID=your_client_id
COMM_EMAIL=your_email
COMM_PASSWORD=your_password

# App
ENV=development
DEBUG=true
HOST=0.0.0.0
PORT=8000
```

## 🔐 Segurança

- JWT tokens para autenticação (via Supabase Auth)
- RLS (Row Level Security) no Supabase
- Rate limiting em endpoints críticos
- Validação de dados com Pydantic

## 📊 Monitoramento

- Logs estruturados com structlog
- Health check endpoint
- Métricas de performance (em desenvolvimento)

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/NovaFuncionalidade`)
3. Commit suas mudanças (`git commit -m 'Add: nova funcionalidade'`)
4. Push para a branch (`git push origin feature/NovaFuncionalidade`)
5. Abra um Pull Request

## 📄 Licença

Este projeto é proprietário.

## 📞 Suporte

Para dúvidas e suporte, entre em contato com a equipe de desenvolvimento.

---

**Status:** 🚧 Em desenvolvimento - Fase 1 (Setup e Configuração) concluída
