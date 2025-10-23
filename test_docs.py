"""
Script de teste para verificar se a documentação está funcionando.
"""

import requests
import time
import subprocess
import sys
from colorama import init, Fore, Style

init(autoreset=True)

def print_success(message):
    print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")

def print_error(message):
    print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")

def print_info(message):
    print(f"{Fore.CYAN}ℹ {message}{Style.RESET_ALL}")

def test_documentation():
    """Testa os endpoints de documentação."""

    base_url = "http://localhost:8000"

    tests = [
        {
            "name": "Root endpoint",
            "url": f"{base_url}/",
            "check": lambda r: r.status_code == 200 and "scalar_docs" in r.json()
        },
        {
            "name": "Health check",
            "url": f"{base_url}/health",
            "check": lambda r: r.status_code == 200
        },
        {
            "name": "Scalar documentation",
            "url": f"{base_url}/scalar",
            "check": lambda r: r.status_code == 200 and "Scalar" in r.text or "api-reference" in r.text
        },
        {
            "name": "OpenAPI spec",
            "url": f"{base_url}/api/docs/openapi.json",
            "check": lambda r: r.status_code == 200 and "openapi" in r.json()
        },
    ]

    print_info(f"Testando documentação em {base_url}...\n")

    success_count = 0
    fail_count = 0

    for test in tests:
        try:
            response = requests.get(test["url"], timeout=5)

            if test["check"](response):
                print_success(f"{test['name']}: OK")
                success_count += 1
            else:
                print_error(f"{test['name']}: Falhou na validação")
                fail_count += 1
        except requests.exceptions.ConnectionError:
            print_error(f"{test['name']}: Servidor não está rodando")
            fail_count += 1
        except Exception as e:
            print_error(f"{test['name']}: {str(e)}")
            fail_count += 1

    print(f"\n{'-' * 50}")
    print(f"Resultados: {Fore.GREEN}{success_count} passou{Style.RESET_ALL} | {Fore.RED}{fail_count} falhou{Style.RESET_ALL}")
    print(f"{'-' * 50}\n")

    if success_count == len(tests):
        print_success("Todos os testes de documentação passaram!")
        print_info(f"\nAcesse a documentação em: {Fore.YELLOW}{base_url}/scalar{Style.RESET_ALL}")
        return True
    else:
        print_error("Alguns testes falharam. Verifique se o servidor está rodando.")
        print_info("Execute: python -m app.main")
        return False

if __name__ == "__main__":
    # Instalar colorama se necessário
    try:
        import colorama
    except ImportError:
        print("Instalando colorama...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "colorama", "-q"])
        import colorama
        colorama.init(autoreset=True)

    success = test_documentation()
    sys.exit(0 if success else 1)
