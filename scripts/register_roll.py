"""
Script para registrar operação de roll de opções via API.

Roll VALE3:
- Recompra: VALEJ640W5 @ R$ 64,00 em 30/10/2025
- Nova venda: VALEK645W1 @ R$ 64,50 em 07/11/2025
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
print(f"Token: {access_token[:20]}...")
print()

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Passo 2: Verificar/Criar conta BTG Pactual
print("2. Verificando conta BTG Pactual...")
accounts_response = requests.get(f"{BASE_URL}/api/accounts", headers=headers)

if accounts_response.status_code != 200:
    print(f"[ERRO] Falha ao listar contas: {accounts_response.status_code}")
    print(accounts_response.text)
    exit(1)

accounts_data = accounts_response.json()

# Se a resposta for uma lista diretamente
if isinstance(accounts_data, list):
    accounts = accounts_data
elif isinstance(accounts_data, dict):
    accounts = accounts_data.get("data", accounts_data.get("accounts", []))
else:
    accounts = []

btg_account = None

for account in accounts:
    if isinstance(account, dict) and account.get("broker") == BROKER:
        btg_account = account
        print(f"[OK] Conta encontrada: {account['name']} ({account['account_number']})")
        break

if not btg_account:
    print("[INFO] Conta BTG não encontrada. Criando...")
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

    btg_account = create_account_response.json()
    print(f"[OK] Conta criada: {btg_account['name']}")

account_id = btg_account["id"]
print()

# Passo 3: Verificar/Criar ativo VALE3
print("3. Verificando ativo VALE3...")
assets_response = requests.get(f"{BASE_URL}/api/assets", headers=headers)

if assets_response.status_code != 200:
    print(f"[ERRO] Falha ao listar ativos: {assets_response.status_code}")
    exit(1)

assets_data = assets_response.json()

# Se a resposta for uma lista diretamente
if isinstance(assets_data, list):
    assets = assets_data
elif isinstance(assets_data, dict):
    assets = assets_data.get("data", assets_data.get("assets", []))
else:
    assets = []

vale3_asset = None

for asset in assets:
    if isinstance(asset, dict) and asset.get("ticker") == "VALE3":
        vale3_asset = asset
        print(f"[OK] Ativo encontrado: VALE3")
        break

if not vale3_asset:
    print("[INFO] Ativo VALE3 não encontrado. Criando...")
    create_asset_response = requests.post(
        f"{BASE_URL}/api/assets",
        headers=headers,
        json={
            "account_id": account_id,
            "ticker": "VALE3",
            "quantity": QUANTITY,
            "average_price": 60.00  # Preço médio estimado
        }
    )

    if create_asset_response.status_code not in [200, 201]:
        print(f"[ERRO] Falha ao criar ativo: {create_asset_response.status_code}")
        print(create_asset_response.text)
        exit(1)

    vale3_asset = create_asset_response.json()
    print(f"[OK] Ativo criado: VALE3 com {QUANTITY} ações")

asset_id = vale3_asset["id"]
print()

# Passo 4: Registrar FECHAMENTO da posição antiga (Recompra)
print("4. Registrando RECOMPRA (fechamento) - VALEJ640W5...")
print("   Strike: R$ 64,00")
print("   Vencimento: 30/10/2025")
print("   Preço: R$ 64,00")

close_option_response = requests.post(
    f"{BASE_URL}/api/options",
    headers=headers,
    json={
        "account_id": account_id,
        "asset_id": asset_id,
        "ticker": "VALE3",
        "strike": 64.00,
        "expiration": "2025-10-30",
        "option_type": "call",
        "quantity": QUANTITY,
        "entry_price": 64.00,
        "current_price": 64.00,
        "status": "closed",
        "position_type": "short"  # Era venda coberta
    }
)

if close_option_response.status_code not in [200, 201]:
    print(f"[AVISO] Falha ao registrar recompra: {close_option_response.status_code}")
    print(close_option_response.text)
else:
    print(f"[OK] Recompra registrada com sucesso!")

print()

# Passo 5: Registrar ABERTURA da nova posição (Nova venda)
print("5. Registrando NOVA VENDA - VALEK645W1...")
print("   Strike: R$ 64,50")
print("   Vencimento: 07/11/2025")
print("   Preço: R$ 64,50")

open_option_response = requests.post(
    f"{BASE_URL}/api/options",
    headers=headers,
    json={
        "account_id": account_id,
        "asset_id": asset_id,
        "ticker": "VALE3",
        "strike": 64.50,
        "expiration": "2025-11-07",
        "option_type": "call",
        "quantity": QUANTITY,
        "entry_price": 64.50,
        "current_price": 64.50,
        "status": "active",
        "position_type": "short"  # Venda coberta
    }
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
print(f"Conta: {btg_account['name']}")
print(f"Ativo: VALE3 ({QUANTITY} ações)")
print()
print("Operação de Roll:")
print(f"  Recompra: VALEJ640W5 @ R$ 64,00 (30/10/2025)")
print(f"  Nova venda: VALEK645W1 @ R$ 64,50 (07/11/2025)")
print()
print(f"Resultado do roll: R$ {(64.50 - 64.00) * QUANTITY:.2f}")
print("=" * 60)
