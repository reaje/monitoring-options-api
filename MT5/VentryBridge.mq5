//+------------------------------------------------------------------+
//|                                                 VentryBridge.mq5 |
//|                                      Ventry Monitoring Options   |
//|          Expert Advisor para integração com backend via HTTP     |
//+------------------------------------------------------------------+
#property copyright "Ventry"
#property link      "https://github.com/ventry"
#property version   "1.00"
#property description "Bridge entre MT5 e Backend Ventry para monitoramento de opções"
#property strict

// Incluir bibliotecas auxiliares
#include "HttpClient.mqh"
#include "JsonHelper.mqh"

#include <Trade/Trade.mqh>  // Execução de ordens

//--- Inputs configuráveis
//=== Configurações do Servidor ===
input string    InpBackendUrl = "http://127.0.0.1:8000";     // URL do Backend (sem / no final)
input string    InpAuthToken = "";                            // Bearer Token para autenticação

//=== Identificação do Terminal ===
input string    InpTerminalId = "MT5-WS-01";                 // ID único deste terminal
input string    InpBroker = "XP";                             // Nome do broker

//=== Símbolos para Monitorar ===
input string    InpSymbolsList = "PETR4,VALE3,BBAS3";        // Lista de símbolos de ações (separados por vírgula)
input string    InpOptionsSymbolsList = "";                   // Lista de símbolos de opções (separados por vírgula) - MT5 format

//=== Intervalos de Envio (em segundos) ===
input int       InpHeartbeatInterval = 60;                    // Intervalo de heartbeat (60s)
input int       InpQuotesInterval = 5;                        // Intervalo de envio de cotações (5s)
input int       InpCommandsPollInterval = 10;                 // Intervalo de polling de comandos (10s)

//=== Configurações Avançadas ===
input bool      InpEnableLogging = true;                      // Habilitar logs detalhados
input int       InpHttpTimeout = 5000;                        // Timeout HTTP em ms (5000ms)


//=== Descoberta automática de símbolos de opções ===
input bool      InpAutoDiscoverOptionSymbols = true;           // Tentar descobrir símbolos de opções no MarketWatch
input int       InpMaxAutoOptionSymbols = 200;                  // Limite máximo ao auto-descobrir (evitar listas enormes)

//--- Variáveis globais
CHttpClient*    g_http_client = NULL;
string          g_symbols[];
int             g_symbols_count = 0;
string          g_option_symbols[];
int             g_option_symbols_count = 0;
datetime        g_last_heartbeat = 0;
datetime        g_last_quotes = 0;
datetime        g_last_option_quotes = 0;
datetime        g_last_commands_poll = 0;
string          g_account_number;
CTrade          g_trade;  // handler de ordens de mercado

int             g_terminal_build;
bool            g_initialized = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("=== Ventry Bridge EA - Inicializando ===");

    // Validar configurações
    if(!ValidateSettings())
    {
        Print("ERRO: Configurações inválidas!");
        return INIT_PARAMETERS_INCORRECT;
    }

    // Obter informações da conta
    g_account_number = IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN));
    g_terminal_build = (int)TerminalInfoInteger(TERMINAL_BUILD);

    Print("Terminal ID: ", InpTerminalId);
    Print("Conta: ", g_account_number);
    Print("Broker: ", InpBroker);
    Print("Build: ", g_terminal_build);
    Print("Backend URL: ", InpBackendUrl);

    // Criar cliente HTTP
    g_http_client = new CHttpClient(InpBackendUrl, InpAuthToken, InpHttpTimeout);

    // Processar lista de símbolos de ações
    if(!ParseSymbols())
    {
        Print("ERRO: Falha ao processar lista de símbolos de ações!");
        return INIT_FAILED;
    }

    Print("Símbolos de ações monitorados: ", g_symbols_count);
    for(int i = 0; i < g_symbols_count; i++)
    {
        Print("  - ", g_symbols[i]);
    }

    // Processar lista de símbolos de opções (opcional)
    if(InpOptionsSymbolsList != "")
    {
        if(!ParseOptionSymbols())
        {
            Print("AVISO: Falha ao processar lista de símbolos de opções (continuando sem elas)");
        }
        else
        {
            Print("Símbolos de opções monitorados: ", g_option_symbols_count);
            for(int i = 0; i < g_option_symbols_count; i++)
            {
                Print("  - ", g_option_symbols[i]);
            }
        }
    }


    // Auto-descoberta de símbolos de opções, se não houver lista explícita
    if(g_option_symbols_count == 0 && InpAutoDiscoverOptionSymbols)
    {
        if(AutoDiscoverOptionSymbols())
        {
            Print("Opções auto-descobertas: ", g_option_symbols_count);
            int show = MathMin(g_option_symbols_count, 20);
            for(int i = 0; i < show; i++)
                Print("  - ", g_option_symbols[i]);
            if(g_option_symbols_count > show)
                Print("  ... (", g_option_symbols_count - show, " restantes)");
        }
        else
        {
            Print("AVISO: Não foi possível auto-descobrir símbolos de opções (MarketWatch vazio ou sem padrões reconhecidos)");
        }
    }

    // Configurar timer
    int timer_interval = MathMin(InpHeartbeatInterval,
                        MathMin(InpQuotesInterval, InpCommandsPollInterval));
    timer_interval = MathMax(1, timer_interval); // Mínimo 1 segundo

    if(!EventSetTimer(timer_interval))
    {
        Print("ERRO: Falha ao configurar timer!");
        return INIT_FAILED;
    }

    // Enviar heartbeat inicial
    SendHeartbeat();

    g_initialized = true;
    Print("=== Ventry Bridge EA - Inicializado com sucesso ===");
    Print("IMPORTANTE: Certifique-se de que a URL está nas URLs permitidas!");
    Print("Ferramentas -> Opções -> Expert Advisors -> WebRequest");

    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("=== Ventry Bridge EA - Finalizando ===");
    Print("Motivo: ", GetDeinitReason(reason));

    // Remover timer
    EventKillTimer();

    // Liberar recursos
    if(g_http_client != NULL)
    {
        delete g_http_client;
        g_http_client = NULL;
    }

    ArrayFree(g_symbols);
    ArrayFree(g_option_symbols);
    g_initialized = false;

    Print("=== Ventry Bridge EA - Finalizado ===");
}

//+------------------------------------------------------------------+
//| Timer function                                                   |
//+------------------------------------------------------------------+
void OnTimer()
{
    if(!g_initialized)
        return;

    datetime now = TimeCurrent();

    // Heartbeat
    if(now - g_last_heartbeat >= InpHeartbeatInterval)
    {
        SendHeartbeat();
        g_last_heartbeat = now;
    }

    // Quotes (ações)
    if(now - g_last_quotes >= InpQuotesInterval)
    {
        SendQuotes();
        g_last_quotes = now;
    }

    // Option quotes (se houver símbolos de opções configurados)
    if(g_option_symbols_count > 0 && now - g_last_option_quotes >= InpQuotesInterval)
    {
        SendOptionQuotes();
        g_last_option_quotes = now;
    }

    // Commands polling
    if(now - g_last_commands_poll >= InpCommandsPollInterval)
    {
        PollCommands();
        g_last_commands_poll = now;
    }
}

//+------------------------------------------------------------------+
//| Valida as configurações de entrada                              |
//+------------------------------------------------------------------+
bool ValidateSettings()
{
    if(InpBackendUrl == "")
    {
        Print("ERRO: URL do backend não configurada!");
        return false;
    }

    if(InpAuthToken == "")
    {
        Print("AVISO: Token de autenticação não configurado!");
        Print("O backend pode rejeitar as requisições!");
    }

    if(InpTerminalId == "")
    {
        Print("ERRO: Terminal ID não configurado!");
        return false;
    }

    if(InpSymbolsList == "")
    {
        Print("ERRO: Lista de símbolos vazia!");
        return false;
    }

    if(InpHeartbeatInterval < 10)
    {
        Print("AVISO: Intervalo de heartbeat muito baixo (mínimo recomendado: 10s)");
    }

    if(InpQuotesInterval < 1)
    {
        Print("ERRO: Intervalo de quotes deve ser >= 1 segundo!");
        return false;
    }

    return true;
}

//+------------------------------------------------------------------+
//| Processa a lista de símbolos do input                           |
//+------------------------------------------------------------------+
bool ParseSymbols()
{
    string symbols_str = InpSymbolsList;
    StringTrimLeft(symbols_str);
    StringTrimRight(symbols_str);

    if(symbols_str == "")
        return false;

    // Contar símbolos (separados por vírgula)
    int count = 1;
    for(int i = 0; i < StringLen(symbols_str); i++)
    {
        if(StringGetCharacter(symbols_str, i) == ',')
            count++;
    }

    ArrayResize(g_symbols, count);
    g_symbols_count = 0;

    // Extrair cada símbolo
    int start = 0;
    for(int i = 0; i <= StringLen(symbols_str); i++)
    {
        if(i == StringLen(symbols_str) || StringGetCharacter(symbols_str, i) == ',')
        {
            string symbol = StringSubstr(symbols_str, start, i - start);
            StringTrimLeft(symbol);
            StringTrimRight(symbol);

            if(symbol != "")
            {
                g_symbols[g_symbols_count] = symbol;
                g_symbols_count++;
            }

            start = i + 1;
        }
    }

    return (g_symbols_count > 0);
}

//+------------------------------------------------------------------+
//| Envia heartbeat para o backend                                  |
//+------------------------------------------------------------------+
void SendHeartbeat()
{
    if(g_http_client == NULL)
        return;

    string json = CJsonHelper::CreateHeartbeat(
        InpTerminalId,
        g_account_number,
        InpBroker,
        g_terminal_build
    );

    if(InpEnableLogging)
        Print("Enviando heartbeat...");

    string response;
    bool success = g_http_client.Post("/api/mt5/heartbeat", json, response);

    if(success)
    {
        if(InpEnableLogging)
            Print("Heartbeat enviado com sucesso. Resposta: ", response);
    }
    else
    {
        Print("ERRO: Falha ao enviar heartbeat!");
    }
}

//+------------------------------------------------------------------+
//| Envia cotações para o backend                                   |
//+------------------------------------------------------------------+
void SendQuotes()
{
    if(g_http_client == NULL || g_symbols_count == 0)
        return;

    // Iniciar JSON
    string json = CJsonHelper::StartQuotesJson(InpTerminalId, g_account_number);

    int quotes_added = 0;

    // Adicionar cotação de cada símbolo
    for(int i = 0; i < g_symbols_count; i++)
    {
        string symbol = g_symbols[i];
        MqlTick tick;

        // Obter último tick do símbolo
        if(!SymbolInfoTick(symbol, tick))
        {
            if(InpEnableLogging)
                Print("AVISO: Não foi possível obter tick de ", symbol);
            continue;
        }

        // Obter volume do tick
        long volume = (long)tick.volume;

        // Adicionar vírgula se não for o primeiro
        if(quotes_added > 0)
            json += ",";

        // Adicionar quote
        json += CJsonHelper::AddQuote(
            symbol,
            tick.bid,
            tick.ask,
            tick.last,
            volume
        );

        quotes_added++;
    }

    // Finalizar JSON
    json += CJsonHelper::EndQuotesJson();

    if(quotes_added == 0)
    {
        if(InpEnableLogging)
            Print("AVISO: Nenhuma cotação disponível para enviar");
        return;
    }

    if(InpEnableLogging)
        Print("Enviando ", quotes_added, " cotações...");

    string response;
    bool success = g_http_client.Post("/api/mt5/quotes", json, response);

    if(success)
    {
        if(InpEnableLogging)
            Print("Cotações enviadas com sucesso. Resposta: ", response);
    }
    else
    {
        Print("ERRO: Falha ao enviar cotações!");
    }
}

//+------------------------------------------------------------------+
//| Faz polling de comandos pendentes                               |
//+------------------------------------------------------------------+
void PollCommands()
{
    if(g_http_client == NULL)
        return;

    string endpoint = "/api/mt5/commands?terminal_id=" + InpTerminalId +
                     "&account_number=" + g_account_number;

    string response;
    bool success = g_http_client.Get(endpoint, response);

    if(!success)
    {
        if(InpEnableLogging)
            Print("AVISO: Falha ao fazer polling de comandos");
        return;
    }

    // Verificar se há comandos
    if(CJsonHelper::HasEmptyArray(response, "commands"))
    {
        // Sem comandos pendentes
        return;
    }

    // Localizar array de comandos
    string marker = "\"commands\":";
    int pos = StringFind(response, marker);
    if(pos == -1)
        return;
    pos += StringLen(marker);
    // Avane7ar ate9 '[']
    while(pos < StringLen(response) && StringGetCharacter(response, pos) != '[') pos++;
    if(pos >= StringLen(response)) return;
    // Entrar no array
    pos++;

    int depth = 0;
    int start = -1;
    for(int i = pos; i < StringLen(response); i++)
    {
        ushort ch = StringGetCharacter(response, i);
        if(ch == '{')
        {
            if(depth == 0)
                start = i;
            depth++;
        }
        else if(ch == '}')
        {
            depth--;
            if(depth == 0 && start != -1)
            {
                int end = i;
                string cmd_json = StringSubstr(response, start, end - start + 1);
                ProcessCommand(cmd_json);
                start = -1;
            }
        }
        else if(ch == ']')
        {
            // Fim do array
            break;
        }
    }
}

//+------------------------------------------------------------------+
//| Processa a lista de símbolos de opções do input                 |
//+------------------------------------------------------------------+
bool ParseOptionSymbols()
{
    string symbols_str = InpOptionsSymbolsList;
    StringTrimLeft(symbols_str);
    StringTrimRight(symbols_str);

    if(symbols_str == "")
        return false;

    // Contar símbolos (separados por vírgula)
    int count = 1;
    for(int i = 0; i < StringLen(symbols_str); i++)
    {
        if(StringGetCharacter(symbols_str, i) == ',')
            count++;
    }

    ArrayResize(g_option_symbols, count);
    g_option_symbols_count = 0;

    // Extrair cada símbolo
    int start = 0;
    for(int i = 0; i <= StringLen(symbols_str); i++)
    {
        if(i == StringLen(symbols_str) || StringGetCharacter(symbols_str, i) == ',')
        {
            string symbol = StringSubstr(symbols_str, start, i - start);
            StringTrimLeft(symbol);
            StringTrimRight(symbol);

            if(symbol != "")
            {
                g_option_symbols[g_option_symbols_count] = symbol;
                g_option_symbols_count++;
            }

            start = i + 1;
        }
    }

    return (g_option_symbols_count > 0);
}

//+------------------------------------------------------------------+
//| Utilitários de descoberta automática de opções                   |
//+------------------------------------------------------------------+
string StripTrailingDigits(string s)
{
    int n = StringLen(s);
    while(n > 0)
    {
        ushort ch = StringGetCharacter(s, n-1);
        if(ch >= '0' && ch <= '9') n--; else break;
    }
    return StringSubstr(s, 0, n);
}

bool IsOptionSeriesLetter(ushort ch)
{
    // Séries CALL: A-L, PUT: M-X
    return ((ch >= 'A' && ch <= 'L') || (ch >= 'M' && ch <= 'X'));
}

bool StartsWith(string s, string prefix)
{
    int lp = StringLen(prefix);
    if(StringLen(s) < lp) return false;
    return StringSubstr(s, 0, lp) == prefix;
}

bool ContainsSymbol(string &arr[], int count, string sym)
{
    for(int i = 0; i < count; i++) if(arr[i] == sym) return true;
    return false;
}

bool AutoDiscoverOptionSymbols()
{
    // Descobre símbolos no MarketWatch que pareçam opções dos ativos-base monitorados
    int total = SymbolsTotal(true); // apenas MarketWatch
    if(total <= 0) return false;

    // Construir lista de bases (ticker sem sufixo numérico)
    string bases[];
    int bases_count = 0;
    ArrayResize(bases, g_symbols_count);
    for(int i = 0; i < g_symbols_count; i++)
    {
        bases[i] = StripTrailingDigits(g_symbols[i]);
        bases_count++;
    }

    // Colecionar candidatos
    string found[];
    int found_count = 0;

    for(int i = 0; i < total; i++)
    {
        string sym = SymbolName(i, true);
        if(sym == "") continue;

        // Testar contra cada base
        for(int b = 0; b < bases_count; b++)
        {
            string base = bases[b];
            if(base == "") continue;
            int lb = StringLen(base);
            if(StringLen(sym) <= lb) continue;
            if(!StartsWith(sym, base)) continue;
            ushort ch = StringGetCharacter(sym, lb);
            if(!IsOptionSeriesLetter(ch)) continue;

            if(!ContainsSymbol(found, found_count, sym))
            {
                // Limite de proteção
                if(found_count >= InpMaxAutoOptionSymbols)
                {
                    Print("AVISO: Limite de auto-descoberta atingido (", InpMaxAutoOptionSymbols, ")");
                    break;
                }
                ArrayResize(found, found_count + 1);
                found[found_count] = sym;
                found_count++;
            }
        }
        if(found_count >= InpMaxAutoOptionSymbols) break;
    }

    if(found_count == 0) return false;

    // Atualizar lista global
    ArrayFree(g_option_symbols);
    g_option_symbols_count = 0;
    ArrayResize(g_option_symbols, found_count);
    for(int j = 0; j < found_count; j++)
    {
        g_option_symbols[j] = found[j];
        g_option_symbols_count++;
    }

    return (g_option_symbols_count > 0);
}


//+------------------------------------------------------------------+
//| Envia cotações de opções para o backend                         |
//+------------------------------------------------------------------+
void SendOptionQuotes()
{
    if(g_http_client == NULL || g_option_symbols_count == 0)
        return;

    // Iniciar JSON
    string json = CJsonHelper::StartOptionQuotesJson(InpTerminalId, g_account_number);

    int quotes_added = 0;

    // Adicionar cotação de cada símbolo de opção
    for(int i = 0; i < g_option_symbols_count; i++)
    {
        string symbol = g_option_symbols[i];
        MqlTick tick;

        // Garantir que o símbolo esteja selecionado (adicionado ao MarketWatch)
        if(!SymbolSelect(symbol, true))
        {
            if(InpEnableLogging)
                Print("AVISO: SymbolSelect falhou para opção ", symbol, ". Adicione ao MarketWatch.");
            continue;
        }

        // Obter último tick do símbolo
        if(!SymbolInfoTick(symbol, tick))
        {
            if(InpEnableLogging)
                Print("AVISO: Tick indisponível para opção ", symbol);
            continue;
        }

        // Obter volume do tick
        long volume = (long)tick.volume;

        // Adicionar vírgula se não for o primeiro
        if(quotes_added > 0)
            json += ",";

        // Adicionar option quote (usa mt5_symbol como identificador)
        json += CJsonHelper::AddOptionQuote(symbol, tick.bid, tick.ask, tick.last, volume);

        quotes_added++;
    }

    // Finalizar JSON
    json += CJsonHelper::EndOptionQuotesJson();

    if(quotes_added == 0)
    {
        if(InpEnableLogging)
            Print("AVISO: Nenhuma cotação de opção disponível para enviar");
        return;
    }

    if(InpEnableLogging)
        Print("Enviando ", quotes_added, " cotações de opções...");

    string response;
    bool success = g_http_client.Post("/api/mt5/option_quotes", json, response);

    if(success)
    {
        if(InpEnableLogging)
            Print("Cotações de opções enviadas com sucesso. Resposta: ", response);
    }
    else
    {
        Print("ERRO: Falha ao enviar cotações de opções!");
    }
}

//+------------------------------------------------------------------+
//| Processamento de comandos MT5                                   |
//+------------------------------------------------------------------+

bool SendExecutionReportSimple(string command_id, string status, string order_id, double filled_qty, double avg_price, string message)
{
    if(g_http_client == NULL) return false;
    string json = CJsonHelper::CreateExecutionReport(command_id, status, order_id, filled_qty, avg_price, message);
    string resp;
    bool ok = g_http_client.Post("/api/mt5/execution_report", json, resp);
    if(InpEnableLogging)
        Print("ExecutionReport[", status, "] -> ", ok, ", resp=", resp);
    return ok;
}

string EncodeOptionSymbol(string ticker, double strike, string option_type, string expiration)
{
    // Remove sufixo numérico do ticker (VALE3 -> VALE)
    string base = ticker;
    while(StringLen(base) > 0 && StringGetCharacter(base, StringLen(base)-1) >= '0' && StringGetCharacter(base, StringLen(base)-1) <= '9')
        base = StringSubstr(base, 0, StringLen(base)-1);

    // Extrair mês de YYYY-MM-DD
    int month = 1;
    if(StringLen(expiration) >= 7)
        month = (int)StringToInteger(StringSubstr(expiration, 5, 2));

    // Letra do mês
    string type = StringToLower(option_type);
    ushort code_char;
    if(type == "call")
        code_char = (ushort)('A' + (month - 1));
    else
        code_char = (ushort)('M' + (month - 1));

    // Strike code (heurística similar ao backend)
    int strike_code = (strike < 10.0) ? (int)MathRound(strike * 100.0) : (int)MathRound(strike * 2.0);

    return base + (string)CharToString(code_char) + IntegerToString(strike_code);
}

bool ExecuteLeg(string command_id, string leg_json, string &order_id, double &filled_qty, double &avg_price, string &err)
{
    order_id = ""; filled_qty = 0; avg_price = 0.0; err = "";
    if(leg_json == "") { err = "leg vazio"; return false; }

    string ticker = CJsonHelper::ExtractStringValue(leg_json, "ticker");
    double strike = CJsonHelper::ExtractDoubleValue(leg_json, "strike");
    string option_type = CJsonHelper::ExtractStringValue(leg_json, "option_type");
    string expiration = CJsonHelper::ExtractStringValue(leg_json, "expiration");
    int quantity = CJsonHelper::ExtractIntValue(leg_json, "quantity");
    string action = CJsonHelper::ExtractStringValue(leg_json, "action");

    if(ticker == "" || strike <= 0 || expiration == "" || quantity <= 0) { err = "dados insuficientes na leg"; return false; }

    string symbol = EncodeOptionSymbol(ticker, strike, option_type, expiration);

    if(!SymbolSelect(symbol, true)) { err = "SymbolSelect falhou: " + symbol; return false; }

    MqlTick tick; if(!SymbolInfoTick(symbol, tick)) { err = "Tick indisponível para " + symbol; return false; }

    // Volume em contratos (assume 1 contrato = 1 lote)
    double volume = (double)quantity;

    bool ok = false;
    if(action == "BUY_TO_CLOSE")
        ok = g_trade.Buy(volume, symbol);
    else if(action == "SELL_TO_OPEN")
        ok = g_trade.Sell(volume, symbol);
    else { err = "Ação desconhecida: " + action; return false; }

    if(!ok)
    {
        err = g_trade.ResultRetcodeDescription();
        return false;
    }

    order_id = IntegerToString((long)g_trade.ResultOrder());
    avg_price = g_trade.ResultPrice();
    filled_qty = volume;

    return true;
}

void ProcessRollCommand(string cmd_json, string cmd_id)
{
    // Executa perna de fechamento e abertura em sequência
    string leg_close = CJsonHelper::ExtractObject(cmd_json, "close_leg");
    string leg_open = CJsonHelper::ExtractObject(cmd_json, "open_leg");

    string order_id; double filled; double price; string err;

    if(!ExecuteLeg(cmd_id, leg_close, order_id, filled, price, err))
    {
        SendExecutionReportSimple(cmd_id, "REJECTED", "", 0.0, 0.0, "close_leg: " + err);
        return;
    }

    // Reportar sucesso da primeira perna (parcial)
    SendExecutionReportSimple(cmd_id, "PARTIAL", order_id, filled, price, "close_leg ok");

    if(!ExecuteLeg(cmd_id, leg_open, order_id, filled, price, err))
    {
        SendExecutionReportSimple(cmd_id, "FAILED", "", 0.0, 0.0, "open_leg: " + err);
        return;
    }

    // Ambas pernas concluídas
    SendExecutionReportSimple(cmd_id, "FILLED", order_id, filled, price, "");
}

void ProcessCommand(string cmd_json)
{
    string cmd_id = CJsonHelper::ExtractStringValue(cmd_json, "id");
    string type = CJsonHelper::ExtractStringValue(cmd_json, "type");
    if(cmd_id == "" || type == "") return;

    // Notificar aceitação para evitar redespacho
    SendExecutionReportSimple(cmd_id, "ACCEPTED", "", 0.0, 0.0, "");

    if(type == "ROLL_POSITION")
    {
        ProcessRollCommand(cmd_json, cmd_id);
    }
    else
    {
        // Tipo não suportado
        SendExecutionReportSimple(cmd_id, "REJECTED", "", 0.0, 0.0, "tipo não suportado: " + type);
    }
}


//+------------------------------------------------------------------+
//| Retorna descrição do motivo de deinicialização                  |
//+------------------------------------------------------------------+
string GetDeinitReason(int reason)
{
    switch(reason)
    {
        case REASON_PROGRAM:     return "Expert Advisor parado pelo usuário";
        case REASON_REMOVE:      return "Expert Advisor removido do gráfico";
        case REASON_RECOMPILE:   return "Expert Advisor recompilado";
        case REASON_CHARTCHANGE: return "Mudança de período/símbolo do gráfico";
        case REASON_CHARTCLOSE:  return "Gráfico fechado";
        case REASON_PARAMETERS:  return "Parâmetros alterados";
        case REASON_ACCOUNT:     return "Conta alterada";
        case REASON_TEMPLATE:    return "Template aplicado";
        case REASON_INITFAILED:  return "Falha na inicialização";
        case REASON_CLOSE:       return "Terminal fechado";
        default:                 return "Motivo desconhecido: " + IntegerToString(reason);
    }
}
//+------------------------------------------------------------------+
