"""Script para verificar posições de opções no banco."""
import sys
import os

# Adicionar o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Configurar Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DB_SCHEMA = os.getenv("DB_SCHEMA", "monitoring_options_operations")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 80)
print("POSIÇÕES DE OPÇÕES NO BANCO")
print(f"Schema: {DB_SCHEMA}")
print("=" * 80)
print()

# Buscar posições (com schema correto)
result = supabase.schema(DB_SCHEMA).table('option_positions').select('*').order('created_at').execute()

print(f"Total de posições: {len(result.data)}")
print()

# Buscar assets para mapear IDs para tickers
assets_result = supabase.schema(DB_SCHEMA).table('assets').select('*').execute()
assets_map = {asset['id']: asset['ticker'] for asset in assets_result.data}

print("Assets encontrados:")
for asset_id, ticker in assets_map.items():
    print(f"  {ticker}: {asset_id}")
print()

print("=" * 80)
print()

for i, pos in enumerate(result.data, 1):
    ticker = assets_map.get(pos['asset_id'], 'Desconhecido')

    print(f"Posição {i}: {ticker}")
    print(f"  ID: {pos['id']}")
    print(f"  Side: {pos['side']}")
    print(f"  Strategy: {pos['strategy']}")
    print(f"  Strike: R$ {pos['strike']:.2f}")
    print(f"  Expiration: {pos['expiration']}")
    print(f"  Quantity: {pos['quantity']}")
    print(f"  Avg Premium: R$ {pos['avg_premium']:.2f}")
    print(f"  Status: {pos['status']}")
    print(f"  Created: {pos['created_at']}")

    if pos.get('notes'):
        print(f"  Notes: {pos['notes']}")

    # Calcular prêmio recebido
    qty_shares = pos['quantity'] if pos['quantity'] > 100 else pos['quantity'] * 100
    premium = pos['avg_premium'] * qty_shares
    print(f"  Prêmio recebido: R$ {premium:.2f}")

    print("-" * 80)

print()
print("ANÁLISE POR ATIVO")
print("=" * 80)
print()

# Agrupar por asset
by_asset = {}
for pos in result.data:
    asset_id = pos['asset_id']
    ticker = assets_map.get(asset_id, 'Desconhecido')

    if ticker not in by_asset:
        by_asset[ticker] = {
            'positions': [],
            'total_premium': 0,
            'open_count': 0,
            'closed_count': 0,
        }

    qty_shares = pos['quantity'] if pos['quantity'] > 100 else pos['quantity'] * 100
    premium = pos['avg_premium'] * qty_shares

    by_asset[ticker]['positions'].append(pos)
    by_asset[ticker]['total_premium'] += premium

    if pos['status'] == 'OPEN':
        by_asset[ticker]['open_count'] += 1
    else:
        by_asset[ticker]['closed_count'] += 1

for ticker, data in by_asset.items():
    print(f"{ticker}:")
    print(f"  Total de posições: {len(data['positions'])}")
    print(f"  Abertas: {data['open_count']}")
    print(f"  Fechadas: {data['closed_count']}")
    print(f"  Prêmio total recebido: R$ {data['total_premium']:.2f}")
    print()

    for pos in data['positions']:
        status_icon = "🟢" if pos['status'] == 'OPEN' else "🔴"
        print(f"    {status_icon} {pos['side']} Strike R$ {pos['strike']:.2f} - Venc: {pos['expiration']} - Status: {pos['status']}")

    print()

print("=" * 80)
