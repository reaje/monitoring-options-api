# Guia de Testes - Backend

## 🎯 Visão Geral

O backend possui testes unitários e de integração para garantir a qualidade do código.

## 📋 Pré-requisitos

1. **Banco de dados configurado:**
   ```bash
   # Aplicar migrations
   python scripts/run_migrations.py
   ```

2. **Dependências instaladas:**
   ```bash
   pip install -r requirements-dev.txt
   ```

## 🚀 Executando Testes

### Todos os Testes

```bash
# Forma simples
pytest

# Com script helper
python scripts/run_tests.py

# Com verbose
pytest -v

# Com coverage
pytest --cov=app --cov-report=html
```

### Testes Específicos

```bash
# Apenas unitários
pytest tests/unit/

# Apenas integração
pytest tests/integration/

# Arquivo específico
pytest tests/integration/test_auth_api.py

# Classe específica
pytest tests/integration/test_auth_api.py::TestAuthLogin

# Teste específico
pytest tests/integration/test_auth_api.py::TestAuthLogin::test_login_success

# Por marcador
pytest -m unit
pytest -m integration
```

## 📊 Estrutura de Testes

```
tests/
├── conftest.py              # Fixtures compartilhadas
│
├── unit/                    # Testes Unitários (11 testes)
│   └── test_security.py     # Segurança (JWT, bcrypt)
│       ├── TestPasswordHashing (4 testes)
│       └── TestJWTTokens (7 testes)
│
└── integration/             # Testes de Integração (62 testes)
    ├── test_auth_api.py     # Autenticação (26 testes)
    │   ├── TestAuthRegister (5)
    │   ├── TestAuthLogin (4)
    │   ├── TestAuthMe (3)
    │   ├── TestAuthLogout (2)
    │   ├── TestAuthRefresh (4)
    │   └── TestAuthChangePassword (4)
    │
    ├── test_accounts_api.py # Contas (17 testes)
    │   ├── TestAccountsList (3)
    │   ├── TestAccountsCreate (3)
    │   ├── TestAccountsGet (3)
    │   ├── TestAccountsUpdate (4)
    │   └── TestAccountsDelete (3)
    │
    └── test_assets_api.py   # Ativos (19 testes)
        ├── TestAssetsList (4)
        ├── TestAssetsCreate (4)
        ├── TestAssetsGet (3)
        ├── TestAssetsUpdate (5)
        └── TestAssetsDelete (3)
```

## 🔧 Fixtures Disponíveis

### Usuários e Autenticação

```python
async def test_example(test_user, auth_token, auth_headers):
    # test_user: dict com dados do usuário
    # auth_token: string JWT token
    # auth_headers: dict {"Authorization": "Bearer ..."}
    pass
```

### Contas

```python
async def test_example(test_account, multiple_accounts):
    # test_account: dict com uma conta
    # multiple_accounts: list com 3 contas
    pass
```

### Ativos

```python
async def test_example(test_asset, multiple_assets):
    # test_asset: dict com um ativo (PETR4)
    # multiple_assets: list com 3 ativos (PETR4, VALE3, ITUB4)
    pass
```

### Cliente HTTP

```python
async def test_example(test_client):
    # test_client: Sanic test client
    _, response = await test_client.get("/api/accounts")
    assert response.status == 200
```

## 📈 Coverage

### Gerar Relatório

```bash
# Gerar coverage HTML
pytest --cov=app --cov-report=html

# Abrir relatório
# Windows
start htmlcov/index.html

# Linux/Mac
open htmlcov/index.html
```

### Interpretar Coverage

- **Verde:** Linhas cobertas por testes
- **Vermelho:** Linhas não cobertas
- **Amarelo:** Linhas parcialmente cobertas

**Meta:** > 80% coverage

## ✅ Checklist de Testes

Ao adicionar novos endpoints:

- [ ] Criar fixture se necessário
- [ ] Testar caso de sucesso
- [ ] Testar validações (422)
- [ ] Testar autenticação (401)
- [ ] Testar autorização (403)
- [ ] Testar not found (404)
- [ ] Testar edge cases

## 🐛 Debugging Testes

### Rodar com Debug

```bash
# Com breakpoint
pytest -s tests/integration/test_auth_api.py

# Com logs
pytest --log-cli-level=DEBUG

# Com traceback completo
pytest --tb=long
```

### Usar pdb

```python
def test_something():
    import pdb; pdb.set_trace()
    # seu teste aqui
```

### Rodar Apenas Falhas

```bash
# Rodar apenas testes que falharam
pytest --lf

# Rodar falhas primeiro
pytest --ff
```

## 📝 Escrevendo Novos Testes

### Template de Teste de Integração

```python
import pytest

@pytest.mark.asyncio
class TestNewEndpoint:
    """Test new endpoint."""

    async def test_success_case(self, test_client, auth_headers):
        """Test successful operation."""
        _, response = await test_client.post(
            "/api/new-endpoint",
            headers=auth_headers,
            json={"field": "value"},
        )

        assert response.status == 201
        data = response.json
        assert "result" in data

    async def test_validation_error(self, test_client, auth_headers):
        """Test validation error."""
        _, response = await test_client.post(
            "/api/new-endpoint",
            headers=auth_headers,
            json={},  # Missing required field
        )

        assert response.status == 422

    async def test_unauthenticated(self, test_client):
        """Test without authentication."""
        _, response = await test_client.post(
            "/api/new-endpoint",
            json={"field": "value"},
        )

        assert response.status == 401
```

### Template de Teste Unitário

```python
import pytest
from app.services.my_service import MyService

class TestMyService:
    """Test MyService class."""

    def test_method_success(self):
        """Test method with valid input."""
        result = MyService.my_method("input")
        assert result == "expected"

    def test_method_error(self):
        """Test method with invalid input."""
        with pytest.raises(ValueError):
            MyService.my_method(None)
```

## 🚨 CI/CD

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11

      - name: Install dependencies
        run: |
          pip install -r backend/requirements-dev.txt

      - name: Run tests
        run: |
          cd backend
          pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## 📚 Recursos

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Sanic Testing](https://sanic.dev/en/guide/testing/getting-started.html)

## ❓ FAQ

**Q: Os testes estão falhando com "database not found"**
A: Execute as migrations primeiro: `python scripts/run_migrations.py`

**Q: Como limpar o banco de dados de teste?**
A: As fixtures já fazem cleanup automático. Se necessário, delete manualmente as tabelas.

**Q: Como mockar o CommunicationsAPI?**
A: Use `pytest-mock` ou `unittest.mock`:
```python
async def test_with_mock(mocker):
    mock_send = mocker.patch('app.services.communications.send_whatsapp')
    mock_send.return_value = {"status": "sent"}
```

**Q: Testes estão lentos**
A: Use markers para rodar apenas testes rápidos:
```bash
pytest -m "not slow"
```

---

**Última atualização:** 2025-01-22
