"""Valida dados em cache do MT5 Bridge após teste de simulação."""
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from MT5.storage import get_latest_quote, get_last_heartbeat

print("=" * 60)
print("VALIDACAO DE CACHE MT5 BRIDGE")
print("=" * 60)
print()

# Verificar heartbeat
print("=== HEARTBEAT ===")
hb = get_last_heartbeat("MT5-TEST-12345")
if hb:
    print(f"[OK] Terminal ID: {hb.get('terminal_id')}")
    print(f"[OK] Broker: {hb.get('broker')}")
    print(f"[OK] Account: {hb.get('account_number')}")
    print(f"[OK] Timestamp: {hb.get('ts')}")
else:
    print("[X] Nenhum heartbeat encontrado!")
print()

# Verificar quote
print("=== QUOTES ===")
q = get_latest_quote("WIN$N", 30)
if q:
    print(f"[OK] Symbol: {q.get('symbol')}")
    print(f"[OK] Bid: {q.get('bid')}")
    print(f"[OK] Ask: {q.get('ask')}")
    print(f"[OK] Last: {q.get('last')}")
    print(f"[OK] Volume: {q.get('volume')}")
    print(f"[OK] Timestamp: {q.get('ts')}")
else:
    print("[X] Nenhuma cotacao encontrada!")
print()

print("=" * 60)
if hb and q:
    print("[OK] VALIDACAO COMPLETA - Dados em cache OK!")
else:
    print("[X] VALIDACAO FALHOU - Dados faltando")
print("=" * 60)
