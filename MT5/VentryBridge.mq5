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

//--- Inputs configuráveis
//=== Configurações do Servidor ===
input string    InpBackendUrl = "http://localhost:8000";     // URL do Backend (sem / no final)
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

    // Verificar se há comandos (Fase 1: sempre retorna array vazio)
    if(CJsonHelper::HasEmptyArray(response, "commands"))
    {
        // Sem comandos pendentes
        return;
    }

    if(InpEnableLogging)
        Print("Comandos recebidos: ", response);

    // TODO: Fase 3 - Processar comandos recebidos
    // Por enquanto, apenas loga
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

        // Obter último tick do símbolo
        if(!SymbolInfoTick(symbol, tick))
        {
            if(InpEnableLogging)
                Print("AVISO: Não foi possível obter tick de opção ", symbol);
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
