# MT5 Bridge - Fase 2: Cotações de Opções + Mapeamento de Símbolos

**Data:** 31/10/2025
**Status:** 🚧 EM DESENVOLVIMENTO

---

## Objetivo

Expandir o MT5 Bridge (Fase 1) para:
1. **Receber cotações de opções** do MetaTrader 5
2. **Mapear símbolos MT5 ↔ Backend** automaticamente
3. **Armazenar e disponibilizar** cotações de opções para o sistema

---

## Problema a Resolver

### Nomenclatura Diferente

O MT5 usa nomenclaturas específicas para opções que diferem do padrão do backend:

**Exemplos reais:**

| MT5 Symbol | Backend Esperado |
|------------|------------------|
| `VALEC125` | `VALE3` strike 62.50 CALL exp 2024-11 |
| `VALEQ125` | `VALE3` strike 62.50 PUT exp 2024-11 |
| `PETRJ70`  | `PETR4` strike 35.00 CALL exp 2024-10 |

**Padrão MT5:**
```
[TICKER][TIPO][STRIKE_CODIFICADO]
```

Onde:
- `TICKER`: 4-5 letras (VALE, PETR, BBAS, etc)
- `TIPO`: 1 letra indicando mês + CALL/PUT
  - `A-L` = CALL (A=Jan, B=Fev, ..., L=Dez)
  - `M-X` = PUT (M=Jan, N=Fev, ..., X=Dez)
- `STRIKE_CODIFICADO`: Strike price * 100, sem ponto decimal
  - Ex: `125` = 62.50, `70` = 35.00

### Necessidade de Mapeamento Bidirecional

1. **MT5 → Backend**: Quando EA envia `VALEC125`, backend precisa saber:
   - Ticker subjacente: `VALE3`
   - Strike: `62.50`
   - Tipo: `CALL`
   - Expiração: `2024-11-15` (3ª sexta-feira)

2. **Backend → MT5**: Quando backend quer cotação de opção específica:
   - Precisa converter `VALE3 strike=62.50 CALL exp=2024-11-15` → `VALEC125`

---

## Arquitetura da Solução

### 1. Banco de Dados: Tabela de Mapeamento

```sql
CREATE TABLE mt5_symbol_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Símbolo MT5
    mt5_symbol VARCHAR(50) NOT NULL UNIQUE,

    -- Informações do backend
    ticker VARCHAR(20) NOT NULL,           -- VALE3, PETR4, etc
    asset_type VARCHAR(20) NOT NULL,       -- 'stock' ou 'option'

    -- Para opções
    strike DECIMAL(10,2),                  -- Strike price (ex: 62.50)
    option_type VARCHAR(10),               -- 'call' ou 'put'
    expiration_date DATE,                  -- Data de vencimento

    -- Metadados
    auto_created BOOLEAN DEFAULT FALSE,     -- Se foi criado automaticamente
    user_id UUID REFERENCES auth.users(id), -- Quem criou (se manual)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Índices
    CONSTRAINT check_option_fields CHECK (
        (asset_type = 'option' AND strike IS NOT NULL AND option_type IS NOT NULL AND expiration_date IS NOT NULL)
        OR (asset_type = 'stock')
    )
);

-- Índices para busca rápida
CREATE INDEX idx_mt5_mappings_ticker ON mt5_symbol_mappings(ticker);
CREATE INDEX idx_mt5_mappings_option_lookup ON mt5_symbol_mappings(ticker, strike, option_type, expiration_date)
    WHERE asset_type = 'option';
```

### 2. Backend: Lógica de Mapeamento

**Arquivo novo:** `backend/MT5/symbol_mapper.py`

```python
class MT5SymbolMapper:
    """
    Mapeia símbolos MT5 ↔ Backend.

    Funcionalidades:
    - Decode: MT5 symbol → (ticker, strike, type, exp)
    - Encode: (ticker, strike, type, exp) → MT5 symbol
    - Cache: Mantém mapeamentos em memória
    - Auto-create: Cria mapeamentos automaticamente quando possível
    """

    # Tabela de meses (A-L = CALL, M-X = PUT)
    MONTH_CODES_CALL = {
        'A': 1,  'B': 2,  'C': 3,  'D': 4,
        'E': 5,  'F': 6,  'G': 7,  'H': 8,
        'I': 9,  'J': 10, 'K': 11, 'L': 12
    }
    MONTH_CODES_PUT = {
        'M': 1,  'N': 2,  'O': 3,  'P': 4,
        'Q': 5,  'R': 6,  'S': 7,  'T': 8,
        'U': 9,  'V': 10, 'W': 11, 'X': 12
    }

    def decode_mt5_symbol(self, mt5_symbol: str) -> dict:
        """
        Decodifica símbolo MT5 para componentes.

        Exemplo:
            decode_mt5_symbol("VALEC125")
            → {
                "ticker": "VALE3",
                "strike": 62.50,
                "option_type": "call",
                "month": 3,
                "year": 2024,  # ou inferido
                "expiration": "2024-03-15"
              }
        """
        pass

    def encode_to_mt5(self, ticker, strike, option_type, expiration) -> str:
        """
        Converte informações do backend para símbolo MT5.

        Exemplo:
            encode_to_mt5("VALE3", 62.50, "call", "2024-03-15")
            → "VALEC125"
        """
        pass

    def get_or_create_mapping(self, mt5_symbol: str) -> dict:
        """
        Busca mapeamento no DB. Se não existir, tenta criar automaticamente.
        """
        pass
```

### 3. Storage: Cotações de Opções

**Atualizar:** `backend/MT5/storage.py`

```python
# Nova estrutura de dados para opções
_OPTIONS_QUOTES: Dict[str, Dict[str, Any]] = {}  # key = f"{ticker}_{strike}_{type}_{exp}"

def upsert_option_quotes(payload: Dict[str, Any]) -> int:
    """
    Armazena cotações de opções recebidas do MT5.

    Payload esperado:
    {
        "terminal_id": "MT5-WS-01",
        "account_number": "4472007",
        "option_quotes": [
            {
                "mt5_symbol": "VALEC125",
                "ticker": "VALE3",        # Já mapeado
                "strike": 62.50,
                "option_type": "call",
                "expiration": "2024-03-15",
                "bid": 2.50,
                "ask": 2.55,
                "last": 2.52,
                "volume": 1000,
                "ts": "2024-10-31T14:30:00Z"
            }
        ]
    }
    """
    pass

def get_latest_option_quote(
    ticker: str,
    strike: float,
    expiration: str,
    option_type: str,
    ttl_seconds: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Retorna cotação mais recente da opção (se dentro do TTL).
    """
    pass
```

### 4. Expert Advisor: Coleta de Opções

**Atualizar:** `backend/MT5/VentryBridge.mq5`

**Novo input:**
```mql5
input string    InpOptionsSymbolsList = "VALEC125,VALEC130,VALEQ125"; // Lista de símbolos de opções
```

**Nova função:**
```mql5
void SendOptionQuotes()
{
    string json = BuildOptionQuotesJson();
    string response;

    if(g_http_client.Post("/api/mt5/option_quotes", json, response))
    {
        Print("Cotações de opções enviadas com sucesso");
    }
    else
    {
        Print("ERRO: Falha ao enviar cotações de opções");
    }
}
```

**Atualizar:** `backend/MT5/Include/JsonHelper.mqh`

```mql5
string BuildOptionQuotesJson(const string &symbols[], int count)
{
    // Construir JSON com cotações de opções
    // Incluir: symbol, bid, ask, last, volume, timestamp
}
```

### 5. Endpoint: Receber Cotações de Opções

**Atualizar:** `backend/MT5/bridge_blueprint.py`

```python
@mt5_bridge_bp.post("/option_quotes")
@openapi.tag("MT5 Bridge")
@openapi.summary("Recebe cotações de opções do MT5")
async def option_quotes(request: Request):
    deny = _require_enabled_and_auth(request)
    if deny:
        return deny

    try:
        payload: Dict[str, Any] = request.json or {}

        # Para cada símbolo MT5, fazer mapeamento
        mapped_quotes = []
        for quote in payload.get("option_quotes", []):
            mt5_symbol = quote.get("mt5_symbol")

            # Buscar ou criar mapeamento
            mapping = symbol_mapper.get_or_create_mapping(mt5_symbol)

            # Adicionar informações mapeadas
            quote.update({
                "ticker": mapping["ticker"],
                "strike": mapping["strike"],
                "option_type": mapping["option_type"],
                "expiration": mapping["expiration_date"]
            })
            mapped_quotes.append(quote)

        # Armazenar no storage
        accepted = upsert_option_quotes({
            **payload,
            "option_quotes": mapped_quotes
        })

        logger.info("mt5.option_quotes", count=accepted)
        return response.json({"accepted": accepted}, status=202)

    except Exception as e:
        logger.error("mt5.option_quotes.error", error=str(e))
        return response.json({"error": str(e)}, status=500)
```

### 6. Endpoint: Gerenciar Mapeamentos

**Novo:** `backend/MT5/mapping_routes.py`

```python
mapping_bp = Blueprint("mt5_mappings", url_prefix="/api/mt5/mappings")

@mapping_bp.get("/")
async def list_mappings(request: Request):
    """Lista todos os mapeamentos."""
    pass

@mapping_bp.post("/")
async def create_mapping(request: Request):
    """Cria mapeamento manual."""
    pass

@mapping_bp.put("/<mapping_id>")
async def update_mapping(request: Request, mapping_id: str):
    """Atualiza mapeamento existente."""
    pass

@mapping_bp.delete("/<mapping_id>")
async def delete_mapping(request: Request, mapping_id: str):
    """Remove mapeamento."""
    pass

@mapping_bp.post("/auto-discover")
async def auto_discover_mappings(request: Request):
    """
    Descobre automaticamente mapeamentos com base em símbolos MT5 fornecidos.
    """
    pass
```

---

## Fluxo de Dados

### Cenário 1: Primeira Cotação de Opção

```
1. MT5 EA coleta cotação do símbolo "VALEC125"
   ↓
2. EA envia POST /api/mt5/option_quotes
   Body: { "option_quotes": [{"mt5_symbol": "VALEC125", "bid": 2.50, ...}] }
   ↓
3. Backend recebe e processa:
   a. Busca mapeamento no DB para "VALEC125"
   b. Não encontra → executa decode automático:
      - Ticker base: VALE → adiciona "3" → VALE3
      - Mês: C = March (CALL)
      - Strike: 125 / 100 = 1.25
      - Expiration: 3ª sexta de March/2024 = 2024-03-15
   c. Cria registro em mt5_symbol_mappings (auto_created=true)
   d. Retorna mapeamento
   ↓
4. Backend armazena em _OPTIONS_QUOTES:
   Key: "VALE3_1.25_call_2024-03-15"
   Value: { "bid": 2.50, "ask": 2.55, ..., "mt5_symbol": "VALEC125" }
   ↓
5. Provider híbrido passa a ter cotação MT5 disponível
```

### Cenário 2: Consulta de Cotação pelo Sistema

```
1. Sistema solicita cotação de opção:
   hybrid_provider.get_option_quote("VALE3", 1.25, "2024-03-15", "call")
   ↓
2. hybrid_provider verifica storage MT5:
   get_latest_option_quote("VALE3", 1.25, "2024-03-15", "call")
   ↓
3. Se encontrar e estiver dentro do TTL:
   → Retorna cotação MT5 (source="mt5")
   ↓
4. Se não encontrar ou expirado:
   → Fallback para brapi (source="brapi")
```

---

## Priorização de Implementação

### Fase 2.1: Base de Mapeamento (1-2 dias)
- [x] Criar migration SQL
- [ ] Implementar `symbol_mapper.py`
- [ ] Testes unitários do mapper
- [ ] Endpoint GET /api/mt5/mappings

### Fase 2.2: Cotações de Opções (1-2 dias)
- [ ] Atualizar `storage.py` com funções de opções
- [ ] Atualizar `JsonHelper.mqh` para opções
- [ ] Atualizar `VentryBridge.mq5` para coletar opções
- [ ] Endpoint POST /api/mt5/option_quotes

### Fase 2.3: Integração com Provider (1 dia)
- [ ] Atualizar `hybrid_provider.py` para usar storage MT5
- [ ] Testes end-to-end
- [ ] Validação com MT5 real

### Fase 2.4: Interface de Gestão (1 dia)
- [ ] CRUD completo de mapeamentos
- [ ] Interface no frontend (opcional)
- [ ] Documentação de uso

---

## Exemplos de Uso

### 1. Auto-descoberta de Mapeamentos

**Usuário fornece lista de símbolos MT5:**
```bash
POST /api/mt5/mappings/auto-discover
{
    "mt5_symbols": [
        "VALEC125",
        "VALEC130",
        "VALEQ125",
        "PETRJ70",
        "PETRV70"
    ]
}
```

**Backend processa e retorna:**
```json
{
    "created": 5,
    "mappings": [
        {
            "mt5_symbol": "VALEC125",
            "ticker": "VALE3",
            "strike": 62.50,
            "option_type": "call",
            "expiration": "2024-03-15"
        },
        ...
    ]
}
```

### 2. Criação Manual de Mapeamento

**Para casos onde auto-decode falha:**
```bash
POST /api/mt5/mappings
{
    "mt5_symbol": "CUSTOM_SYMBOL_XYZ",
    "ticker": "VALE3",
    "asset_type": "option",
    "strike": 62.50,
    "option_type": "call",
    "expiration_date": "2024-03-15"
}
```

### 3. Configurar EA com Opções

**Arquivo .set atualizado:**
```
InpSymbolsList=VALE3,PETR4,BBAS3
InpOptionsSymbolsList=VALEC125,VALEC130,VALEQ125,PETRJ70
InpQuotesInterval=5
```

---

## Benefícios da Fase 2

### Imediatos
- ✅ Cotações de opções em tempo real do MT5
- ✅ Redução de chamadas para brapi (opções)
- ✅ Mapeamento automático inteligente

### Médio Prazo
- ✅ Base para Fase 3 (execução de ordens)
- ✅ Cotações mais precisas (direto do broker)
- ✅ Menor latência (sem API externa)

### Longo Prazo
- ✅ Sistema 100% independente de APIs externas
- ✅ Suporte a múltiplos brokers/terminais
- ✅ Histórico de cotações próprio

---

## Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| Nomenclatura MT5 diferente por broker | Permitir mapeamento manual + tabela configurável |
| Auto-decode falhar para casos edge | Logs detalhados + fallback para criação manual |
| Performance de lookup | Índices otimizados + cache em memória |
| Símbolos com múltiplos vencimentos | Usar data completa + validar unicidade |

---

## Métricas de Sucesso

- [ ] 90%+ de auto-decode correto para símbolos padrão B3
- [ ] Cotações de opções com latência < 10s
- [ ] 0 erros de mapeamento após configuração inicial
- [ ] Interface de gestão permite criar/editar mapeamentos em < 30s

---

## Próximos Passos

1. Revisar e aprovar este design
2. Criar migration SQL
3. Implementar `symbol_mapper.py`
4. Testes unitários do mapper
5. Atualizar EA para coletar opções
6. Implementar endpoint de cotações
7. Testar end-to-end com MT5 real
8. Documentar configuração

---

**Status Atual:** 🚧 Aguardando aprovação para iniciar implementação
**Tempo Estimado:** 5-7 dias de desenvolvimento
**Documentado por:** Claude Code
**Data:** 31/10/2025
