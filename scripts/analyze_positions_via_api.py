"""Script para analisar posições de opções via API."""
import sys
import io
import requests
from typing import Dict, List, Any
from collections import defaultdict
from datetime import datetime

# Configurar encoding para UTF-8 no Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Configuração
BASE_URL = "http://localhost:8000"
EMAIL = "rubenilson12@gmail.com"
PASSWORD = "123456"

def format_brl(value: float) -> str:
    """Formata valor em BRL."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def calculate_premium(position: Dict) -> float:
    """Calcula o prêmio total de uma posição."""
    qty = position.get('quantity', 0)
    qty_shares = qty if qty > 100 else qty * 100
    return position.get('avg_premium', 0) * qty_shares

def main():
    print("=" * 80)
    print("ANÁLISE DE POSIÇÕES DE OPÇÕES - VIA API")
    print("=" * 80)
    print()

    # 1. Login
    print("1. Fazendo login...")
    try:
        login_response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": EMAIL, "password": PASSWORD}
        )
        login_response.raise_for_status()
        token = login_response.json().get("access_token")
        print(f"   ✅ Login realizado com sucesso")
    except Exception as e:
        print(f"   ❌ Erro no login: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 2. Buscar assets
    print("\n2. Buscando assets...")
    try:
        assets_response = requests.get(f"{BASE_URL}/api/assets", headers=headers)
        assets_response.raise_for_status()
        assets_data = assets_response.json()

        # Criar mapa asset_id -> ticker
        asset_map = {}
        if 'assets' in assets_data:
            for asset in assets_data['assets']:
                asset_map[asset['id']] = asset['ticker']

        print(f"   ✅ {len(asset_map)} assets encontrados:")
        for asset_id, ticker in asset_map.items():
            print(f"      - {ticker}: {asset_id[:8]}...")
    except Exception as e:
        print(f"   ❌ Erro ao buscar assets: {e}")
        asset_map = {}

    # 3. Buscar posições
    print("\n3. Buscando posições de opções...")
    try:
        positions_response = requests.get(f"{BASE_URL}/api/options", headers=headers)
        positions_response.raise_for_status()
        positions_data = positions_response.json()

        positions = positions_data.get('positions', [])
        print(f"   ✅ {len(positions)} posições encontradas")
    except Exception as e:
        print(f"   ❌ Erro ao buscar posições: {e}")
        return

    if not positions:
        print("\n⚠️  Nenhuma posição encontrada no sistema")
        return

    print("\n" + "=" * 80)
    print("TODAS AS POSIÇÕES")
    print("=" * 80)
    print()

    # Agrupar por asset
    by_asset: Dict[str, List[Dict]] = defaultdict(list)

    for pos in positions:
        asset_id = pos.get('asset_id', 'unknown')
        ticker = asset_map.get(asset_id, f'Asset-{asset_id[:8]}')
        by_asset[ticker].append(pos)

    # Mostrar todas as posições organizadas por ativo
    for ticker in sorted(by_asset.keys()):
        positions_list = by_asset[ticker]

        print(f"\n{'=' * 80}")
        print(f"ATIVO: {ticker}")
        print(f"{'=' * 80}")
        print(f"Total de posições: {len(positions_list)}")
        print()

        # Ordenar por data de criação
        positions_list.sort(key=lambda p: p.get('created_at', ''))

        total_premium = 0
        total_unrealized_pnl = 0
        open_count = 0
        closed_count = 0

        for i, pos in enumerate(positions_list, 1):
            status = pos.get('status', 'UNKNOWN')
            side = pos.get('side', 'UNKNOWN')
            strategy = pos.get('strategy', 'UNKNOWN')
            strike = pos.get('strike', 0)
            expiration = pos.get('expiration', 'N/A')
            quantity = pos.get('quantity', 0)
            avg_premium = pos.get('avg_premium', 0)
            unrealized_pnl = pos.get('unrealized_pnl', 0)
            created_at = pos.get('created_at', 'N/A')
            notes = pos.get('notes', '')

            # Calcular prêmio
            premium = calculate_premium(pos)
            total_premium += premium
            total_unrealized_pnl += unrealized_pnl

            if status == 'OPEN':
                open_count += 1
                status_icon = "🟢"
            else:
                closed_count += 1
                status_icon = "🔴"

            # Mostrar posição
            print(f"{status_icon} Posição {i}:")
            print(f"   ID: {pos.get('id', 'N/A')[:8]}...")
            print(f"   Status: {status}")
            print(f"   Side: {side}")
            print(f"   Strategy: {strategy}")
            print(f"   Strike: {format_brl(strike)}")
            print(f"   Vencimento: {expiration}")
            print(f"   Quantidade: {quantity}")
            print(f"   Prêmio Médio: {format_brl(avg_premium)}")
            print(f"   Prêmio Total Recebido: {format_brl(premium)}")
            print(f"   P&L Não Realizado: {format_brl(unrealized_pnl)}")
            print(f"   Lucro Total: {format_brl(premium + unrealized_pnl)}")
            print(f"   Criado em: {created_at}")
            if notes:
                print(f"   Notas: {notes}")
            print()

        # Resumo do ativo
        print(f"\n{'-' * 80}")
        print(f"RESUMO - {ticker}")
        print(f"{'-' * 80}")
        print(f"Posições abertas: {open_count}")
        print(f"Posições fechadas: {closed_count}")
        print(f"Prêmio total recebido: {format_brl(total_premium)}")
        print(f"P&L não realizado total: {format_brl(total_unrealized_pnl)}")
        print(f"Lucro total: {format_brl(total_premium + total_unrealized_pnl)}")

        # Se houver múltiplas posições, pode ser uma rolagem
        if len(positions_list) > 1:
            print(f"\n⚠️  ATENÇÃO: {len(positions_list)} posições detectadas para {ticker}")
            print("   Isso pode indicar operações de ROLAGEM.")
            print("   Analise as datas e strikes para identificar os pares de roll.")

        print()

    # Resumo geral
    print("\n" + "=" * 80)
    print("RESUMO GERAL - TODOS OS ATIVOS")
    print("=" * 80)
    print()

    grand_total_premium = 0
    grand_total_unrealized = 0
    grand_total_open = 0
    grand_total_closed = 0

    for ticker, positions_list in by_asset.items():
        total_premium = sum(calculate_premium(p) for p in positions_list)
        total_unrealized = sum(p.get('unrealized_pnl', 0) for p in positions_list)
        open_count = sum(1 for p in positions_list if p.get('status') == 'OPEN')
        closed_count = sum(1 for p in positions_list if p.get('status') != 'OPEN')

        grand_total_premium += total_premium
        grand_total_unrealized += total_unrealized
        grand_total_open += open_count
        grand_total_closed += closed_count

        print(f"{ticker}:")
        print(f"   Posições: {len(positions_list)} ({open_count} abertas, {closed_count} fechadas)")
        print(f"   Prêmio recebido: {format_brl(total_premium)}")
        print(f"   P&L não realizado: {format_brl(total_unrealized)}")
        print(f"   Lucro total: {format_brl(total_premium + total_unrealized)}")
        print()

    print(f"{'-' * 80}")
    print(f"TOTAIS:")
    print(f"   Ativos diferentes: {len(by_asset)}")
    print(f"   Posições totais: {len(positions)} ({grand_total_open} abertas, {grand_total_closed} fechadas)")
    print(f"   Prêmio total recebido: {format_brl(grand_total_premium)}")
    print(f"   P&L não realizado total: {format_brl(grand_total_unrealized)}")
    print(f"   LUCRO TOTAL: {format_brl(grand_total_premium + grand_total_unrealized)}")
    print("=" * 80)

if __name__ == "__main__":
    main()
