"""
Script corrigido para registrar operação de roll de opções via API.

Roll VALE3:
- Fechar posição antiga: VALEJ640W5 @ R$ 64,00 em 30/10/2025
- Abrir nova posição: VALEK645W1 @ R$ 64,50 em 07/11/2025
"""
import requests
import json
from datetime import datetime

# Configurações
BASE_URL = "http://localhost:8000"
EMAIL = "rubenilson12@gmail.com"
PASSWORD = "123456"
BROKER = "BTG Pactual"
QUANTITY = 700

print("=" * 60)
print("REGISTRO DE ROLL - VALE3")
print("=" * 60)
print()

# Passo 1: Login
print("1. Fazendo login...")
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": EMAIL, "password": PASSWORD}
)

if login_response.status_code != 200:
    print(f"[ERRO] Login falhou: {login_response.status_code}")
    print(login_response.text)
    exit(1)

login_data = login_response.json()
access_token = login_data.get("access_token")
print(f"[OK] Login bem-sucedido!")
print()

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Passo 2: Buscar conta BTG Pactual
print("2. Buscando conta BTG Pactual...")
accounts_response = requests.get(f"{BASE_URL}/api/accounts", headers=headers)

if accounts_response.status_code != 200:
    print(f"[ERRO] Falha ao listar contas: {accounts_response.status_code}")
    print(accounts_response.text)
    exit(1)

accounts_data = accounts_response.json()
accounts = accounts_data if isinstance(accounts_data, list) else accounts_data.get("data", accounts_data.get("accounts", []))

account_id = None
if accounts and len(accounts) > 0:
    account_id = accounts[0]["id"]
    print(f"[OK] Conta encontrada: {accounts[0].get('name', 'Sem nome')}")
    print(f"ID: {account_id}")

if not account_id:
    print(f"[INFO] Conta não encontrada. Criando conta BTG Pactual...")
    create_account_response = requests.post(
        f"{BASE_URL}/api/accounts",
        headers=headers,
        json={
            "name": "BTG Pactual - Principal",
            "broker": BROKER,
            "account_number": "BTG-001"
        }
    )

    if create_account_response.status_code not in [200, 201]:
        print(f"[ERRO] Falha ao criar conta: {create_account_response.status_code}")
        print(create_account_response.text)
        exit(1)

    account_id = create_account_response.json()["id"]
    print(f"[OK] Conta criada: {account_id}")

print()

# Passo 3: Buscar ou criar ativo VALE3
print("3. Buscando ativo VALE3...")
assets_response = requests.get(f"{BASE_URL}/api/assets", headers=headers)

if assets_response.status_code != 200:
    print(f"[ERRO] Falha ao listar ativos: {assets_response.status_code}")
    exit(1)

assets_data = assets_response.json()
assets = assets_data if isinstance(assets_data, list) else assets_data.get("data", assets_data.get("assets", []))

# Procurar VALE3 nos ativos existentes
asset_id = None
for asset in assets:
    if isinstance(asset, dict) and asset.get("ticker") == "VALE3":
        asset_id = asset["id"]
        print(f"[OK] Ativo VALE3 encontrado: {asset_id}")
        break

if not asset_id:
    print("[INFO] Ativo VALE3 não encontrado. Criando...")
    create_asset_response = requests.post(
        f"{BASE_URL}/api/assets",
        headers=headers,
        json={
            "account_id": account_id,
            "ticker": "VALE3"
        }
    )

    if create_asset_response.status_code not in [200, 201]:
        print(f"[ERRO] Falha ao criar ativo: {create_asset_response.status_code}")
        print(create_asset_response.text)
        exit(1)

    asset_id = create_asset_response.json()["id"]
    print(f"[OK] Ativo VALE3 criado: {asset_id}")

print()

# Passo 4: Criar posição de ações (equity) se não existir
print("4. Verificando posição de ações VALE3...")
equity_response = requests.get(
    f"{BASE_URL}/api/equities",
    headers=headers
)

has_equity = False
if equity_response.status_code == 200:
    equities = equity_response.json()
    for eq in equities:
        if eq.get("asset_id") == asset_id:
            has_equity = True
            print(f"[OK] Posição de ações encontrada: {eq.get('quantity')} ações")
            break

if not has_equity:
    print(f"[INFO] Criando posição de {QUANTITY} ações VALE3...")
    equity_create = requests.post(
        f"{BASE_URL}/api/equities",
        headers=headers,
        json={
            "account_id": account_id,
            "asset_id": asset_id,
            "quantity": QUANTITY,
            "avg_price": 60.00
        }
    )

    if equity_create.status_code in [200, 201]:
        print(f"[OK] Posição de ações criada!")
    else:
        print(f"[AVISO] Não foi possível criar posição de ações: {equity_create.status_code}")

print()

# Passo 5: Registrar NOVA VENDA - VALEK645W1
print("5. Registrando NOVA VENDA COBERTA - VALEK645W1...")
print("   Ticker: VALE3")
print("   Strike: R$ 64,50")
print("   Vencimento: 07/11/2025")
print("   Prêmio: R$ 0,52 por ação")
print("   Quantidade: 700 contratos")
print("   Tipo: CALL")
print("   Estratégia: COVERED_CALL (venda coberta)")

option_payload = {
    "account_id": account_id,
    "asset_id": asset_id,  # UUID correto do ativo VALE3
    "side": "CALL",
    "strategy": "COVERED_CALL",
    "strike": 64.50,
    "expiration": "2025-11-07",
    "quantity": 700,
    "avg_premium": 0.52,
    "notes": "Roll de VALEJ640W5 (R$64,00) para VALEK645W1 (R$64,50)"
}

print(f"\nPayload da requisição:")
print(json.dumps(option_payload, indent=2))
print()

open_option_response = requests.post(
    f"{BASE_URL}/api/options",
    headers=headers,
    json=option_payload
)

if open_option_response.status_code not in [200, 201]:
    print(f"[ERRO] Falha ao registrar nova venda: {open_option_response.status_code}")
    print(open_option_response.text)
    exit(1)

new_option = open_option_response.json()
print(f"[OK] Nova venda registrada com sucesso!")
print(f"ID da posição: {new_option.get('id')}")
print()

# Resumo
print("=" * 60)
print("ROLL REGISTRADO COM SUCESSO!")
print("=" * 60)
print(f"Conta: {account_id}")
print(f"Ativo VALE3: {asset_id}")
print()
print("Nova Posição:")
print(f"  Estratégia: Venda coberta (COVERED_CALL)")
print(f"  Opção: VALEK645W1")
print(f"  Strike: R$ 64,50")
print(f"  Vencimento: 07/11/2025")
print(f"  Quantidade: 700 contratos")
print(f"  Prêmio recebido: R$ {0.52 * 700:.2f} (R$ 0,52/ação)")
print()
print(f"Resultado potencial:")
print(f"  Prêmio recebido: R$ {0.52 * 700:.2f}")
print(f"  Se exercida em R$ 64,50: Ganho adicional de R$ {(64.50 - 60.00) * 700:.2f}")
print("=" * 60)
