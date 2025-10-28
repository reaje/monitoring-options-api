# MT5 Bridge - Integração MetaTrader 5

## 📁 Estrutura do Diretório

```
MT5/
├── VentryBridge.mq5          # Expert Advisor principal
├── Include/
│   ├── HttpClient.mqh        # Biblioteca HTTP para requisições
│   └── JsonHelper.mqh        # Biblioteca para construção de JSON
├── bridge_blueprint.py       # Blueprint Sanic com rotas da API
├── storage.py                # Cache em memória para quotes/heartbeats
├── INSTALLATION.md           # Guia completo de instalação
├── EXAMPLE.set              # Arquivo de configuração exemplo
└── README.md                # Este arquivo

```

## ✅ Status da Implementação

**Fase 1: COMPLETA**

### Backend (Python/Sanic)
- ✅ Blueprint com 4 endpoints REST
- ✅ Autenticação via Bearer token
- ✅ Whitelist de IPs (opcional)
- ✅ Cache thread-safe em memória
- ✅ Integração com Market Data Providers
- ✅ Logs estruturados

### Cliente (MQL5)
- ✅ Expert Advisor completo
- ✅ Biblioteca HTTP com suporte a WebRequest
- ✅ Biblioteca JSON para serialização
- ✅ Timer automático para envio de dados
- ✅ Configuração via inputs no MT5
- ✅ Tratamento de erros robusto

## 🚀 Quick Start

### 1. Backend

Edite `backend/.env`:

```bash
MT5_BRIDGE_ENABLED=true
MT5_BRIDGE_TOKEN=seu-token-secreto-forte
MARKET_DATA_PROVIDER=hybrid  # Recomendado
```

Inicie o servidor:

```bash
cd backend
python -m app.main
```

### 2. Expert Advisor

Consulte o guia completo em **[INSTALLATION.md](INSTALLATION.md)**

Resumo:
1. Copiar arquivos para `<DataFolder>/MQL5/Experts/Ventry/`
2. Compilar `VentryBridge.mq5` no MetaEditor (F7)
3. Adicionar URL do backend nas URLs permitidas do MT5
4. Anexar EA ao gráfico e configurar parâmetros
5. Verificar logs na aba Expert

### 3. Testar

```bash
# Script Python de simulação
cd backend
python scripts/test_mt5_bridge.py
```

## 🔌 API Endpoints

Todas as rotas em `/api/mt5/*` requerem autenticação via `Authorization: Bearer <token>`

### POST /api/mt5/heartbeat

Recebe heartbeat do terminal MT5.

**Request:**
```json
{
  "terminal_id": "MT5-WS-01",
  "account_number": "123456",
  "broker": "XP",
  "build": 3770,
  "timestamp": "2025-01-22T10:30:00Z"
}
```

**Response:**
```json
{
  "status": "ok"
}
```

### POST /api/mt5/quotes

Recebe snapshot de cotações.

**Request:**
```json
{
  "terminal_id": "MT5-WS-01",
  "account_number": "123456",
  "quotes": [
    {
      "symbol": "PETR4",
      "bid": 36.50,
      "ask": 36.52,
      "last": 36.51,
      "volume": 15234000,
      "ts": "2025-01-22T10:30:05Z"
    }
  ]
}
```

**Response:**
```json
{
  "accepted": 1
}
```

### GET /api/mt5/commands

Retorna comandos pendentes (Fase 3).

**Query Params:**
- `terminal_id` - ID do terminal
- `account_number` - Número da conta

**Response (Fase 1):**
```json
{
  "commands": []
}
```

### POST /api/mt5/execution_report

Recebe relatório de execução (Fase 3).

**Request:**
```json
{
  "command_id": "cmd-001",
  "status": "FILLED",
  "order_id": "MT5-987654",
  "filled_qty": 700,
  "avg_price": 0.35,
  "ts": "2025-01-22T10:30:15Z",
  "message": "Roll executado com sucesso"
}
```

**Response:**
```json
{
  "status": "ok"
}
```

## ⚙️ Configuração

### Variáveis de Ambiente (Backend)

```bash
# Habilitar/desabilitar bridge
MT5_BRIDGE_ENABLED=true

# Token de autenticação (obrigatório se enabled)
MT5_BRIDGE_TOKEN=abc123xyz

# Whitelist de IPs (opcional, separado por vírgula)
MT5_BRIDGE_ALLOWED_IPS=127.0.0.1,192.168.1.100

# TTL para expiração de cotações (segundos)
MT5_BRIDGE_QUOTE_TTL_SECONDS=10

# TTL para expiração de comandos (segundos)
MT5_BRIDGE_COMMAND_TTL_SECONDS=60
```

### Parâmetros do EA (MT5)

| Parâmetro | Descrição | Padrão |
|-----------|-----------|--------|
| `InpBackendUrl` | URL do backend | `http://localhost:8000` |
| `InpAuthToken` | Bearer token | `` (vazio) |
| `InpTerminalId` | ID único do terminal | `MT5-WS-01` |
| `InpBroker` | Nome do broker | `XP` |
| `InpSymbolsList` | Símbolos (separados por vírgula) | `PETR4,VALE3,BBAS3` |
| `InpHeartbeatInterval` | Intervalo de heartbeat (s) | `60` |
| `InpQuotesInterval` | Intervalo de quotes (s) | `5` |
| `InpCommandsPollInterval` | Intervalo de polling (s) | `10` |
| `InpEnableLogging` | Logs detalhados | `true` |
| `InpHttpTimeout` | Timeout HTTP (ms) | `5000` |

## 🔧 Integração com Market Data Providers

O bridge MT5 se integra perfeitamente com o sistema de providers:

```python
# backend/app/services/market_data/__init__.py

MARKET_DATA_PROVIDER = "hybrid"  # Recomendado

# Opções disponíveis:
# - "mock"   : Dados fake para testes
# - "brapi"  : API brasileira brapi.dev
# - "mt5"    : Apenas MT5 (erro se indisponível)
# - "hybrid" : MT5 primeiro, fallback para brapi ✅
```

### Fluxo do Provider Híbrido

```
Request → Hybrid Provider
    ↓
    ├─ MT5 disponível (< 10s)?
    │  └─ ✅ Retorna dados MT5
    │
    └─ MT5 indisponível?
       └─ ⚠️ Fallback para brapi
```

## 📊 Monitoramento

### Logs do Backend

```json
{
  "event": "mt5.heartbeat",
  "terminal_id": "MT5-WS-01",
  "account_number": "123456",
  "broker": "XP",
  "build": 3770
}

{
  "event": "mt5.quotes",
  "count": 3
}
```

### Logs do EA (MT5)

```
Enviando heartbeat...
Heartbeat enviado com sucesso. Resposta: {"status":"ok"}
Enviando 3 cotações...
Cotações enviadas com sucesso. Resposta: {"accepted":3}
```

## 🗺️ Roadmap

### ✅ Fase 1: Subjacente (Completa)
- Heartbeat do terminal
- Cotações de ações (bid/ask/last/volume)
- Provider híbrido com fallback
- Cache em memória thread-safe

### ⏳ Fase 2: Opções (Planejada)
- Cotações de opções do MT5
- Mapeamento de símbolos B3 (PETRC123 → PETR4C123)
- Normalização para modelo interno
- Fallback inteligente

### ⏳ Fase 3: Execução (Planejada)
- Fila de comandos persistente (DB/Redis)
- Execução de ordens de roll
- Relatórios de execução detalhados
- Idempotência e auditoria
- UI "Enviar para MT5"

## 📚 Documentação

- **[INSTALLATION.md](INSTALLATION.md)** - Guia completo de instalação e troubleshooting
- **[EXAMPLE.set](EXAMPLE.set)** - Arquivo de configuração exemplo para MT5
- **[../docs/planning/INTEGRACAO_MT5_MQL5_BRIDGE.md](../docs/planning/INTEGRACAO_MT5_MQL5_BRIDGE.md)** - Arquitetura e planejamento completo

## 🐛 Troubleshooting

### EA não envia dados

1. ✅ AutoTrading está VERDE?
2. ✅ URL está nas URLs permitidas? (Ferramentas → Opções → Expert Advisors)
3. ✅ Token está correto no EA e no backend?
4. ✅ Backend está rodando?
5. ✅ Logs na aba Expert mostram erros?

### HTTP Error 401 (Unauthorized)

- Token inválido ou diferente entre EA e backend
- Solução: Verifique `InpAuthToken` e `MT5_BRIDGE_TOKEN`

### HTTP Error 403 (Forbidden)

- Bridge desabilitado ou IP não autorizado
- Solução: `MT5_BRIDGE_ENABLED=true` e verificar `MT5_BRIDGE_ALLOWED_IPS`

### WebRequest Error 4060

- URL não está na lista de permitidas
- Solução: Adicionar URL em Ferramentas → Opções → Expert Advisors

Consulte **[INSTALLATION.md](INSTALLATION.md#-troubleshooting)** para mais detalhes.

## 🤝 Contribuindo

Para contribuir com o bridge MT5:

1. Teste localmente com o script de simulação
2. Documente mudanças no código MQL5
3. Atualize esta documentação se necessário
4. Use commits convencionais:
   - `feat(mt5): Add new feature`
   - `fix(mt5): Fix EA bug`
   - `docs(mt5): Update installation guide`

## 📄 Licença

Este código é proprietário da Ventry.

