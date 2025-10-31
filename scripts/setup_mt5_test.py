"""
Script para configurar e testar a integração MT5.

Este script:
1. Verifica configurações necessárias no .env
2. Sugere configurações se não existirem
3. Testa os endpoints do MT5 Bridge
"""

import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def check_env_config():
    """Verifica configurações MT5 no .env"""
    env_file = backend_dir / ".env"

    required_vars = {
        "MT5_BRIDGE_ENABLED": "true",
        "MT5_BRIDGE_TOKEN": None,  # Deve existir mas não tem valor padrão
        "MARKET_DATA_PROVIDER": "hybrid",
        "MARKET_DATA_HYBRID_FALLBACK": "brapi",
        "MT5_BRIDGE_QUOTE_TTL_SECONDS": "10",
    }

    print("=" * 60)
    print("VERIFICANDO CONFIGURAÇÃO MT5 BRIDGE")
    print("=" * 60)
    print()

    if not env_file.exists():
        print("[X] Arquivo .env nao encontrado!")
        print(f"   Crie o arquivo em: {env_file}")
        print("   Use .env.example como base.")
        return False

    # Ler .env
    env_content = {}
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_content[key.strip()] = value.strip()
    except Exception as e:
        print(f"[X] Erro ao ler .env: {e}")
        return False

    print("[OK] Arquivo .env encontrado")
    print()

    # Verificar variáveis
    missing = []
    suggestions = []

    for var, default in required_vars.items():
        if var not in env_content:
            missing.append(var)
            if default:
                suggestions.append(f"{var}={default}")
            else:
                suggestions.append(f"{var}=<CONFIGURE_AQUI>")
        else:
            value = env_content[var]
            if var == "MT5_BRIDGE_TOKEN" and value in ["", "CHANGE-ME-SET-A-STRONG-TOKEN-HERE"]:
                print(f"[!] {var}: Token precisa ser configurado!")
                print(f"   Valor atual: {value}")
                print(f"   Gere um token forte com:")
                print(f"   python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
                print()
            else:
                print(f"[OK] {var}: {value}")

    print()

    if missing:
        print("[X] Variaveis faltando no .env:")
        for var in missing:
            print(f"   - {var}")
        print()
        print("Adicione ao .env:")
        for suggestion in suggestions:
            print(f"   {suggestion}")
        print()
        return False

    return True


def test_import():
    """Testa importação dos módulos MT5"""
    print("=" * 60)
    print("TESTANDO IMPORTAÇÕES")
    print("=" * 60)
    print()

    try:
        print("Importando MT5.bridge_blueprint...", end=" ")
        from MT5.bridge_blueprint import mt5_bridge_bp
        print("[OK]")

        print("Importando MT5.storage...", end=" ")
        from MT5 import storage
        print("[OK]")

        print("Importando market_data providers...", end=" ")
        from app.services.market_data import market_data_provider
        print("[OK]")

        print()
        print(f"Provider ativo: {market_data_provider.__class__.__name__}")
        print()

        return True
    except Exception as e:
        print(f"[X] ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_next_steps():
    """Imprime próximos passos"""
    print("=" * 60)
    print("PRÓXIMOS PASSOS")
    print("=" * 60)
    print()
    print("1. Configure o .env com as variáveis MT5 necessárias")
    print()
    print("2. Gere um token forte:")
    print('   python -c "import secrets; print(secrets.token_urlsafe(32))"')
    print()
    print("3. Adicione ao .env:")
    print("   MT5_BRIDGE_ENABLED=true")
    print("   MT5_BRIDGE_TOKEN=<seu-token-aqui>")
    print("   MARKET_DATA_PROVIDER=hybrid")
    print()
    print("4. Teste a integração:")
    print("   # Terminal 1: Iniciar backend")
    print("   python -m app.main")
    print()
    print("   # Terminal 2: Testar com script")
    print("   set MT5_BRIDGE_TOKEN=<seu-token-aqui>")
    print("   python scripts/test_mt5_bridge.py")
    print()
    print("5. Ver documentação completa:")
    print("   backend/MT5/INSTALLATION.md")
    print("   backend/MT5/TESTING.md")
    print()


def main():
    print()
    print(">>> SETUP E TESTE MT5 BRIDGE <<<")
    print()

    # Verificar config
    config_ok = check_env_config()

    if not config_ok:
        print()
        print("[!] Configuracao incompleta!")
        print_next_steps()
        return 1

    # Testar imports
    import_ok = test_import()

    if not import_ok:
        print()
        print("[X] Erro ao importar modulos!")
        return 1

    # Tudo OK
    print("=" * 60)
    print("[OK] CONFIGURACAO OK!")
    print("=" * 60)
    print()
    print("Próximos passos:")
    print()
    print("1. Iniciar backend:")
    print("   python -m app.main")
    print()
    print("2. Em outro terminal, testar:")
    print(f"   set MT5_BRIDGE_TOKEN={os.getenv('MT5_BRIDGE_TOKEN', '<token>')}")
    print("   python scripts/test_mt5_bridge.py")
    print()
    print("3. Ver mais em: backend/MT5/TESTING.md")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
