# API Documentation

## Acessando a Documentação

O backend do Monitoring Options possui documentação interativa disponível em múltiplos formatos:

### 🎨 Scalar API Reference (Recomendado)

Interface moderna e interativa com tema dark mode.

**URL**: `http://localhost:8000/scalar`

**Recursos**:
- Interface moderna e responsiva
- Dark mode habilitado
- Busca rápida (atalho: `k`)
- Try-it-out integrado
- Autenticação JWT integrada
- Visualização de schemas
- Exemplos de código em múltiplas linguagens

### 📄 OpenAPI Specification

Especificação OpenAPI 3.0 em formato JSON.

**URL**: `http://localhost:8000/api/docs/openapi.json`

Use esta URL para importar a especificação em ferramentas como:
- Postman
- Insomnia
- Bruno
- Outras ferramentas compatíveis com OpenAPI

### 🏠 API Root

Informações gerais da API e links para documentação.

**URL**: `http://localhost:8000/`

**Response**:
```json
{
  "name": "Monitoring Options API",
  "version": "1.0.0",
  "description": "API para monitoramento de operações com opções",
  "docs_url": "/docs",
  "scalar_docs": "/scalar",
  "openapi_spec": "/api/docs/openapi.json",
  "health_check": "/health"
}
```

## Autenticação na Documentação

Para testar endpoints autenticados no Scalar:

1. Acesse `http://localhost:8000/scalar`
2. Faça login via endpoint `/auth/login` para obter o token
3. Clique no botão "Authorize" (cadeado) no topo
4. Cole o token JWT no formato: `Bearer <seu-token-aqui>`
5. Agora você pode testar todos os endpoints protegidos

## Configuração

A documentação pode ser habilitada/desabilitada via variável de ambiente:

```bash
# .env
ENABLE_DOCS=true  # ou false para desabilitar
```

## Tags Organizacionais

Os endpoints estão organizados nas seguintes tags:

- **Authentication** - Registro, login, tokens
- **Accounts** - Gerenciamento de contas
- **Assets** - Gerenciamento de ativos
- **Options** - Posições de opções
- **Rules** - Regras de rolagem
- **Alerts** - Sistema de alertas
- **Notifications** - Envio de notificações
- **Workers** - Gerenciamento de workers
- **Rolls** - Calculadora de rolagem
- **Market Data** - Dados de mercado

## Personalização do Scalar

O tema e configurações do Scalar podem ser ajustados em `app/main.py`:

```javascript
data-configuration='{
    "theme": "purple",        // purple, blue, green, etc
    "layout": "modern",       // modern, classic
    "showSidebar": true,      // true, false
    "darkMode": true,         // true, false, auto
    "searchHotKey": "k"       // tecla de atalho para busca
}'
```

## Schemas Disponíveis

Todos os modelos Pydantic são automaticamente convertidos para schemas OpenAPI:

- `UserRegister` - Registro de usuário
- `UserLogin` - Login de usuário
- `TokenResponse` - Resposta de autenticação
- `AccountCreate` - Criação de conta
- `OptionPositionCreate` - Criação de posição
- `RuleCreate` - Criação de regra
- E muitos outros...

## Troubleshooting

### Documentação não aparece

1. Verifique se `ENABLE_DOCS=true` no `.env`
2. Reinicie o servidor
3. Limpe o cache do navegador

### Erros de CORS

Se estiver acessando de um domínio diferente, adicione-o ao `CORS_ORIGINS` no `.env`:

```bash
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://seu-dominio.com
```

### Token JWT inválido

1. Faça login novamente para obter um token válido
2. Verifique se o token não expirou (válido por 1 hora)
3. Certifique-se de usar o formato `Bearer <token>`

## Contribuindo

Para adicionar documentação a novos endpoints:

```python
from sanic_ext import openapi

@blueprint.get("/endpoint")
@openapi.tag("Categoria")
@openapi.summary("Título curto")
@openapi.description("Descrição detalhada")
@openapi.parameter("param", str, "path", description="Descrição do parâmetro")
@openapi.secured("BearerAuth")  # Se requer autenticação
@openapi.response(200, description="Sucesso")
@openapi.response(401, description="Não autenticado")
async def endpoint(request):
    pass
```

## Links Úteis

- [Scalar Documentation](https://github.com/scalar/scalar)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Sanic OpenAPI](https://sanic.dev/en/plugins/sanic-ext/openapi/basics.html)
- [API Endpoints List](./API_ENDPOINTS.md)
