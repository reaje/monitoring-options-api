# API Endpoints - Backend

## 📋 Visão Geral

Base URL: `http://localhost:8000`

Total de Endpoints: **58**

## 🔐 Autenticação

Todos os endpoints protegidos requerem header:
```
Authorization: Bearer <jwt_token>
```

---

## 🏥 Health & Info

### GET /health
Health check do servidor

**Response 200:**
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

### GET /
Informações da API

**Response 200:**
```json
{
  "name": "Monitoring Options API",
  "version": "1.0.0",
  "description": "API para monitoramento de operações com opções",
  "docs_url": "/docs",
  "health_check": "/health"
}
```

---

## 🔑 Auth - Autenticação (6 endpoints)

### POST /auth/register
Registrar novo usuário

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "User Name"
}
```

**Response 201:**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name",
    "created_at": "2025-01-22T10:30:00Z"
  }
}
```

### POST /auth/login
Login de usuário

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response 200:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name"
  }
}
```

### POST /auth/refresh
Renovar access token

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response 200:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### POST /auth/logout
Logout (requer autenticação)

**Response 200:**
```json
{
  "message": "Logout successful"
}
```

### GET /auth/me
Dados do usuário autenticado

**Response 200:**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name",
    "created_at": "2025-01-22T10:30:00Z"
  }
}
```

### POST /auth/change-password
Trocar senha

**Request:**
```json
{
  "current_password": "oldpass123",
  "new_password": "newpass123"
}
```

**Response 200:**
```json
{
  "message": "Password changed successfully"
}
```

---

## 💼 Accounts - Contas (5 endpoints)

### GET /api/accounts
Listar contas do usuário

**Response 200:**
```json
{
  "accounts": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "name": "My Account",
      "created_at": "2025-01-22T10:30:00Z"
    }
  ],
  "total": 1
}
```

### POST /api/accounts
Criar nova conta

**Request:**
```json
{
  "name": "New Account"
}
```

**Response 201:**
```json
{
  "message": "Account created successfully",
  "account": {
    "id": "uuid",
    "user_id": "uuid",
    "name": "New Account",
    "created_at": "2025-01-22T10:30:00Z"
  }
}
```

### GET /api/accounts/{account_id}
Detalhes da conta

**Response 200:**
```json
{
  "account": {
    "id": "uuid",
    "user_id": "uuid",
    "name": "My Account",
    "created_at": "2025-01-22T10:30:00Z"
  }
}
```

### PUT /api/accounts/{account_id}
Atualizar conta

**Request:**
```json
{
  "name": "Updated Account Name"
}
```

**Response 200:**
```json
{
  "message": "Account updated successfully",
  "account": {
    "id": "uuid",
    "name": "Updated Account Name",
    ...
  }
}
```

### DELETE /api/accounts/{account_id}
Deletar conta

**Response 200:**
```json
{
  "message": "Account deleted successfully"
}
```

---

## 📈 Assets - Ativos (5 endpoints)

### GET /api/assets
Listar ativos

**Query Params:**
- `account_id` (optional): UUID da conta

**Response 200:**
```json
{
  "assets": [
    {
      "id": "uuid",
      "account_id": "uuid",
      "ticker": "PETR4",
      "created_at": "2025-01-22T10:30:00Z"
    }
  ],
  "total": 1
}
```

### POST /api/assets
Criar novo ativo

**Request:**
```json
{
  "account_id": "uuid",
  "ticker": "PETR4"
}
```

**Response 201:**
```json
{
  "message": "Asset created successfully",
  "asset": {
    "id": "uuid",
    "account_id": "uuid",
    "ticker": "PETR4",
    "created_at": "2025-01-22T10:30:00Z"
  }
}
```

### GET /api/assets/{asset_id}
Detalhes do ativo

**Response 200:**
```json
{
  "asset": {
    "id": "uuid",
    "account_id": "uuid",
    "ticker": "PETR4",
    "created_at": "2025-01-22T10:30:00Z"
  }
}
```

### PUT /api/assets/{asset_id}
Atualizar ativo

**Request:**
```json
{
  "ticker": "VALE3"
}
```

**Response 200:**
```json
{
  "message": "Asset updated successfully",
  "asset": {
    "id": "uuid",
    "ticker": "VALE3",
    ...
  }
}
```

### DELETE /api/assets/{asset_id}
Deletar ativo

**Response 200:**
```json
{
  "message": "Asset deleted successfully"
}
```

---

## 📊 Options - Posições de Opções (8 endpoints)

### GET /api/options
Listar posições de opções

**Query Params:**
- `account_id` (optional): UUID da conta
- `asset_id` (optional): UUID do ativo
- `status` (optional): OPEN | CLOSED | EXPIRED

**Response 200:**
```json
{
  "positions": [
    {
      "id": "uuid",
      "account_id": "uuid",
      "asset_id": "uuid",
      "side": "CALL",
      "strategy": "COVERED_CALL",
      "strike": 100.00,
      "expiration": "2025-03-15",
      "quantity": 100,
      "avg_premium": 2.50,
      "status": "OPEN",
      "notes": "Optional notes",
      "created_at": "2025-01-22T10:30:00Z"
    }
  ],
  "total": 1
}
```

### GET /api/options/active
Listar apenas posições abertas (OPEN)

**Query Params:**
- `account_id` (optional): UUID da conta

**Response 200:**
```json
{
  "positions": [...],
  "total": 5
}
```

### POST /api/options
Criar nova posição

**Request:**
```json
{
  "account_id": "uuid",
  "asset_id": "uuid",
  "side": "CALL",
  "strategy": "COVERED_CALL",
  "strike": 100.00,
  "expiration": "2025-03-15",
  "quantity": 100,
  "avg_premium": 2.50,
  "notes": "Optional notes"
}
```

**Response 201:**
```json
{
  "message": "Position created successfully",
  "position": {
    "id": "uuid",
    "account_id": "uuid",
    "asset_id": "uuid",
    "side": "CALL",
    "strategy": "COVERED_CALL",
    "strike": 100.00,
    "expiration": "2025-03-15",
    "quantity": 100,
    "avg_premium": 2.50,
    "status": "OPEN",
    "notes": "Optional notes",
    "created_at": "2025-01-22T10:30:00Z"
  }
}
```

**Enums:**
- `side`: CALL | PUT
- `strategy`: COVERED_CALL | SHORT_PUT | LONG_PUT | OTHER
- `status`: OPEN | CLOSED | EXPIRED

### GET /api/options/{position_id}
Detalhes da posição

**Response 200:**
```json
{
  "position": {
    "id": "uuid",
    "account_id": "uuid",
    "asset_id": "uuid",
    "side": "CALL",
    "strategy": "COVERED_CALL",
    ...
  }
}
```

### PUT /api/options/{position_id}
Atualizar posição

**Request:**
```json
{
  "strike": 105.00,
  "quantity": 200,
  "avg_premium": 3.00,
  "status": "CLOSED",
  "notes": "Updated notes"
}
```

**Response 200:**
```json
{
  "message": "Position updated successfully",
  "position": {
    "id": "uuid",
    "strike": 105.00,
    ...
  }
}
```

### DELETE /api/options/{position_id}
Deletar posição

**Response 200:**
```json
{
  "message": "Position deleted successfully"
}
```

### POST /api/options/{position_id}/close
Fechar posição (status = CLOSED)

**Response 200:**
```json
{
  "message": "Position closed successfully",
  "position": {
    "id": "uuid",
    "status": "CLOSED",
    ...
  }
}
```

### GET /api/options/statistics/{account_id}
Estatísticas de posições da conta

**Response 200:**
```json
{
  "statistics": {
    "total_positions": 10,
    "open_positions": 5,
    "closed_positions": 5,
    "strategies": {
      "COVERED_CALL": 7,
      "SHORT_PUT": 2,
      "LONG_PUT": 1
    }
  }
}
```

---

## ⚙️ Rules - Regras de Rolagem (6 endpoints)

### GET /api/rules
Listar regras de rolagem

**Query Params:**
- `account_id` (optional): UUID da conta

**Response 200:**
```json
{
  "rules": [
    {
      "id": "uuid",
      "account_id": "uuid",
      "delta_threshold": 0.60,
      "dte_min": 3,
      "dte_max": 5,
      "spread_threshold": 5.0,
      "price_to_strike_ratio": 0.98,
      "min_volume": 1000,
      "max_spread": 0.05,
      "min_oi": 5000,
      "target_otm_pct_low": 0.03,
      "target_otm_pct_high": 0.08,
      "notify_channels": ["whatsapp", "sms"],
      "is_active": true,
      "created_at": "2025-01-22T10:30:00Z"
    }
  ],
  "total": 1
}
```

### GET /api/rules/active
Listar apenas regras ativas (is_active = true)

**Query Params:**
- `account_id` (optional): UUID da conta

**Response 200:**
```json
{
  "rules": [...],
  "total": 2
}
```

### POST /api/rules
Criar nova regra

**Request:**
```json
{
  "account_id": "uuid",
  "delta_threshold": 0.65,
  "dte_min": 5,
  "dte_max": 7,
  "spread_threshold": 3.5,
  "price_to_strike_ratio": 0.98,
  "min_volume": 1000,
  "max_spread": 0.05,
  "min_oi": 5000,
  "target_otm_pct_low": 0.03,
  "target_otm_pct_high": 0.08,
  "notify_channels": ["whatsapp", "sms"],
  "is_active": true
}
```

**Response 201:**
```json
{
  "message": "Rule created successfully",
  "rule": {
    "id": "uuid",
    "account_id": "uuid",
    "delta_threshold": 0.65,
    "dte_min": 5,
    "dte_max": 7,
    "is_active": true,
    "created_at": "2025-01-22T10:30:00Z",
    ...
  }
}
```

**Field Descriptions:**
- `delta_threshold`: Delta threshold para trigger (0-1)
- `dte_min`: Dias mínimos até vencimento
- `dte_max`: Dias máximos até vencimento
- `spread_threshold`: Percentual de spread threshold
- `price_to_strike_ratio`: Razão mínima preço/strike (0-1)
- `min_volume`: Volume mínimo diário requerido
- `max_spread`: Spread bid-ask máximo permitido
- `min_oi`: Open interest mínimo requerido
- `target_otm_pct_low`: Percentual OTM baixo desejado (0-1)
- `target_otm_pct_high`: Percentual OTM alto desejado (0-1)
- `notify_channels`: Canais de notificação (whatsapp, sms, email)
- `is_active`: Se a regra está ativa

### GET /api/rules/{rule_id}
Detalhes da regra

**Response 200:**
```json
{
  "rule": {
    "id": "uuid",
    "account_id": "uuid",
    "delta_threshold": 0.60,
    ...
  }
}
```

### PUT /api/rules/{rule_id}
Atualizar regra

**Request:**
```json
{
  "delta_threshold": 0.70,
  "dte_min": 7,
  "is_active": false
}
```

**Response 200:**
```json
{
  "message": "Rule updated successfully",
  "rule": {
    "id": "uuid",
    "delta_threshold": 0.70,
    ...
  }
}
```

### DELETE /api/rules/{rule_id}
Deletar regra

**Response 200:**
```json
{
  "message": "Rule deleted successfully"
}
```

### POST /api/rules/{rule_id}/toggle
Alternar status ativo/inativo da regra

**Response 200:**
```json
{
  "message": "Rule toggled successfully",
  "rule": {
    "id": "uuid",
    "is_active": false,
    ...
  }
}
```

---

## 🔔 Alerts - Sistema de Alertas (9 endpoints)

### GET /api/alerts
Listar alertas

**Query Params:**
- `account_id` (optional): UUID da conta
- `status` (optional): PENDING | PROCESSING | SENT | FAILED

**Response 200:**
```json
{
  "alerts": [
    {
      "id": "uuid",
      "account_id": "uuid",
      "option_position_id": "uuid",
      "reason": "roll_trigger",
      "payload": {
        "delta": 0.75,
        "dte": 3,
        "message": "Roll condition met"
      },
      "status": "PENDING",
      "created_at": "2025-01-22T10:30:00Z"
    }
  ],
  "total": 1
}
```

### GET /api/alerts/pending
Listar apenas alertas pendentes (status = PENDING)

**Query Params:**
- `account_id` (optional): UUID da conta

**Response 200:**
```json
{
  "alerts": [...],
  "total": 5
}
```

### POST /api/alerts
Criar novo alerta manualmente

**Request:**
```json
{
  "account_id": "uuid",
  "option_position_id": "uuid",
  "reason": "manual_alert",
  "payload": {
    "message": "Custom notification message",
    "priority": "high"
  }
}
```

**Response 201:**
```json
{
  "message": "Alert created successfully",
  "alert": {
    "id": "uuid",
    "account_id": "uuid",
    "reason": "manual_alert",
    "status": "PENDING",
    "created_at": "2025-01-22T10:30:00Z",
    ...
  }
}
```

**Common Alert Reasons:**
- `roll_trigger` - Regra de rolagem disparada
- `expiration_warning` - Aviso de vencimento próximo
- `delta_threshold` - Threshold de delta atingido
- `manual_alert` - Alerta criado manualmente

### GET /api/alerts/{alert_id}
Detalhes do alerta

**Response 200:**
```json
{
  "alert": {
    "id": "uuid",
    "account_id": "uuid",
    "reason": "roll_trigger",
    "payload": {...},
    "status": "SENT",
    ...
  }
}
```

### DELETE /api/alerts/{alert_id}
Deletar alerta

**Response 200:**
```json
{
  "message": "Alert deleted successfully"
}
```

### POST /api/alerts/{alert_id}/retry
Retentar envio de alerta falhado

**Response 200:**
```json
{
  "message": "Alert marked for retry",
  "alert": {
    "id": "uuid",
    "status": "PENDING",
    ...
  }
}
```

### GET /api/alerts/statistics/{account_id}
Estatísticas de alertas da conta

**Query Params:**
- `hours` (optional): Horas para retroceder (default: 24)

**Response 200:**
```json
{
  "statistics": {
    "period_hours": 24,
    "total_alerts": 15,
    "pending": 3,
    "processing": 1,
    "sent": 10,
    "failed": 1,
    "success_rate": 66.67,
    "reasons": {
      "roll_trigger": 8,
      "expiration_warning": 5,
      "manual_alert": 2
    }
  }
}
```

### GET /api/alerts/{alert_id}/logs
Logs de notificação de um alerta

**Response 200:**
```json
{
  "logs": [
    {
      "id": "uuid",
      "queue_id": "uuid",
      "channel": "whatsapp",
      "target": "+5511999999999",
      "message": "Sua opção PETR4 atingiu o critério de rolagem",
      "status": "success",
      "sent_at": "2025-01-22T10:31:00Z",
      "provider_msg_id": "wamid.xxx"
    }
  ],
  "total": 1
}
```

### GET /api/alerts/logs/statistics
Estatísticas globais de logs de notificação

**Query Params:**
- `hours` (optional): Horas para retroceder (default: 24)

**Response 200:**
```json
{
  "statistics": {
    "period_hours": 24,
    "total_notifications": 50,
    "successful": 48,
    "failed": 2,
    "success_rate": 96.00,
    "by_channel": {
      "whatsapp": {
        "total": 35,
        "success": 34,
        "failed": 1
      },
      "sms": {
        "total": 15,
        "success": 14,
        "failed": 1
      }
    }
  }
}
```

---

## 📱 Notifications - Envio de Notificações (4 endpoints)

### POST /api/notifications/send
Enviar notificação manual

**Request:**
```json
{
  "account_id": "uuid",
  "message": "Mensagem personalizada de notificação",
  "channels": ["whatsapp", "sms"],
  "phone": "+5511999999999"
}
```

**Response 200:**
```json
{
  "message": "Notification sent to 2/2 channels",
  "results": {
    "whatsapp": {
      "status": "success",
      "message_id": "wamid.xxx"
    },
    "sms": {
      "status": "success",
      "message_id": "sms_yyy"
    }
  }
}
```

**Channels Disponíveis:**
- `whatsapp` - WhatsApp via CommunicationsAPI
- `sms` - SMS via CommunicationsAPI
- `email` - Email (requer campo email na conta)

### POST /api/notifications/test
Enviar notificação de teste

**Request:**
```json
{
  "channel": "whatsapp",
  "phone": "+5511999999999"
}
```

**Response 200:**
```json
{
  "message": "Test notification sent successfully",
  "result": {
    "message_id": "test_msg_123",
    "status": "sent"
  }
}
```

### GET /api/notifications/status/{message_id}
Verificar status de entrega de mensagem

**Response 200:**
```json
{
  "status": {
    "message_id": "wamid.xxx",
    "status": "delivered",
    "timestamp": "2025-01-22T10:35:00Z",
    "provider": "whatsapp"
  }
}
```

**Possíveis Status:**
- `sent` - Enviado
- `delivered` - Entregue
- `read` - Lido (WhatsApp)
- `failed` - Falhou

### POST /api/notifications/process-queue
Processar fila de alertas manualmente (Admin/Debug)

**Query Params:**
- `limit` (optional): Máximo de alertas para processar (default: 100)

**Response 200:**
```json
{
  "message": "Queue processing completed",
  "results": {
    "total": 15,
    "successful": 14,
    "failed": 1
  }
}
```

---

## ⚙️ Workers - Gerenciamento de Workers (5 endpoints)

### GET /api/workers/status
Status de todos os background workers

**Response 200:**
```json
{
  "scheduler_running": true,
  "jobs": [
    {
      "id": "monitor_positions",
      "name": "Monitor Option Positions",
      "next_run": "2025-01-22T10:35:00Z",
      "trigger": "interval[0:05:00]"
    },
    {
      "id": "process_alerts",
      "name": "Process Alert Queue",
      "next_run": "2025-01-22T10:30:30Z",
      "trigger": "interval[0:00:30]"
    },
    {
      "id": "cleanup_data",
      "name": "Cleanup Old Data",
      "next_run": "2025-01-23T03:00:00Z",
      "trigger": "cron[hour='3', minute='0']"
    },
    {
      "id": "expire_positions",
      "name": "Expire Old Positions",
      "next_run": "2025-01-23T01:00:00Z",
      "trigger": "cron[hour='1', minute='0']"
    }
  ],
  "total_jobs": 4
}
```

**Jobs Disponíveis:**
- `monitor_positions` - Monitora posições e cria alertas (a cada 5 min)
- `process_alerts` - Processa fila de alertas (a cada 30 seg)
- `cleanup_data` - Limpa dados antigos (diário às 3h)
- `expire_positions` - Expira posições vencidas (diário à 1h)

### GET /api/workers/status/{job_id}
Status de um job específico

**Response 200:**
```json
{
  "job": {
    "id": "monitor_positions",
    "name": "Monitor Option Positions",
    "next_run": "2025-01-22T10:35:00Z",
    "trigger": "interval[0:05:00]"
  }
}
```

### POST /api/workers/jobs/{job_id}/pause
Pausar um worker

**Response 200:**
```json
{
  "message": "Job monitor_positions paused successfully"
}
```

### POST /api/workers/jobs/{job_id}/resume
Retomar um worker pausado

**Response 200:**
```json
{
  "message": "Job monitor_positions resumed successfully"
}
```

### POST /api/workers/jobs/{job_id}/trigger
Disparar um job manualmente (imediatamente)

**Response 200:**
```json
{
  "message": "Job monitor_positions triggered successfully",
  "result": {
    "check_number": 15,
    "timestamp": "2025-01-22T10:32:00Z",
    "accounts_processed": 5,
    "positions_checked": 12,
    "alerts_created": 3
  }
}
```

**Jobs que podem ser disparados manualmente:**
- `monitor_positions` - Retorna estatísticas de monitoramento
- `process_alerts` - Retorna estatísticas de processamento

---

## 🔄 Rolls - Calculadora de Rolagem (3 endpoints)

### POST /api/rolls/preview
Previsualização de rolagem com sugestões

**Request:**
```json
{
  "option_position_id": "uuid",
  "market_data": {
    "current_price": 98.50,
    "bid": 98.45,
    "ask": 98.55
  }
}
```

**Response 200:**
```json
{
  "current_position": {
    "id": "uuid",
    "ticker": "PETR4",
    "side": "CALL",
    "strike": 100.00,
    "expiration": "2025-02-15",
    "quantity": 100,
    "avg_premium": 2.50,
    "dte": 5,
    "otm_pct": 2.04,
    "is_itm": false,
    "current_premium": 1.20,
    "pnl": 13000.00,
    "current_price": 98.00
  },
  "suggestions": [
    {
      "strike": 100.88,
      "expiration": "2025-03-15",
      "dte": 30,
      "otm_pct": 3.00,
      "premium": 2.80,
      "net_credit": 1.60,
      "spread": 0.02,
      "volume": 5000,
      "oi": 10000,
      "score": 85.50
    },
    {
      "strike": 102.90,
      "expiration": "2025-03-15",
      "dte": 30,
      "otm_pct": 5.00,
      "premium": 2.40,
      "net_credit": 1.20,
      "spread": 0.02,
      "volume": 5000,
      "oi": 10000,
      "score": 78.30
    }
  ],
  "market_data": {
    "ticker": "PETR4",
    "current_price": 98.00,
    "bid": 97.90,
    "ask": 98.10,
    "volume": 1500000,
    "timestamp": "2025-01-22T10:45:00Z"
  },
  "rule_used": {
    "delta_threshold": 0.60,
    "dte_min": 21,
    "dte_max": 45,
    "target_otm_pct_low": 0.03,
    "target_otm_pct_high": 0.08
  }
}
```

**Algoritmo de Score:**
O score (0-100) é calculado baseado em:
- **Net Credit** (40 pontos): Quanto maior o crédito líquido, maior o score
- **OTM no Range Alvo** (30 pontos): Proximidade do OTM% ideal (3-8%)
- **DTE no Range Alvo** (20 pontos): Proximidade do DTE ideal (21-45 dias)
- **Liquidez** (10 pontos): Volume e Open Interest

### GET /api/rolls/suggestions/{position_id}
Sugestões de rolagem simplificadas

**Response 200:**
```json
{
  "position_id": "uuid",
  "current_metrics": {
    "dte": 5,
    "otm_pct": 2.04,
    "current_price": 98.00
  },
  "suggestions": [
    {
      "strike": 100.88,
      "expiration": "2025-03-15",
      "dte": 30,
      "otm_pct": 3.00,
      "premium": 2.80,
      "net_credit": 1.60,
      "score": 85.50
    }
  ]
}
```

### GET /api/rolls/analysis/{account_id}
Análise de rolagem para todas posições abertas da conta

**Response 200:**
```json
{
  "account_id": "uuid",
  "positions": [
    {
      "position_id": "uuid",
      "ticker": "PETR4",
      "strike": 100.00,
      "expiration": "2025-02-15",
      "side": "CALL",
      "current_metrics": {
        "dte": 5,
        "otm_pct": 2.04,
        "pnl": 13000.00
      },
      "best_suggestion": {
        "strike": 100.88,
        "expiration": "2025-03-15",
        "dte": 30,
        "otm_pct": 3.00,
        "premium": 2.80,
        "net_credit": 1.60,
        "score": 85.50
      },
      "total_suggestions": 5
    }
  ],
  "total_positions": 1
}
```

**Nota:** Os cálculos atuais usam estimativas mock. Em produção, integrar com dados reais de mercado (opções chain, greeks, etc.).

---

## 📊 Market Data - Dados de Mercado (5 endpoints)

### GET /api/market/quote/{ticker}
Cotação atual de um ativo

**Path Parameters:**
- `ticker`: Símbolo do ticker (ex: PETR4, VALE3)

**Response 200:**
```json
{
  "ticker": "PETR4",
  "current_price": 28.35,
  "bid": 28.32,
  "ask": 28.38,
  "previous_close": 28.50,
  "change": -0.15,
  "change_percent": -0.53,
  "volume": 2500000,
  "high": 28.65,
  "low": 28.10,
  "timestamp": "2025-01-22T10:45:00Z",
  "market_status": "open"
}
```

### GET /api/market/options/{ticker}
Cadeia de opções completa para um ativo

**Path Parameters:**
- `ticker`: Símbolo do ticker

**Query Parameters:**
- `expiration` (optional): Filtrar por data de vencimento (YYYY-MM-DD)

**Response 200:**
```json
{
  "ticker": "PETR4",
  "underlying_price": 28.35,
  "expirations": [
    "2025-02-21",
    "2025-03-21",
    "2025-04-18",
    "2025-05-16",
    "2025-06-20",
    "2025-07-18"
  ],
  "strikes": [22.50, 23.50, 24.50, 25.50, 26.50, 27.50, 28.50, 29.50, 30.50],
  "calls": [
    {
      "ticker": "PETR4",
      "strike": 28.50,
      "expiration": "2025-02-21",
      "option_type": "CALL",
      "premium": 1.25,
      "bid": 1.23,
      "ask": 1.27,
      "intrinsic_value": 0.0,
      "time_value": 1.25,
      "delta": 0.50,
      "gamma": 0.05,
      "theta": -0.06,
      "vega": 0.13,
      "rho": 0.01,
      "volume": 5000,
      "open_interest": 15000,
      "implied_volatility": 0.32,
      "dte": 30
    }
  ],
  "puts": [
    {
      "ticker": "PETR4",
      "strike": 28.50,
      "expiration": "2025-02-21",
      "option_type": "PUT",
      "premium": 1.30,
      "bid": 1.28,
      "ask": 1.32,
      "intrinsic_value": 0.15,
      "time_value": 1.15,
      "delta": -0.50,
      "gamma": 0.05,
      "theta": -0.07,
      "vega": 0.13,
      "rho": -0.01,
      "volume": 4500,
      "open_interest": 12000,
      "implied_volatility": 0.30,
      "dte": 30
    }
  ],
  "timestamp": "2025-01-22T10:45:00Z"
}
```

### GET /api/market/options/{ticker}/quote
Cotação de uma opção específica

**Path Parameters:**
- `ticker`: Símbolo do ticker

**Query Parameters:**
- `strike`: Preço de strike (required)
- `expiration`: Data de vencimento YYYY-MM-DD (required)
- `type`: Tipo de opção CALL ou PUT (required)

**Response 200:**
```json
{
  "ticker": "PETR4",
  "strike": 30.00,
  "expiration": "2025-03-21",
  "option_type": "CALL",
  "premium": 0.85,
  "bid": 0.83,
  "ask": 0.87,
  "intrinsic_value": 0.0,
  "time_value": 0.85,
  "delta": 0.30,
  "gamma": 0.04,
  "theta": -0.04,
  "vega": 0.09,
  "rho": 0.01,
  "volume": 3500,
  "open_interest": 10000,
  "implied_volatility": 0.28,
  "dte": 58
}
```

### GET /api/market/options/{ticker}/greeks
Greeks de uma opção específica

**Path Parameters:**
- `ticker`: Símbolo do ticker

**Query Parameters:**
- `strike`: Preço de strike (required)
- `expiration`: Data de vencimento YYYY-MM-DD (required)
- `type`: Tipo de opção CALL ou PUT (required)

**Response 200:**
```json
{
  "ticker": "PETR4",
  "strike": 30.00,
  "expiration": "2025-03-21",
  "option_type": "CALL",
  "delta": 0.30,
  "gamma": 0.04,
  "theta": -0.04,
  "vega": 0.09,
  "rho": 0.01,
  "timestamp": "2025-01-22T10:45:00Z"
}
```

**Greeks Explicados:**
- **Delta**: Sensibilidade do prêmio em relação ao preço do ativo (-1 a 1)
- **Gamma**: Taxa de mudança do delta
- **Theta**: Decaimento temporal do prêmio (por dia)
- **Vega**: Sensibilidade à volatilidade implícita
- **Rho**: Sensibilidade à taxa de juros

### GET /api/market/health
Health check do provedor de dados de mercado

**Response 200:**
```json
{
  "provider": "mock",
  "healthy": true,
  "timestamp": "2025-01-22T10:45:00Z"
}
```

**Response 503 (Unhealthy):**
```json
{
  "provider": "mock",
  "healthy": false,
  "error": "Connection timeout"
}
```

**Nota:** Atualmente utilizando provedor mock para desenvolvimento. Em produção, integrar com provedor real (Yahoo Finance, Alpha Vantage, etc.).

---

## 📝 Resumo por Categoria

| Categoria | Endpoints | Requer Auth |
|-----------|-----------|-------------|
| Health & Info | 2 | ❌ |
| Auth | 6 | Misto |
| Accounts | 5 | ✅ |
| Assets | 5 | ✅ |
| Options | 8 | ✅ |
| Rules | 6 | ✅ |
| Alerts | 9 | ✅ |
| Notifications | 4 | ✅ |
| Workers | 5 | ✅ |
| Rolls | 3 | ✅ |
| Market Data | 5 | ✅ |
| **Total** | **58** | - |

---

## ⚠️ Códigos de Status HTTP

| Código | Significado |
|--------|-------------|
| 200 | Sucesso |
| 201 | Criado com sucesso |
| 401 | Não autenticado |
| 403 | Não autorizado (sem permissão) |
| 404 | Não encontrado |
| 409 | Conflito (ex: email duplicado) |
| 422 | Erro de validação |
| 500 | Erro interno do servidor |
| 503 | Serviço indisponível |

---

## 🔒 Segurança

- **JWT Tokens:** Expiram em 1 hora (access) e 30 dias (refresh)
- **Password:** Mínimo 6 caracteres, hash bcrypt
- **RLS:** Row Level Security no Supabase
- **Ownership:** Todas operações validam posse do recurso

---

## 📚 Exemplos de Uso

### Fluxo Completo: Criar Posição de Opção

```bash
# 1. Registrar
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123","name":"User"}'

# 2. Login
TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123"}' \
  | jq -r '.access_token')

# 3. Criar conta
ACCOUNT=$(curl -X POST http://localhost:8000/api/accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"My Account"}' \
  | jq -r '.account.id')

# 4. Criar ativo
ASSET=$(curl -X POST http://localhost:8000/api/assets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"account_id\":\"$ACCOUNT\",\"ticker\":\"PETR4\"}" \
  | jq -r '.asset.id')

# 5. Criar posição de opção
curl -X POST http://localhost:8000/api/options \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"account_id\":\"$ACCOUNT\",
    \"asset_id\":\"$ASSET\",
    \"side\":\"CALL\",
    \"strategy\":\"COVERED_CALL\",
    \"strike\":100.00,
    \"expiration\":\"2025-03-15\",
    \"quantity\":100,
    \"avg_premium\":2.50
  }"

# 6. Listar posições
curl -X GET http://localhost:8000/api/options \
  -H "Authorization: Bearer $TOKEN"
```

---

**Última atualização:** 2025-01-22
**Versão da API:** 1.0.0
