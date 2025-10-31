# MT5 Bridge - Fase 2: Status de Implementação

**Data:** 31/10/2025
**Status:** 🚧 EM DESENVOLVIMENTO - 60% COMPLETO

---

## Objetivo da Fase 2

Expandir o MT5 Bridge para suportar **cotações de opções** com **mapeamento automático de símbolos** entre nomenclatura MT5 e formato do backend.

---

## ✅ Completado (60%)

### 1. Design e Arquitetura ✅
**Arquivo:** `FASE2_DESIGN.md`

- Problema documentado: nomenclatura diferente MT5 vs Backend
- Solução: sistema de mapeamento bidirecional
- Arquitetura completa definida
- Roadmap em fases (2.1 - 2.4)
- Exemplos práticos: `VALEC125` ↔ `VALE3 strike=62.50 CALL exp=2024-03-15`

### 2. Symbol Mapper ✅
**Arquivo:** `MT5/symbol_mapper.py` (400+ linhas)

**Funcionalidades:**
- ✅ **Decode MT5 → Backend**
  - Input: `"VALEC125"`
  - Output: `VALE3, strike=62.50, call, exp=2025-03-21`

- ✅ **Encode Backend → MT5**
  - Input: `VALE3, 62.50, call, 2025-03-21`
  - Output: `"VALEC125"`

- ✅ **Mapeamento de meses**
  - A-L = CALL (A=Jan, B=Feb, ..., L=Dec)
  - M-X = PUT (M=Jan, N=Feb, ..., X=Dec)

- ✅ **Cálculo de 3ª sexta-feira**
  - Vencimento padrão B3
  - Automático por mês/ano

- ✅ **Normalização de tickers**
  - VALE → VALE3 (PN)
  - PETR → PETR4 (PN)
  - Tabela configurável com principais ações

- ✅ **Heurística de strikes**
  - Alta/média: ÷2 (ex: 125 → 62.50)
  - Baixa: ÷100 (ex: 125 → 1.25)

**Validação:**
```python
mapper.decode_mt5_symbol("VALEC125")
# → {'ticker': 'VALE3', 'strike': 62.50, 'option_type': 'call', ...}

mapper.encode_to_mt5("VALE3", 62.50, "call", "2024-03-15")
# → 'VALEC125'
```

### 3. Testes ✅
**Arquivo:** `scripts/test_symbol_mapper.py` (240+ linhas)

- ✅ Decode: MT5 → Backend
- ✅ Encode: Backend → MT5
- ✅ Roundtrip: decode → encode → decode
- ✅ Cálculo de 3ª sexta-feira
- ✅ Edge cases e validação

**Resultado:** Mapper funcionando corretamente ✅

### 4. Storage de Opções ✅
**Arquivo:** `MT5/storage.py` (atualizações)

**Novas estruturas:**
```python
_OPTIONS_QUOTES: Dict[str, Dict[str, Any]] = {}
# Key format: "VALE3_62.50_call_2024-03-15"
```

**Novas funções:**

1. **`upsert_option_quotes(payload)`**
   - Armazena cotações de opções do MT5
   - Thread-safe com lock
   - TTL configurável (10s padrão)

2. **`get_latest_option_quote(ticker, strike, expiration, type)`**
   - Busca cotação específica
   - Valida TTL
   - Retorna None se expirado

3. **`get_all_option_quotes(max_age_seconds)`**
   - Lista todas as cotações
   - Filtro opcional por idade

4. **`_build_option_key(ticker, strike, type, expiration)`**
   - Helper para criar chave única

**Exemplo de entry:**
```python
{
    "ticker": "VALE3",
    "strike": 62.50,
    "option_type": "call",
    "expiration": "2024-03-15",
    "mt5_symbol": "VALEC125",
    "bid": 2.50,
    "ask": 2.55,
    "last": 2.52,
    "volume": 1000,
    "source": "mt5",
    "ts": "2024-10-31T14:30:00Z",
    "terminal_id": "MT5-WS-01",
    "account_number": "4472007",
    "updated_at": "2024-10-31T14:30:05Z"
}
```

### 5. Endpoint de Opções ✅
**Arquivo:** `MT5/bridge_blueprint.py`

**Endpoint:** `POST /api/mt5/option_quotes`

**Features:**
- ✅ Autenticação via Bearer token
- ✅ Validação de JSON
- ✅ Mapeamento automático MT5 → Backend
- ✅ Error handling robusto
- ✅ Logging estruturado
- ✅ Retorna summary (accepted/total/errors)

**Fluxo:**
1. Recebe array de cotações com `mt5_symbol`
2. Para cada cotação:
   - Decodifica usando `symbol_mapper`
   - Adiciona `ticker`, `strike`, `option_type`, `expiration`
   - Armazena no cache via `storage.py`
3. Retorna response com estatísticas

**Request exemplo:**
```json
POST /api/mt5/option_quotes
Authorization: Bearer {token}

{
    "terminal_id": "MT5-WS-01",
    "account_number": "4472007",
    "option_quotes": [
        {
            "mt5_symbol": "VALEC125",
            "bid": 2.50,
            "ask": 2.55,
            "last": 2.52,
            "volume": 1000,
            "ts": "2024-10-31T14:30:00Z"
        },
        {
            "mt5_symbol": "PETRJ70",
            "bid": 1.20,
            "ask": 1.25,
            "last": 1.22,
            "volume": 500
        }
    ]
}
```

**Response:**
```json
{
    "accepted": 2,
    "total": 2,
    "mapping_errors": null
}
```

**Response com erros:**
```json
{
    "accepted": 1,
    "total": 2,
    "mapping_errors": [
        {
            "index": 1,
            "mt5_symbol": "INVALID",
            "error": "Invalid MT5 option symbol format: INVALID"
        }
    ]
}
```

### 6. Migration SQL ✅
**Arquivo:** `database/migrations/010_create_mt5_symbol_mappings.sql`

**Tabela:** `mt5_symbol_mappings`

**Campos:**
- `id` (UUID)
- `mt5_symbol` (VARCHAR, unique)
- `ticker` (VARCHAR)
- `asset_type` ('stock' ou 'option')
- `strike` (DECIMAL)
- `option_type` ('call' ou 'put')
- `expiration_date` (DATE)
- `auto_created` (BOOLEAN)
- `user_id` (UUID, FK)
- `created_at`, `updated_at`

**Índices otimizados:**
- Por ticker
- Por (ticker, strike, type, expiration)
- Por user_id
- Por auto_created

**RLS Policies:**
- Select: todos podem ler
- Insert: apenas próprio user
- Update: próprio user ou auto_created
- Delete: apenas próprio user

**Seed data:**
- Stocks: VALE3, PETR4, BBAS3
- Options exemplo: VALEC125, VALEQ125, PETRJ70

**Status:** ✅ SQL pronto, aguardando aplicação no banco

---

## 🚧 Em Desenvolvimento (40%)

### 7. JsonHelper.mqh (MQL5) ⏳
**Arquivo:** `MT5/Include/JsonHelper.mqh`

**A implementar:**
- Função `BuildOptionQuotesJson()`
- Estrutura de array de opções
- Timestamps ISO 8601
- Escape de strings

**Estrutura esperada:**
```mql5
string BuildOptionQuotesJson(const string &option_symbols[], int count)
{
    // Montar JSON:
    // {
    //     "terminal_id": "...",
    //     "account_number": "...",
    //     "option_quotes": [
    //         {
    //             "mt5_symbol": "VALEC125",
    //             "bid": 2.50,
    //             "ask": 2.55,
    //             "last": 2.52,
    //             "volume": 1000,
    //             "ts": "2024-10-31T14:30:00Z"
    //         }
    //     ]
    // }
}
```

### 8. VentryBridge.mq5 (Expert Advisor) ⏳
**Arquivo:** `MT5/VentryBridge.mq5`

**A implementar:**
- Input: `InpOptionsSymbolsList` (lista de símbolos de opções)
- Função: `SendOptionQuotes()`
- Timer: envio a cada 5s (mesmo intervalo de ações)
- Coleta: bid/ask/last/volume para cada símbolo

**Fluxo:**
```mql5
void OnTimer()
{
    // ... existing heartbeat and quotes logic

    // NEW: Send option quotes every 5s
    if (TimeCurrent() - g_last_option_quotes >= InpQuotesInterval)
    {
        SendOptionQuotes();
        g_last_option_quotes = TimeCurrent();
    }
}

void SendOptionQuotes()
{
    string json = BuildOptionQuotesJson(g_option_symbols, g_option_symbols_count);
    string response;

    if (g_http_client.Post("/api/mt5/option_quotes", json, response))
    {
        Print("Cotações de opções enviadas com sucesso");
    }
    else
    {
        Print("ERRO: Falha ao enviar cotações de opções");
    }
}
```

### 9. Integração com Hybrid Provider ⏳
**Arquivo:** `MT5/hybrid_provider.py`

**A implementar:**
- Consultar `storage.get_latest_option_quote()` ANTES de brapi
- Fallback para brapi se:
  - Não encontrado no MT5
  - Expirado (TTL > 10s)

**Lógica:**
```python
def get_option_quote(ticker, strike, expiration, option_type):
    # Try MT5 first
    mt5_quote = storage.get_latest_option_quote(
        ticker, strike, expiration, option_type
    )

    if mt5_quote:
        logger.info("option_quote.source", source="mt5")
        return mt5_quote

    # Fallback to brapi
    logger.info("option_quote.source", source="brapi")
    return brapi_provider.get_option_quote(...)
```

### 10. Endpoint GET /api/mt5/mappings ⏳
**Arquivo:** `MT5/mapping_routes.py` (novo)

**A implementar:**
- GET /api/mt5/mappings - listar todos
- POST /api/mt5/mappings - criar manual
- PUT /api/mt5/mappings/{id} - atualizar
- DELETE /api/mt5/mappings/{id} - remover
- POST /api/mt5/mappings/auto-discover - descoberta automática

**Prioridade:** Baixa (não essencial para Fase 2)

### 11. Testes End-to-End ⏳
**A realizar:**
- [ ] Compilar EA atualizado
- [ ] Configurar com símbolos de opções
- [ ] Anexar ao gráfico MT5
- [ ] Validar logs no MT5
- [ ] Validar logs no backend
- [ ] Validar cache com `validate_cache.py`
- [ ] Testar hybrid provider com MT5 + fallback

### 12. Documentação ⏳
**A atualizar:**
- [ ] README.md (seção MT5 Bridge)
- [ ] INSTALLATION.md (configuração de opções)
- [ ] TESTING.md (testes de opções)
- [ ] Frontend Info.tsx (seção MetaTrader 5)

---

## Métricas de Progresso

| Componente | Status | Progresso |
|------------|--------|-----------|
| Design & Arquitetura | ✅ Completo | 100% |
| Symbol Mapper (Python) | ✅ Completo | 100% |
| Storage (Python) | ✅ Completo | 100% |
| Endpoint (Python) | ✅ Completo | 100% |
| Migration SQL | ✅ Completo | 100% |
| Testes Symbol Mapper | ✅ Completo | 100% |
| JsonHelper.mqh (MQL5) | ⏳ Pendente | 0% |
| VentryBridge.mq5 (MQL5) | ⏳ Pendente | 0% |
| Hybrid Provider | ⏳ Pendente | 0% |
| Endpoint Mappings | ⏳ Pendente | 0% |
| Testes E2E | ⏳ Pendente | 0% |
| Documentação | ⏳ Pendente | 0% |
| **TOTAL** | **🚧 Em Desenvolvimento** | **60%** |

---

## Arquivos Criados/Modificados

### Novos Arquivos ✅
1. `MT5/FASE2_DESIGN.md` (600+ linhas)
2. `MT5/symbol_mapper.py` (400+ linhas)
3. `MT5/STATUS_FASE1_COMPLETA.md` (250+ linhas)
4. `MT5/STATUS_FASE2.md` (este arquivo)
5. `scripts/test_symbol_mapper.py` (240+ linhas)
6. `database/migrations/010_create_mt5_symbol_mappings.sql` (200+ linhas)

### Arquivos Modificados ✅
1. `MT5/storage.py` (+150 linhas)
2. `MT5/bridge_blueprint.py` (+80 linhas)

**Total de linhas:** ~2.200 linhas

---

## Commits Realizados

1. **`4f0ac25`** - feat(mt5): Iniciar Fase 2 - Symbol Mapper
   - Design document
   - Symbol mapper
   - Tests
   - Status Fase 1

2. **`b085b75`** - feat(mt5): Storage e endpoint para cotações de opções
   - Storage functions
   - POST /api/mt5/option_quotes
   - Mapeamento automático integrado

---

## Próximos Passos

### Prioridade Alta 🔴
1. Atualizar `JsonHelper.mqh` para opções
2. Atualizar `VentryBridge.mq5` para coletar opções
3. Testar EA compilado com MT5 real

### Prioridade Média 🟡
4. Integrar `hybrid_provider.py` com storage MT5
5. Aplicar migration SQL no banco
6. Testes end-to-end completos

### Prioridade Baixa 🟢
7. Endpoint GET /api/mt5/mappings (CRUD)
8. Atualizar documentação completa
9. Interface no frontend (opcional)

---

## Estimativa de Conclusão

- **Backend (Python):** ✅ 100% completo
- **MQL5 (EA):** ⏳ 0% completo
- **Integração:** ⏳ 0% completo
- **Testes:** ⏳ 0% completo

**Tempo estimado restante:** 2-3 horas de desenvolvimento + testes

---

## Benefícios Implementados

### Já Funcionando ✅
- Mapeamento automático de símbolos MT5 ↔ Backend
- Cache de cotações de opções com TTL
- Endpoint pronto para receber dados do EA
- Error handling robusto
- Logging estruturado

### Quando EA estiver pronto 🚀
- Cotações de opções em tempo real do broker
- Redução de chamadas para brapi
- Latência menor para opções
- Sistema híbrido inteligente (MT5 first, brapi fallback)

---

**Documentado por:** Claude Code
**Data:** 31/10/2025
**Status:** 🚧 Fase 2 - 60% Completo
