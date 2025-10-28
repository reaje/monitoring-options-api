//+------------------------------------------------------------------+
//|                                                   HttpClient.mqh |
//|                                      Ventry Monitoring Options   |
//|                          Biblioteca para requisições HTTP/HTTPS  |
//+------------------------------------------------------------------+
#property copyright "Ventry"
#property version   "1.00"
#property strict

//+------------------------------------------------------------------+
//| Classe para realizar requisições HTTP                            |
//+------------------------------------------------------------------+
class CHttpClient
{
private:
    string            m_base_url;
    string            m_auth_token;
    int               m_timeout;

public:
    //+------------------------------------------------------------------+
    //| Construtor                                                       |
    //+------------------------------------------------------------------+
    CHttpClient(string base_url, string auth_token, int timeout = 5000)
    {
        m_base_url = base_url;
        m_auth_token = auth_token;
        m_timeout = timeout;
    }

    //+------------------------------------------------------------------+
    //| POST request                                                     |
    //+------------------------------------------------------------------+
    bool Post(string endpoint, string json_data, string &response)
    {
        string url = m_base_url + endpoint;
        string headers = "Content-Type: application/json\r\n";

        if(m_auth_token != "")
        {
            headers += "Authorization: Bearer " + m_auth_token + "\r\n";
        }

        char post_data[];
        char result_data[];
        string result_headers;

        // Converter string para array de bytes
        int data_len = StringToCharArray(json_data, post_data, 0, WHOLE_ARRAY, CP_UTF8) - 1;

        ResetLastError();
        int res = WebRequest(
            "POST",
            url,
            headers,
            m_timeout,
            post_data,
            result_data,
            result_headers
        );

        if(res == -1)
        {
            int error = GetLastError();
            Print("WebRequest error: ", error, " - ", ErrorDescription(error));
            Print("URL: ", url);

            if(error == 4060)
            {
                Print("ERRO: URL não está na lista de URLs permitidas!");
                Print("Adicione a URL nas configurações do MT5:");
                Print("Ferramentas -> Opções -> Expert Advisors -> ");
                Print("Marque 'Permitir WebRequest para as seguintes URLs' e adicione: ", m_base_url);
            }

            return false;
        }

        // HTTP status codes: 200-299 são sucesso
        if(res < 200 || res >= 300)
        {
            Print("HTTP error: ", res);
            if(ArraySize(result_data) > 0)
            {
                response = CharArrayToString(result_data, 0, WHOLE_ARRAY, CP_UTF8);
                Print("Response: ", response);
            }
            return false;
        }

        // Converter resposta para string
        if(ArraySize(result_data) > 0)
        {
            response = CharArrayToString(result_data, 0, WHOLE_ARRAY, CP_UTF8);
        }

        return true;
    }

    //+------------------------------------------------------------------+
    //| GET request                                                      |
    //+------------------------------------------------------------------+
    bool Get(string endpoint, string &response)
    {
        string url = m_base_url + endpoint;
        string headers = "";

        if(m_auth_token != "")
        {
            headers = "Authorization: Bearer " + m_auth_token + "\r\n";
        }

        char post_data[];
        char result_data[];
        string result_headers;

        ResetLastError();
        int res = WebRequest(
            "GET",
            url,
            headers,
            m_timeout,
            post_data,
            result_data,
            result_headers
        );

        if(res == -1)
        {
            int error = GetLastError();
            Print("WebRequest error: ", error, " - ", ErrorDescription(error));
            Print("URL: ", url);

            if(error == 4060)
            {
                Print("ERRO: URL não está na lista de URLs permitidas!");
                Print("Adicione a URL nas configurações do MT5:");
                Print("Ferramentas -> Opções -> Expert Advisors -> ");
                Print("Marque 'Permitir WebRequest para as seguintes URLs' e adicione: ", m_base_url);
            }

            return false;
        }

        if(res < 200 || res >= 300)
        {
            Print("HTTP error: ", res);
            if(ArraySize(result_data) > 0)
            {
                response = CharArrayToString(result_data, 0, WHOLE_ARRAY, CP_UTF8);
                Print("Response: ", response);
            }
            return false;
        }

        if(ArraySize(result_data) > 0)
        {
            response = CharArrayToString(result_data, 0, WHOLE_ARRAY, CP_UTF8);
        }

        return true;
    }

private:
    //+------------------------------------------------------------------+
    //| Retorna descrição do erro                                       |
    //+------------------------------------------------------------------+
    string ErrorDescription(int error_code)
    {
        switch(error_code)
        {
            case 4060: return "URL não permitida - Configure em Ferramentas->Opções->Expert Advisors";
            case 4014: return "Função desabilitada";
            case 5203: return "Erro ao copiar dados";
            default:   return "Código: " + IntegerToString(error_code);
        }
    }
};
