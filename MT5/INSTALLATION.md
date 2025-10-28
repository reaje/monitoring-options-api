# Instalação e Configuração do Ventry Bridge EA

Este guia explica como instalar e configurar o Expert Advisor (EA) Ventry Bridge para integração entre MetaTrader 5 e o backend Ventry.

## 📋 Requisitos

- **MetaTrader 5** instalado e configurado
- **Conta ativa** no broker conectada ao MT5
- **Backend Ventry** rodando (padrão: http://localhost:8000)
- **Token de autenticação** configurado no backend

---

## 🚀 Instalação Rápida

### 1. Copiar Arquivos para o MT5

Existem duas formas de fazer isso:

#### Opção A: Via Explorador de Arquivos do Windows

1. Abra o MetaTrader 5
2. Pressione `Ctrl + Shift + D` ou vá em **Arquivo → Abrir Pasta de Dados**
3. Navegue até a pasta `MQL5/Experts/`
4. Crie uma pasta chamada `Ventry` (se não existir)
5. Copie os seguintes arquivos deste repositório:

```
Copiar de: backend/MT5/
Para: <DataFolder>/MQL5/Experts/Ventry/

Arquivos:
- VentryBridge.mq5
- Include/HttpClient.mqh
- Include/JsonHelper.mqh
```

#### Opção B: Via MetaEditor

1. Abra o MetaEditor (pressione F4 no MT5)
2. No Navegador, clique com botão direito em **Experts**
3. Selecione **Create → Folder** e nomeie como `Ventry`
4. Clique com botão direito na pasta `Ventry` → **Open Folder**
5. Copie os arquivos para esta pasta
6. No MetaEditor, clique com botão direito na pasta `Ventry` → **Refresh**

### 2. Compilar o Expert Advisor

1. No MetaEditor, abra o arquivo `VentryBridge.mq5`
2. Pressione **F7** ou clique no botão **Compile**
3. Verifique se não há erros na aba **Toolbox → Errors**
4. Se a compilação for bem-sucedida, aparecerá: `0 error(s), 0 warning(s)`

### 3. Configurar URLs Permitidas (IMPORTANTE!)

**Este passo é OBRIGATÓRIO para que o EA funcione!**

1. No MetaTrader 5, vá em **Ferramentas → Opções**
2. Aba **Expert Advisors**
3. Marque a opção: **☑ Permitir WebRequest para as seguintes URLs**
4. Clique no botão **Adicionar**
5. Digite a URL do seu backend (exemplos):
   - Desenvolvimento local: `http://localhost:8000`
   - Produção: `https://api.ventry.com.br`
6. Clique **OK** para salvar

**Nota:** Você pode adicionar múltiplas URLs se necessário.

---

## ⚙️ Configuração do Backend

Antes de iniciar o EA, configure o backend:

### 1. Editar arquivo `.env`

```bash
cd backend
nano .env  # ou use seu editor preferido
```

### 2. Configurar variáveis do MT5 Bridge

```bash
# Habilitar o bridge
MT5_BRIDGE_ENABLED=true

# Token de autenticação (gere um token forte!)
MT5_BRIDGE_TOKEN=seu-token-secreto-aqui-abc123xyz

# (Opcional) Whitelist de IPs permitidos
MT5_BRIDGE_ALLOWED_IPS=127.0.0.1,192.168.1.100

# TTL para cotações (segundos)
MT5_BRIDGE_QUOTE_TTL_SECONDS=10

# TTL para comandos (segundos)
MT5_BRIDGE_COMMAND_TTL_SECONDS=60

# Configurar provider híbrido (usa MT5 quando disponível, senão fallback)
MARKET_DATA_PROVIDER=hybrid
MARKET_DATA_HYBRID_FALLBACK=brapi
```

### 3. Reiniciar o backend

```bash
python -m app.main
```

Verifique se o servidor iniciou e está escutando em http://localhost:8000

---

## 🎯 Anexar o EA ao Gráfico

### 1. Abrir gráfico de qualquer ativo

No MT5, abra um gráfico de qualquer símbolo (exemplo: PETR4).

### 2. Anexar o Expert Advisor

- Vá em **Navegador → Expert Advisors → Ventry → VentryBridge**
- Arraste o EA para o gráfico **OU**
- Clique duplo no EA

### 3. Configurar Parâmetros

Na janela de configuração que abrir, configure:

#### **Configurações do Servidor**

| Parâmetro | Descrição | Exemplo |
|-----------|-----------|---------|
| `InpBackendUrl` | URL do backend (sem / no final) | `http://localhost:8000` |
| `InpAuthToken` | Token Bearer para autenticação | `seu-token-secreto-aqui-abc123xyz` |

#### **Identificação do Terminal**

| Parâmetro | Descrição | Exemplo |
|-----------|-----------|---------|
| `InpTerminalId` | ID único deste terminal | `MT5-WS-01` |
| `InpBroker` | Nome do broker | `XP`, `Clear`, `Rico` |

#### **Símbolos para Monitorar**

| Parâmetro | Descrição | Exemplo |
|-----------|-----------|---------|
| `InpSymbolsList` | Lista de símbolos (separados por vírgula) | `PETR4,VALE3,BBAS3` |

**Importante:** Use os símbolos exatamente como aparecem no Market Watch do seu broker!

#### **Intervalos de Envio**

| Parâmetro | Descrição | Padrão | Recomendação |
|-----------|-----------|--------|--------------|
| `InpHeartbeatInterval` | Intervalo de heartbeat (segundos) | 60 | 30-120s |
| `InpQuotesInterval` | Intervalo de envio de cotações (segundos) | 5 | 1-10s |
| `InpCommandsPollInterval` | Intervalo de polling de comandos (segundos) | 10 | 5-30s |

#### **Configurações Avançadas**

| Parâmetro | Descrição | Padrão |
|-----------|-----------|--------|
| `InpEnableLogging` | Habilitar logs detalhados | `true` |
| `InpHttpTimeout` | Timeout HTTP em milissegundos | 5000 |

### 4. Habilitar AutoTrading

1. Certifique-se de que o botão **AutoTrading** na barra de ferramentas está VERDE
2. Se estiver vermelho, clique nele para habilitar

### 5. Verificar se o EA está rodando

No gráfico, você deve ver:
- Um smile 😊 no canto superior direito (EA ativo)
- Na aba **Expert**, logs de inicialização:

```
=== Ventry Bridge EA - Inicializando ===
Terminal ID: MT5-WS-01
Conta: 123456
Broker: XP
Build: 3770
Backend URL: http://localhost:8000
Símbolos monitorados: 3
  - PETR4
  - VALE3
  - BBAS3
=== Ventry Bridge EA - Inicializado com sucesso ===
```

---

## ✅ Verificar Funcionamento

### 1. Verificar logs do EA

Na aba **Toolbox → Expert** do MT5, você deve ver mensagens como:

```
Enviando heartbeat...
Heartbeat enviado com sucesso. Resposta: {"status":"ok"}
Enviando 3 cotações...
Cotações enviadas com sucesso. Resposta: {"accepted":3}
```

### 2. Verificar logs do backend

No terminal onde o backend está rodando, você deve ver:

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

### 3. Testar endpoint de saúde

```bash
curl http://localhost:8000/health
```

Deve retornar status "healthy" com database "ok".

### 4. Testar API de cotações

Através do frontend ou diretamente pela API, as cotações devem mostrar `source: "mt5"` quando disponíveis.

---

## 🐛 Troubleshooting

### Problema: "WebRequest error: 4060"

**Causa:** URL não está na lista de URLs permitidas.

**Solução:**
1. Vá em **Ferramentas → Opções → Expert Advisors**
2. Adicione a URL do backend na lista
3. Remova e adicione o EA novamente no gráfico

### Problema: "HTTP error: 401"

**Causa:** Token de autenticação inválido ou não configurado.

**Solução:**
1. Verifique se `MT5_BRIDGE_TOKEN` no backend `.env` está correto
2. Verifique se `InpAuthToken` no EA está igual ao token do backend
3. Reinicie o backend após alterar o `.env`

### Problema: "HTTP error: 403"

**Causa:** Bridge desabilitado no backend ou IP não autorizado.

**Solução:**
1. Verifique se `MT5_BRIDGE_ENABLED=true` no backend `.env`
2. Se usar `MT5_BRIDGE_ALLOWED_IPS`, adicione seu IP à lista
3. Reinicie o backend

### Problema: "Não foi possível obter tick de XXXX"

**Causa:** Símbolo não existe ou não está no Market Watch.

**Solução:**
1. Abra o Market Watch (Ctrl + M)
2. Clique com botão direito → **Symbols**
3. Procure o símbolo e clique em **Show**
4. Verifique se o símbolo está escrito corretamente em `InpSymbolsList`

### Problema: EA não envia nada

**Causa:** AutoTrading desabilitado ou EA não está rodando.

**Solução:**
1. Verifique se o botão AutoTrading está VERDE
2. Verifique se há um smile 😊 no canto do gráfico
3. Verifique os logs na aba Expert por mensagens de erro

---

## 📊 Monitoramento em Produção

### Logs Importantes

**No MT5 (aba Expert):**
- Heartbeat enviado com sucesso → Conexão OK
- Cotações enviadas com sucesso → Dados sendo transmitidos
- Erros HTTP → Problemas de conectividade/autenticação

**No Backend:**
- `mt5.heartbeat` → Terminal está vivo
- `mt5.quotes` → Cotações recebidas
- Erros de autorização → Verificar token/IP

### Métricas Recomendadas

- **Última heartbeat:** Deve ser < 2x InpHeartbeatInterval
- **Última cotação:** Deve ser < 2x InpQuotesInterval
- **Taxa de sucesso HTTP:** Deve ser > 95%
- **Latência média:** Deve ser < 500ms

### Alertas Sugeridos

- ⚠️ Sem heartbeat por > 3 minutos
- ⚠️ Sem cotações por > 1 minuto
- ⚠️ Taxa de erro HTTP > 10%
- 🔴 EA desconectado por > 10 minutos

---

## 🔄 Atualizações

Para atualizar o EA:

1. Baixe a nova versão dos arquivos
2. Substitua os arquivos na pasta do MT5
3. Recompile o EA (F7 no MetaEditor)
4. Remova o EA do gráfico
5. Adicione novamente (as configurações serão mantidas)

---

## 📞 Suporte

Em caso de problemas:

1. Verifique os logs do EA (aba Expert)
2. Verifique os logs do backend
3. Consulte a seção Troubleshooting acima
4. Consulte a documentação completa: `docs/planning/INTEGRACAO_MT5_MQL5_BRIDGE.md`

---

## 🎓 Próximos Passos

Após configurar e validar a Fase 1:

- **Fase 2:** Implementar cotações de opções
- **Fase 3:** Implementar execução de ordens de roll
- **Monitoramento:** Adicionar dashboards com métricas do bridge

Consulte o roadmap completo em `docs/planning/INTEGRACAO_MT5_MQL5_BRIDGE.md`.
