# Guia de Testes - MT5 Bridge

Este documento descreve como testar a integração MT5 Bridge em diferentes cenários.

## 🧪 Tipos de Teste

### 1. Teste de Simulação (Sem MT5)

Teste os endpoints do backend usando o script Python de simulação.

**Requisitos:**
- Backend rodando
- Token configurado

**Passos:**

```bash
# 1. Configurar token no .env
echo "MT5_BRIDGE_ENABLED=true" >> backend/.env
echo "MT5_BRIDGE_TOKEN=test-token-123" >> backend/.env

# 2. Iniciar backend
cd backend
python -m app.main

# 3. Em outro terminal, configurar token e executar teste
export MT5_BRIDGE_TOKEN=test-token-123
python scripts/test_mt5_bridge.py
```

**Resultado esperado:**

```
HEARTBEAT: 200 {"status":"ok"}
QUOTES: 202 {"accepted":1}
```

### 2. Teste com cURL

Teste individual de endpoints usando cURL.

#### Heartbeat

```bash
curl -X POST http://localhost:8000/api/mt5/heartbeat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token-123" \
  -d '{
    "terminal_id": "TEST-01",
    "account_number": "9999",
    "broker": "TEST",
    "build": 3770,
    "timestamp": "2025-01-22T12:00:00Z"
  }'
```

**Resposta esperada:**
```json
{"status":"ok"}
```

#### Quotes

```bash
curl -X POST http://localhost:8000/api/mt5/quotes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token-123" \
  -d '{
    "terminal_id": "TEST-01",
    "account_number": "9999",
    "quotes": [
      {
        "symbol": "PETR4",
        "bid": 36.50,
        "ask": 36.52,
        "last": 36.51,
        "volume": 1000000,
        "ts": "2025-01-22T12:00:00Z"
      }
    ]
  }'
```

**Resposta esperada:**
```json
{"accepted":1}
```

#### Commands

```bash
curl -X GET "http://localhost:8000/api/mt5/commands?terminal_id=TEST-01&account_number=9999" \
  -H "Authorization: Bearer test-token-123"
```

**Resposta esperada:**
```json
{"commands":[]}
```

### 3. Teste de Autenticação

Teste cenários de falha de autenticação.

#### Token Inválido

```bash
curl -X POST http://localhost:8000/api/mt5/heartbeat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer token-invalido" \
  -d '{"terminal_id":"TEST","account_number":"999","broker":"TEST","build":3770,"timestamp":"2025-01-22T12:00:00Z"}'
```

**Resposta esperada:**
```json
HTTP/1.1 401 Unauthorized
{"error":"unauthorized"}
```

#### Sem Token

```bash
curl -X POST http://localhost:8000/api/mt5/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"terminal_id":"TEST","account_number":"999","broker":"TEST","build":3770,"timestamp":"2025-01-22T12:00:00Z"}'
```

**Resposta esperada:**
```json
HTTP/1.1 401 Unauthorized
{"error":"unauthorized"}
```

#### Bridge Desabilitado

```bash
# Configurar MT5_BRIDGE_ENABLED=false no .env
# Reiniciar backend

curl -X POST http://localhost:8000/api/mt5/heartbeat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token-123" \
  -d '{"terminal_id":"TEST","account_number":"999","broker":"TEST","build":3770,"timestamp":"2025-01-22T12:00:00Z"}'
```

**Resposta esperada:**
```json
HTTP/1.1 403 Forbidden
{"error":"mt5 bridge disabled"}
```

### 4. Teste de Market Data Provider

Teste a integração com o sistema de providers.

#### Configurar Provider Híbrido

```bash
# backend/.env
MARKET_DATA_PROVIDER=hybrid
MARKET_DATA_HYBRID_FALLBACK=brapi
MT5_BRIDGE_QUOTE_TTL_SECONDS=10
```

#### Enviar Cotação via MT5

```bash
curl -X POST http://localhost:8000/api/mt5/quotes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token-123" \
  -d '{
    "terminal_id": "TEST-01",
    "account_number": "9999",
    "quotes": [{"symbol":"PETR4","bid":36.50,"ask":36.52,"last":36.51,"volume":1000000,"ts":"2025-01-22T12:00:00Z"}]
  }'
```

#### Consultar Cotação (via API do sistema)

```bash
# Substitua TOKEN_USUARIO pelo token JWT do usuário
curl http://localhost:8000/api/market-data/quote/PETR4 \
  -H "Authorization: Bearer TOKEN_USUARIO"
```

**Resposta esperada (se MT5 disponível):**
```json
{
  "symbol": "PETR4",
  "current_price": 36.51,
  "bid": 36.50,
  "ask": 36.52,
  "volume": 1000000,
  "timestamp": "2025-01-22T12:00:00Z",
  "source": "mt5"
}
```

**Resposta esperada (se MT5 expirado, fallback):**
```json
{
  "symbol": "PETR4",
  "current_price": 36.45,
  "source": "fallback",
  ...
}
```

### 5. Teste com Expert Advisor Real

Teste end-to-end com o EA rodando no MT5.

**Pré-requisitos:**
- MT5 instalado e logado
- EA compilado e instalado
- URL nas URLs permitidas
- Backend rodando

**Passos:**

1. **Preparar Backend:**

```bash
cd backend

# Configurar .env
cat >> .env << EOF
MT5_BRIDGE_ENABLED=true
MT5_BRIDGE_TOKEN=producao-token-forte-xyz123
MARKET_DATA_PROVIDER=hybrid
MT5_BRIDGE_QUOTE_TTL_SECONDS=10
EOF

# Iniciar servidor
python -m app.main
```

2. **Configurar EA no MT5:**

- Anexar `VentryBridge` a um gráfico
- Configurar parâmetros:
  - `InpBackendUrl`: `http://localhost:8000`
  - `InpAuthToken`: `producao-token-forte-xyz123`
  - `InpTerminalId`: `MT5-PROD-01`
  - `InpBroker`: Nome do seu broker
  - `InpSymbolsList`: `PETR4,VALE3,BBAS3`
  - `InpHeartbeatInterval`: `60`
  - `InpQuotesInterval`: `5`

3. **Verificar Logs do EA:**

Aba Expert no MT5 deve mostrar:

```
=== Ventry Bridge EA - Inicializando ===
Terminal ID: MT5-PROD-01
Conta: 123456
Broker: XP
...
=== Ventry Bridge EA - Inicializado com sucesso ===
Enviando heartbeat...
Heartbeat enviado com sucesso. Resposta: {"status":"ok"}
Enviando 3 cotações...
Cotações enviadas com sucesso. Resposta: {"accepted":3}
```

4. **Verificar Logs do Backend:**

Console do backend deve mostrar:

```json
{"event":"mt5.heartbeat","terminal_id":"MT5-PROD-01",...}
{"event":"mt5.quotes","count":3}
```

5. **Testar Fallback:**

- Pare o EA (remova do gráfico)
- Aguarde > 10 segundos (TTL)
- Consulte cotação via API → deve usar fallback (brapi)
- Reative o EA
- Aguarde alguns segundos
- Consulte cotação via API → deve usar MT5 novamente

### 6. Teste de Carga

Teste o comportamento sob carga.

#### Script de Stress Test

```python
# backend/scripts/stress_test_mt5.py
import asyncio
import aiohttp
import time

BASE_URL = "http://localhost:8000"
TOKEN = "test-token-123"

async def send_quotes(session, terminal_id):
    while True:
        data = {
            "terminal_id": terminal_id,
            "account_number": "9999",
            "quotes": [
                {"symbol": f"TEST{i}", "bid": 10.0, "ask": 10.2, "last": 10.1, "volume": 1000, "ts": "2025-01-22T12:00:00Z"}
                for i in range(10)
            ]
        }

        async with session.post(
            f"{BASE_URL}/api/mt5/quotes",
            json=data,
            headers={"Authorization": f"Bearer {TOKEN}"}
        ) as resp:
            print(f"Terminal {terminal_id}: {resp.status}")

        await asyncio.sleep(1)

async def main():
    async with aiohttp.ClientSession() as session:
        tasks = [send_quotes(session, f"TERMINAL-{i}") for i in range(5)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
```

**Executar:**

```bash
pip install aiohttp
python backend/scripts/stress_test_mt5.py
```

**Monitorar:**
- CPU e memória do backend
- Latência das respostas
- Taxa de erros

### 7. Teste de Persistência

Verificar se os dados são mantidos corretamente.

```python
# Enviar cotação
curl -X POST http://localhost:8000/api/mt5/quotes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token-123" \
  -d '{"terminal_id":"TEST","account_number":"999","quotes":[{"symbol":"PETR4","bid":36.50,"ask":36.52,"last":36.51,"volume":1000000,"ts":"2025-01-22T12:00:00Z"}]}'

# Verificar imediatamente (deve retornar dados)
curl http://localhost:8000/api/market-data/quote/PETR4 \
  -H "Authorization: Bearer TOKEN_USUARIO"

# Aguardar TTL + 1 segundo (10s + 1s = 11s)
sleep 11

# Verificar novamente (deve usar fallback)
curl http://localhost:8000/api/market-data/quote/PETR4 \
  -H "Authorization: Bearer TOKEN_USUARIO"
```

## ✅ Checklist de Validação

Antes de considerar a integração pronta:

### Backend
- [ ] Endpoints respondem corretamente
- [ ] Autenticação funciona (token válido/inválido)
- [ ] Bridge pode ser habilitado/desabilitado
- [ ] Whitelist de IPs funciona (se configurado)
- [ ] Logs estruturados aparecem corretamente
- [ ] TTL de cotações funciona
- [ ] Provider híbrido faz fallback corretamente

### Expert Advisor
- [ ] Compila sem erros
- [ ] Inicializa com sucesso
- [ ] Envia heartbeats periodicamente
- [ ] Envia cotações periodicamente
- [ ] Faz polling de comandos
- [ ] Trata erros de rede gracefully
- [ ] Logs são claros e informativos
- [ ] Configuração via inputs funciona

### Integração
- [ ] EA comunica com backend via HTTP
- [ ] Dados chegam no backend
- [ ] Sistema usa dados do MT5 quando disponíveis
- [ ] Sistema usa fallback quando MT5 indisponível
- [ ] Fonte de dados é identificável (`source: "mt5"`)

### Performance
- [ ] Latência < 500ms
- [ ] Taxa de sucesso > 95%
- [ ] Sem memory leaks após 1h rodando
- [ ] CPU do backend < 50% sob carga normal

### Documentação
- [ ] INSTALLATION.md está completo
- [ ] README.md está atualizado
- [ ] CLAUDE.md menciona MT5
- [ ] Troubleshooting cobre problemas comuns

## 🐛 Problemas Comuns

### Quote não aparece no provider

**Sintoma:** Cotação enviada mas não retornada pela API.

**Debug:**
```bash
# Verificar logs do backend
grep "mt5.quotes" backend.log

# Verificar storage em memória (adicionar endpoint de debug):
curl http://localhost:8000/api/mt5/debug/storage \
  -H "Authorization: Bearer test-token-123"
```

**Soluções:**
- Verificar se TTL não expirou
- Verificar se símbolo está uppercase
- Verificar se provider está configurado como `hybrid` ou `mt5`

### Latência alta

**Sintoma:** Respostas lentas (> 1s).

**Debug:**
- Adicionar timing nos logs
- Verificar rede entre MT5 e backend
- Verificar carga do backend

**Soluções:**
- Aumentar timeout HTTP no EA
- Otimizar intervalo de quotes
- Reduzir número de símbolos monitorados

### Memory leak

**Sintoma:** Memória do backend cresce continuamente.

**Debug:**
```bash
# Monitorar memória
watch -n 1 "ps aux | grep 'python.*app.main'"
```

**Soluções:**
- Verificar se storage não está acumulando dados
- Verificar se há coroutines não finalizadas
- Implementar limpeza periódica de dados expirados

## 📊 Métricas Recomendadas

Para produção, monitore:

- **Taxa de heartbeats/min** - Deve ser ~1/min (se interval=60s)
- **Taxa de quotes/min** - Depende do intervalo configurado
- **Latência P95** - Deve ser < 500ms
- **Taxa de erro HTTP** - Deve ser < 5%
- **Uso de CPU** - Deve ser < 50%
- **Uso de memória** - Deve ser estável (não crescer)
- **Idade da última cotação** - Deve ser < 2x QuotesInterval

## 🎓 Próximos Passos

Após validar Fase 1:

1. **Fase 2 - Opções:**
   - Implementar cotações de opções
   - Mapear símbolos B3
   - Testar com opções reais

2. **Fase 3 - Execução:**
   - Implementar fila de comandos
   - Testar execução de ordens
   - Validar idempotência

3. **Produção:**
   - Deploy em servidor remoto
   - Configurar HTTPS
   - Adicionar monitoramento
   - Configurar alertas
