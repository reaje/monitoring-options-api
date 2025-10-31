# MT5 Bridge Fase 2 - Migration Instructions

**Data:** 31/10/2025
**Status:** AGUARDANDO APLICAÇÃO MANUAL

---

## Situação Atual

### Backend Python: 100% Completo ✅

Todos os componentes backend estão implementados e prontos:

1. **Symbol Mapper** (`MT5/symbol_mapper.py`) - 400 linhas
   - Decodifica símbolos MT5 → Backend
   - Codifica Backend → MT5
   - Testes completos e validados

2. **Storage** (`MT5/storage.py`) - +150 linhas
   - Cache de cotações de opções
   - TTL de 10 segundos
   - Thread-safe com locks

3. **Endpoint** (`MT5/bridge_blueprint.py`) - +80 linhas
   - `POST /api/mt5/option_quotes`
   - Mapeamento automático integrado
   - Error handling robusto

4. **Migration SQL** (`database/migrations/010_create_mt5_symbol_mappings.sql`)
   - Tabela completa com constraints
   - Índices otimizados
   - RLS policies
   - Seed data

### Bloqueio Atual: Migration Não Aplicada

**Problema:** A tabela `mt5_symbol_mappings` ainda não existe no banco de dados Supabase.

**Razão:** O cliente Python do Supabase não pode executar DDL (Data Definition Language) statements diretamente. A migration precisa ser aplicada manualmente.

---

## Instrução: Aplicar Migration Manualmente

### Método 1: Via Supabase Dashboard (RECOMENDADO)

Este é o método mais fácil e seguro.

#### Passo a Passo:

1. **Acesse o Supabase Dashboard**
   - URL: https://supabase.com/dashboard
   - Faça login com suas credenciais

2. **Selecione o Projeto**
   - Selecione o projeto: `monitoring-options` (ou o nome do seu projeto)

3. **Abra o SQL Editor**
   - No menu lateral esquerdo, clique em **"SQL Editor"**

4. **Crie uma Nova Query**
   - Clique em **"New query"** (ou botão "+")

5. **Cole o SQL da Migration**
   - Abra o arquivo: `database/migrations/010_create_mt5_symbol_mappings.sql`
   - Copie TODO o conteúdo (193 linhas)
   - Cole no SQL Editor

6. **Execute a Query**
   - Clique em **"Run"** (ou pressione `Ctrl+Enter`)
   - Aguarde a execução (deve levar ~2-5 segundos)

7. **Verifique o Resultado**
   - Você deve ver mensagens de sucesso como:
     ```
     NOTICE: Migration 010: mt5_symbol_mappings table created successfully
     ```
   - Verifique se não há erros em vermelho

8. **Confirme a Criação**
   - No menu lateral, clique em **"Table Editor"**
   - Procure pela tabela `mt5_symbol_mappings`
   - Você deve ver as colunas: `id`, `mt5_symbol`, `ticker`, `asset_type`, etc.

---

### Método 2: Via psql Command Line

Se você tem acesso ao `psql` no terminal:

```bash
# No diretório raiz do projeto
psql $DATABASE_URL < database/migrations/010_create_mt5_symbol_mappings.sql
```

**Nota:** O `DATABASE_URL` deve estar configurado no `.env`

---

### Método 3: Via pgAdmin ou GUI Tool

Se você usa pgAdmin ou outro cliente PostgreSQL:

1. Conecte ao banco Supabase usando as credenciais
2. Navegue até o schema `monitoring_options_operations`
3. Abra uma nova query window
4. Cole o conteúdo de `010_create_mt5_symbol_mappings.sql`
5. Execute

---

## Validação Pós-Migration

### Após aplicar a migration, valide executando:

```bash
cd backend
python scripts/apply_migration_supabase.py
```

**Saída esperada:**
```
======================================================================
TABLE ALREADY EXISTS!
======================================================================

Table 'mt5_symbol_mappings' already exists!
Current records: 6

Sample mappings:
  - VALE3 -> VALE3 (type: stock)
  - PETR4 -> PETR4 (type: stock)
  - BBAS3 -> BBAS3 (type: stock)
  - VALEC125 -> VALE3 (type: option)
  - VALEQ125 -> VALE3 (type: option)
  - PETRJ70 -> PETR4 (type: option)

======================================================================
Migration not needed - table exists and is functional!
======================================================================
```

---

## O Que a Migration Faz?

### Cria a Tabela `mt5_symbol_mappings`

**Campos principais:**
- `mt5_symbol` (VARCHAR) - Símbolo do MT5 (ex: "VALEC125")
- `ticker` (VARCHAR) - Ticker do backend (ex: "VALE3")
- `asset_type` (VARCHAR) - Tipo: "stock" ou "option"
- `strike` (DECIMAL) - Strike price (apenas opções)
- `option_type` (VARCHAR) - "call" ou "put" (apenas opções)
- `expiration_date` (DATE) - Data de vencimento (apenas opções)

### Cria 4 Índices Otimizados

1. `idx_mt5_mappings_ticker` - Busca por ticker
2. `idx_mt5_mappings_option_lookup` - Busca por (ticker + strike + type + expiration)
3. `idx_mt5_mappings_user` - Busca por user_id
4. `idx_mt5_mappings_auto_created` - Filtro por auto_created

### Configura RLS Policies

- **SELECT:** Todos podem ler
- **INSERT:** Apenas próprio user_id
- **UPDATE:** Próprio user_id ou auto_created
- **DELETE:** Apenas próprio user_id

### Insere Seed Data (6 registros)

**Stocks:**
- VALE3 → VALE3
- PETR4 → PETR4
- BBAS3 → BBAS3

**Options (exemplos):**
- VALEC125 → VALE3 strike=62.50 CALL exp=2024-11-15
- VALEQ125 → VALE3 strike=62.50 PUT exp=2024-11-15
- PETRJ70 → PETR4 strike=35.00 CALL exp=2024-10-18

---

## Próximos Passos Após Migration

Depois que a migration for aplicada com sucesso:

### 1. Validar Backend (5 min)

```bash
cd backend
python scripts/apply_migration_supabase.py
```

### 2. Testar Symbol Mapper (2 min)

```bash
cd backend
python scripts/test_symbol_mapper.py
```

### 3. Implementar JsonHelper.mqh (30 min)

Atualizar o arquivo `MT5/Include/JsonHelper.mqh` para incluir função:
```mql5
string BuildOptionQuotesJson(const string &option_symbols[], int count)
```

### 4. Atualizar VentryBridge.mq5 (30 min)

Adicionar:
- Input: `InpOptionsSymbolsList`
- Função: `SendOptionQuotes()`
- Timer: envio a cada 5s

### 5. Testar com MT5 Real (1 hora)

- Compilar EA atualizado
- Configurar símbolos de opções
- Validar logs MT5 + backend
- Verificar cache com `validate_cache.py`

### 6. Integrar com Hybrid Provider (30 min)

Atualizar `MT5/hybrid_provider.py` para:
- Consultar cache MT5 primeiro
- Fallback para brapi se não encontrado ou expirado

---

## Troubleshooting

### Migration falha com "schema does not exist"

**Solução:** Crie o schema primeiro:
```sql
CREATE SCHEMA IF NOT EXISTS monitoring_options_operations;
```

### Migration falha com "permission denied"

**Solução:** Use a service role key do Supabase (não a anon key)

### Tabela criada mas sem seed data

**Solução:** Execute apenas a parte de INSERT:
```sql
INSERT INTO monitoring_options_operations.mt5_symbol_mappings
    (mt5_symbol, ticker, asset_type, auto_created)
VALUES
    ('VALE3', 'VALE3', 'stock', true),
    ('PETR4', 'PETR4', 'stock', true),
    ('BBAS3', 'BBAS3', 'stock', true)
ON CONFLICT (mt5_symbol) DO NOTHING;

-- Options examples...
```

### Script de validação ainda diz "table does not exist"

**Possíveis causas:**
1. Migration aplicada no schema errado
2. Cache do cliente Supabase
3. Configuração de `DB_SCHEMA` incorreta no `.env`

**Solução:** Verifique via SQL Editor:
```sql
SELECT COUNT(*)
FROM monitoring_options_operations.mt5_symbol_mappings;
```

---

## Contatos e Documentação

- **Design da Fase 2:** `backend/MT5/FASE2_DESIGN.md`
- **Status da Fase 2:** `backend/MT5/STATUS_FASE2.md`
- **Migration SQL:** `database/migrations/010_create_mt5_symbol_mappings.sql`
- **Script de Validação:** `backend/scripts/apply_migration_supabase.py`

---

## Resumo

**O QUE FAZER AGORA:**

1. Acesse https://supabase.com/dashboard
2. Abra o SQL Editor
3. Cole o conteúdo de `database/migrations/010_create_mt5_symbol_mappings.sql`
4. Execute a query
5. Valide com `python scripts/apply_migration_supabase.py`

**TEMPO ESTIMADO:** 5-10 minutos

**APÓS MIGRAÇÃO:**
- Fase 2 Backend estará 100% funcional
- Poderá prosseguir para implementação MQL5 (EA)
- Sistema de mapeamento automático estará ativo

---

**Documentado por:** Claude Code
**Data:** 31/10/2025
**Versão:** 1.0
