"""
Script para verificar se o Scalar está configurado corretamente.
"""

import requests
import sys

def verificar():
    print("=" * 60)
    print("VERIFICAÇÃO DA DOCUMENTAÇÃO SCALAR")
    print("=" * 60)
    print()

    try:
        # Teste 1: Servidor está rodando?
        print("✓ Testando se o servidor está rodando...")
        response = requests.get("http://localhost:8000/", timeout=3)

        if response.status_code == 200:
            print("  ✓ Servidor está rodando!")
            data = response.json()

            # Teste 2: Tem scalar_docs?
            print("\n✓ Verificando se scalar_docs está configurado...")
            if "scalar_docs" in data:
                print(f"  ✓ scalar_docs encontrado: {data['scalar_docs']}")

                # Teste 3: Endpoint /scalar funciona?
                print("\n✓ Testando endpoint /scalar...")
                scalar_response = requests.get("http://localhost:8000/scalar", timeout=3)

                if scalar_response.status_code == 200:
                    if "Scalar" in scalar_response.text or "api-reference" in scalar_response.text:
                        print("  ✓ Endpoint /scalar está funcionando!")
                        print()
                        print("=" * 60)
                        print("✅ TUDO FUNCIONANDO!")
                        print("=" * 60)
                        print()
                        print("Acesse a documentação em:")
                        print("  👉 http://localhost:8000/scalar")
                        print()
                        return True
                    else:
                        print("  ✗ Endpoint retornou HTML mas sem Scalar")
                else:
                    print(f"  ✗ Endpoint retornou erro {scalar_response.status_code}")
            else:
                print("  ✗ scalar_docs NÃO encontrado")
                print()
                print("=" * 60)
                print("❌ SERVIDOR PRECISA SER REINICIADO")
                print("=" * 60)
                print()
                print("O código do Scalar foi adicionado, mas o servidor")
                print("que está rodando não tem essas mudanças.")
                print()
                print("SOLUÇÃO:")
                print("1. Pare o servidor atual (Ctrl+C no terminal)")
                print("2. Execute: python -m app.main")
                print("3. Execute este script novamente")
                print()
                return False
        else:
            print(f"  ✗ Servidor retornou erro {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("  ✗ Não foi possível conectar ao servidor")
        print()
        print("=" * 60)
        print("❌ SERVIDOR NÃO ESTÁ RODANDO")
        print("=" * 60)
        print()
        print("SOLUÇÃO:")
        print("1. Abra um terminal")
        print("2. Execute: cd backend")
        print("3. Execute: python -m app.main")
        print("4. Aguarde 'Server started successfully'")
        print("5. Execute este script novamente")
        print()
        return False

    except Exception as e:
        print(f"  ✗ Erro inesperado: {e}")
        return False

    return False

if __name__ == "__main__":
    sucesso = verificar()
    sys.exit(0 if sucesso else 1)
