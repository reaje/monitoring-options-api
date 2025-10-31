# Correção - MT5 Bridge JSON Parse Error

**Data:** 31/10/2025
**Problema:** Expert Advisor enviando JSON com caractere nulo (null terminator)
**Status:** ✅ RESOLVIDO

---

## Problema Identificado

O VentryBridge EA estava recebendo erro 400 ao enviar cotações para o backend:

```
HTTP error: 400
Response: {"error":"invalid_json","details":"Failed when parsing body as json"}
```

### Causa Raiz

O JSON enviado pelo EA continha um **caractere nulo** (`\u0000`) no final:

```json
{"terminal_id":"MT5-WS-01","account_number":"4472007","quotes":[...]}\u0000
                                                                        ^^^^
```

Isso é inválido em JSON e causava falha no parse pelo backend Python.

### Por Que Acontecia?

No arquivo `Include/HttpClient.mqh`, linha 49:

```mql5
// ANTES (ERRADO)
int data_len = StringToCharArray(json_data, post_data, 0, WHOLE_ARRAY, CP_UTF8) - 1;

ResetLastError();
int res = WebRequest(
    "POST",
    url,
    headers,
    m_timeout,
    post_data,  // ← Array ainda contém null terminator!
    result_data,
    result_headers
);
```

O código calculava `data_len` (tamanho sem null terminator) mas **não usava** esse valor. O array `post_data` ainda tinha o caractere nulo no final e era enviado inteiro.

---

## Solução Implementada

### Arquivo Corrigido: `Include/HttpClient.mqh`

**Linhas 48-53:**

```mql5
// DEPOIS (CORRETO)
// Converter string para array de bytes (sem null terminator)
int data_len = StringToCharArray(json_data, post_data, 0, WHOLE_ARRAY, CP_UTF8) - 1;

// Redimensionar array para remover o null terminator
if(data_len > 0)
    ArrayResize(post_data, data_len);

ResetLastError();
int res = WebRequest(
    "POST",
    url,
    headers,
    m_timeout,
    post_data,  // ← Agora sem null terminator!
    result_data,
    result_headers
);
```

**O que foi feito:**
1. Calculamos o tamanho correto (`data_len`) sem o null terminator
2. **Redimensionamos o array** `post_data` para esse tamanho
3. Agora o WebRequest envia apenas os bytes válidos do JSON

---

## Validação

### Antes da Correção

```
2025.10.31 11:05:24 VentryBridge (VALE3,H1) HTTP error: 400
2025.10.31 11:05:24 VentryBridge (VALE3,H1) Response: {"error":"invalid_json",...}
2025.10.31 11:05:24 VentryBridge (VALE3,H1) ERRO: Falha ao enviar cotações!
```

### Depois da Correção

```
2025.10.31 11:20:46 VentryBridge (VALE3,H1) Enviando 2 cotações...
2025.10.31 11:20:46 VentryBridge (VALE3,H1) Cotações enviadas com sucesso. Resposta: {"accepted":2}
```

✅ **Status: FUNCIONANDO**

---

## Arquivos Modificados

### 1. `backend/MT5/Include/HttpClient.mqh`
- **Mudança:** Adicionado `ArrayResize(post_data, data_len)` após calcular tamanho
- **Motivo:** Remover null terminator do array antes de enviar via WebRequest
- **Impacto:** Corrige JSON enviado para ser válido

### 2. `backend/MT5/bridge_blueprint.py`
- **Mudança:** Removidos logs temporários de debug (`raw_body`)
- **Motivo:** Limpeza após identificar e corrigir o problema
- **Impacto:** Código mais limpo e logs mais concisos

---

## Como Aplicar a Correção

Se você estiver começando do zero:

1. **Certifique-se de usar o `HttpClient.mqh` corrigido:**
   - Arquivo em: `backend/MT5/Include/HttpClient.mqh`
   - Contém o `ArrayResize(post_data, data_len)` na linha 52-53

2. **Copie os arquivos para a pasta do MT5:**
   ```
   Origem: D:\Projetos\Ventry\monitoring-options\backend\MT5\
   Destino: C:\Users\<usuario>\AppData\Roaming\MetaQuotes\Terminal\<ID>\MQL5\

   Copiar:
   - VentryBridge.mq5 → Experts\
   - Include\HttpClient.mqh → Include\
   - Include\JsonHelper.mqh → Include\
   ```

3. **Compile no MetaEditor:**
   - Abra `VentryBridge.mq5`
   - Pressione F7
   - Deve mostrar "0 errors, 0 warnings"

4. **Anexe ao gráfico no MT5:**
   - Arraste do Navigator para o gráfico
   - Configure com o arquivo `.set` correto

---

## Lições Aprendidas

### Problema Comum em MQL5

O null terminator é comum em C/C++, mas **inválido em JSON**. Sempre que converter strings MQL5 para arrays de bytes:

```mql5
// ✅ SEMPRE faça isso:
int data_len = StringToCharArray(str, arr, 0, WHOLE_ARRAY, CP_UTF8) - 1;
ArrayResize(arr, data_len);

// ❌ NUNCA faça isso:
StringToCharArray(str, arr, 0, WHOLE_ARRAY, CP_UTF8);
// (Array terá \0 no final!)
```

### Debug de JSON Malformado

Para debugar JSON inválido:

1. **Backend:** Capture o raw body antes de fazer parse
2. **Olhe para o final da string:** Caracteres de controle geralmente aparecem lá
3. **Use ferramentas:** JSON validators mostram `\u0000` claramente

---

## Status Final

✅ **MT5 Bridge Totalmente Operacional**

- Heartbeat: Enviado a cada 60s ✅
- Quotes: Enviadas a cada 5s ✅
- Commands polling: A cada 10s ✅
- Backend: Recebendo e processando dados corretamente ✅

**Próximos Passos:**
- Fase 2: Implementar cotações de opções + mapeamento de símbolos
- Fase 3: Implementar execução de ordens (rolls)

---

**Documentado por:** Claude Code
**Data:** 31/10/2025
**Commit:** (aguardando)
