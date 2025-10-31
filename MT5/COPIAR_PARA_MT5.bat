@echo off
REM ========================================================================
REM Script para copiar VentryBridge EA para o MetaTrader 5
REM ========================================================================

echo.
echo ========================================================================
echo Ventry Bridge - Instalacao no MetaTrader 5
echo ========================================================================
echo.

REM Diretorio do Terminal MT5 (encontrado nos erros de compilacao)
set MT5_DIR=C:\Users\ruben\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts

REM Verificar se o diretorio existe
if not exist "%MT5_DIR%" (
    echo ERRO: Diretorio do MT5 nao encontrado!
    echo Caminho esperado: %MT5_DIR%
    echo.
    echo Por favor, verifique o caminho correto do seu MT5 e edite este script.
    echo.
    pause
    exit /b 1
)

echo Diretorio do MT5 encontrado: %MT5_DIR%
echo.

REM Copiar arquivos
echo Copiando arquivos para o MT5...
echo.

copy /Y "VentryBridge.mq5" "%MT5_DIR%\VentryBridge.mq5"
if errorlevel 1 (
    echo ERRO ao copiar VentryBridge.mq5
    pause
    exit /b 1
)
echo [OK] VentryBridge.mq5

copy /Y "HttpClient.mqh" "%MT5_DIR%\HttpClient.mqh"
if errorlevel 1 (
    echo ERRO ao copiar HttpClient.mqh
    pause
    exit /b 1
)
echo [OK] HttpClient.mqh

copy /Y "JsonHelper.mqh" "%MT5_DIR%\JsonHelper.mqh"
if errorlevel 1 (
    echo ERRO ao copiar JsonHelper.mqh
    pause
    exit /b 1
)
echo [OK] JsonHelper.mqh

echo.
echo ========================================================================
echo Arquivos copiados com sucesso!
echo ========================================================================
echo.
echo Proximos passos:
echo.
echo 1. Abra o MetaEditor (F4 no MT5)
echo 2. Navegue ate: Experts ^> VentryBridge.mq5
echo 3. Compile o arquivo (F7)
echo 4. Arraste o EA para um grafico no MT5
echo 5. Configure os parametros
echo.
echo Documentacao completa em: COMPILACAO_CORRIGIDA.md
echo.
pause
