//+------------------------------------------------------------------+
//|                                                   JsonHelper.mqh |
//|                                      Ventry Monitoring Options   |
//|                  Biblioteca para construção de JSON strings      |
//+------------------------------------------------------------------+
#property copyright "Ventry"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Classe auxiliar para construção de JSON                          |
//+------------------------------------------------------------------+
class CJsonHelper
{
public:
    //+------------------------------------------------------------------+
    //| Escapa string para JSON                                         |
    //+------------------------------------------------------------------+
    static string EscapeString(string value)
    {
        string result = value;
        StringReplace(result, "\\", "\\\\");
        StringReplace(result, "\"", "\\\"");
        StringReplace(result, "\n", "\\n");
        StringReplace(result, "\r", "\\r");
        StringReplace(result, "\t", "\\t");
        return result;
    }

    //+------------------------------------------------------------------+
    //| Formata timestamp ISO 8601                                      |
    //+------------------------------------------------------------------+
    static string FormatTimestamp(datetime dt)
    {
        MqlDateTime mdt;
        TimeToStruct(dt, mdt);

        return StringFormat("%04d-%02d-%02dT%02d:%02d:%02dZ",
            mdt.year, mdt.mon, mdt.day,
            mdt.hour, mdt.min, mdt.sec);
    }

    //+------------------------------------------------------------------+
    //| Cria JSON de heartbeat                                          |
    //+------------------------------------------------------------------+
    static string CreateHeartbeat(string terminal_id, string account_number,
                                  string broker, int build)
    {
        string json = "{";
        json += "\"terminal_id\":\"" + EscapeString(terminal_id) + "\",";
        json += "\"account_number\":\"" + EscapeString(account_number) + "\",";
        json += "\"broker\":\"" + EscapeString(broker) + "\",";
        json += "\"build\":" + IntegerToString(build) + ",";
        json += "\"timestamp\":\"" + FormatTimestamp(TimeCurrent()) + "\"";
        json += "}";

        return json;
    }

    //+------------------------------------------------------------------+
    //| Inicia JSON de quotes                                           |
    //+------------------------------------------------------------------+
    static string StartQuotesJson(string terminal_id, string account_number)
    {
        string json = "{";
        json += "\"terminal_id\":\"" + EscapeString(terminal_id) + "\",";
        json += "\"account_number\":\"" + EscapeString(account_number) + "\",";
        json += "\"quotes\":[";

        return json;
    }

    //+------------------------------------------------------------------+
    //| Adiciona uma quote ao JSON (sem array wrapper)                  |
    //+------------------------------------------------------------------+
    static string AddQuote(string symbol, double bid, double ask,
                          double last, long volume)
    {
        string json = "{";
        json += "\"symbol\":\"" + EscapeString(symbol) + "\",";
        json += "\"bid\":" + DoubleToString(bid, 8) + ",";
        json += "\"ask\":" + DoubleToString(ask, 8) + ",";
        json += "\"last\":" + DoubleToString(last, 8) + ",";
        json += "\"volume\":" + IntegerToString(volume) + ",";
        json += "\"ts\":\"" + FormatTimestamp(TimeCurrent()) + "\"";
        json += "}";

        return json;
    }

    //+------------------------------------------------------------------+
    //| Finaliza JSON de quotes                                         |
    //+------------------------------------------------------------------+
    static string EndQuotesJson()
    {
        return "]}";
    }

    //+------------------------------------------------------------------+
    //| Cria JSON de execution report                                   |
    //+------------------------------------------------------------------+
    static string CreateExecutionReport(string command_id, string status,
                                       string order_id, double filled_qty,
                                       double avg_price, string message)
    {
        string json = "{";
        json += "\"command_id\":\"" + EscapeString(command_id) + "\",";
        json += "\"status\":\"" + EscapeString(status) + "\",";
        json += "\"order_id\":\"" + EscapeString(order_id) + "\",";
        json += "\"filled_qty\":" + DoubleToString(filled_qty, 2) + ",";
        json += "\"avg_price\":" + DoubleToString(avg_price, 8) + ",";
        json += "\"ts\":\"" + FormatTimestamp(TimeCurrent()) + "\",";
        json += "\"message\":\"" + EscapeString(message) + "\"";
        json += "}";

        return json;
    }

    //+------------------------------------------------------------------+
    //| Extrai valor string de JSON simples (busca por chave)           |
    //+------------------------------------------------------------------+
    static string ExtractStringValue(string json, string key)
    {
        string search = "\"" + key + "\":\"";
        int start = StringFind(json, search);

        if(start == -1)
            return "";

        start += StringLen(search);
        int end = StringFind(json, "\"", start);

        if(end == -1)
            return "";

        return StringSubstr(json, start, end - start);
    }

    //+------------------------------------------------------------------+
    //| Extrai valor inteiro de JSON simples (busca por chave)          |
    //+------------------------------------------------------------------+
    static int ExtractIntValue(string json, string key)
    {
        string search = "\"" + key + "\":";
        int start = StringFind(json, search);

        if(start == -1)
            return 0;

        start += StringLen(search);

        // Pula espaços em branco
        while(start < StringLen(json) &&
              (StringGetCharacter(json, start) == ' ' ||
               StringGetCharacter(json, start) == '\t'))
        {
            start++;
        }

        // Encontra o fim do número
        int end = start;
        while(end < StringLen(json))
        {
            ushort ch = StringGetCharacter(json, end);
            if((ch < '0' || ch > '9') && ch != '-')
                break;
            end++;
        }

        if(end <= start)
            return 0;

        string value = StringSubstr(json, start, end - start);
        return (int)StringToInteger(value);
    }

    //+------------------------------------------------------------------+
    //| Verifica se JSON contém array vazio para determinada chave      |
    //+------------------------------------------------------------------+
    static bool HasEmptyArray(string json, string key)
    {
        string search = "\"" + key + "\":[]";
        return (StringFind(json, search) != -1);
    }

    //+------------------------------------------------------------------+
    //| Inicia JSON de option quotes                                    |
    //+------------------------------------------------------------------+
    static string StartOptionQuotesJson(string terminal_id, string account_number)
    {
        string json = "{";
        json += "\"terminal_id\":\"" + EscapeString(terminal_id) + "\",";
        json += "\"account_number\":\"" + EscapeString(account_number) + "\",";
        json += "\"option_quotes\":[";

        return json;
    }

    //+------------------------------------------------------------------+
    //| Adiciona uma option quote ao JSON                               |
    //+------------------------------------------------------------------+
    static string AddOptionQuote(string mt5_symbol, double bid, double ask,
                                 double last, long volume)
    {
        string json = "{";
        json += "\"mt5_symbol\":\"" + EscapeString(mt5_symbol) + "\",";
        json += "\"bid\":" + DoubleToString(bid, 8) + ",";
        json += "\"ask\":" + DoubleToString(ask, 8) + ",";
        json += "\"last\":" + DoubleToString(last, 8) + ",";
        json += "\"volume\":" + IntegerToString(volume) + ",";
        json += "\"ts\":\"" + FormatTimestamp(TimeCurrent()) + "\"";
        json += "}";

        return json;
    }

    //+------------------------------------------------------------------+
    //| Finaliza JSON de option quotes                                  |
    //+------------------------------------------------------------------+
    static string EndOptionQuotesJson()
    {
        return "]}";
    }
};
