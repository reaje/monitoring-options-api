"""
Script para adicionar decorators OpenAPI em todos os endpoints.
"""

import re
from pathlib import Path

# Mapeamento de rotas para tags
ROUTE_TAGS = {
    "accounts.py": "Accounts",
    "assets.py": "Assets",
    "options.py": "Options",
    "rules.py": "Rules",
    "alerts.py": "Alerts",
    "notifications.py": "Notifications",
    "workers.py": "Workers",
    "rolls.py": "Rolls",
    "market_data.py": "Market Data",
}

# Mapeamento de métodos HTTP para descrições padrão
METHOD_DESCRIPTIONS = {
    "get": {
        "/": "List all {resource}",
        "/<": "Get {resource} by ID",
        "/active": "List active {resource}",
        "/pending": "List pending {resource}",
        "/statistics": "Get {resource} statistics",
    },
    "post": {
        "/": "Create new {resource}",
        "/send": "Send {resource}",
        "/test": "Test {resource}",
        "/toggle": "Toggle {resource}",
        "/close": "Close {resource}",
        "/retry": "Retry {resource}",
        "/trigger": "Trigger {resource}",
    },
    "put": {
        "/<": "Update {resource} by ID",
    },
    "patch": {
        "/<": "Partially update {resource} by ID",
    },
    "delete": {
        "/<": "Delete {resource} by ID",
    },
}

def add_openapi_import(content, filename):
    """Adiciona import do openapi se não existir."""
    if "from sanic_ext import openapi" in content:
        return content

    # Encontra a linha após os imports do sanic
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('from sanic import'):
            lines.insert(i + 1, 'from sanic_ext import openapi')
            return '\n'.join(lines)

    return content

def get_resource_name(filename):
    """Extrai o nome do recurso do nome do arquivo."""
    name = filename.replace('.py', '').replace('_', ' ')
    return name.title()

def get_summary(method, path, resource):
    """Gera summary baseado no método e path."""
    method_lower = method.lower()

    # Verifica cada padrão
    for pattern, desc in METHOD_DESCRIPTIONS.get(method_lower, {}).items():
        if pattern in path:
            return desc.format(resource=resource.lower())

    # Fallback
    return f"{method.upper()} {resource}"

def add_decorators_to_endpoint(content, bp_name):
    """Adiciona decorators OpenAPI aos endpoints."""
    tag = ROUTE_TAGS.get(bp_name.split('.')[0] + '.py', "API")

    # Padrão para encontrar definições de endpoint
    pattern = r'(@' + bp_name.split('_')[0] + r'_bp\.(get|post|put|patch|delete)\(["\']([^"\']+)["\']\)\s*\n)((?:@\w+.*\n)*)(async def \w+)'

    def add_decorators(match):
        route_dec = match.group(1)  # @bp.get("/path")
        method = match.group(2)     # get, post, etc
        path = match.group(3)        # /path
        existing_decs = match.group(4)  # decorators existentes
        func_def = match.group(5)    # async def name

        # Se já tem openapi.tag, pula
        if '@openapi.tag' in existing_decs:
            return match.group(0)

        # Determina se precisa de autenticação
        needs_auth = '@require_auth' in existing_decs

        # Gera decorators
        decorators = f'@openapi.tag("{tag}")\n'

        # Summary baseado no método e path
        resource = tag.lower()
        summary = get_summary(method, path, resource)
        decorators += f'@openapi.summary("{summary}")\n'

        # Secured se tem @require_auth
        if needs_auth:
            decorators += '@openapi.secured("BearerAuth")\n'

        # Response codes padrão
        decorators += f'@openapi.response(200, description="Success")\n'
        if needs_auth:
            decorators += f'@openapi.response(401, description="Not authenticated")\n'

        if method in ['post', 'put', 'patch']:
            decorators += f'@openapi.response(422, description="Validation error")\n'

        if method == 'delete':
            decorators += f'@openapi.response(404, description="Not found")\n'

        return route_dec + decorators + existing_decs + func_def

    return re.sub(pattern, add_decorators, content)

def process_file(filepath):
    """Processa um arquivo de rotas."""
    print(f"Processando {filepath.name}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Adiciona import
    content = add_openapi_import(content, filepath.name)

    # Adiciona decorators
    bp_name = filepath.stem
    content = add_decorators_to_endpoint(content, bp_name)

    # Salva
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✓ {filepath.name} processado")

def main():
    """Processa todos os arquivos de rotas."""
    routes_dir = Path(__file__).parent / "app" / "routes"

    # Arquivos já processados (auth e parcialmente accounts/market_data)
    skip_files = {"__init__.py", "auth.py"}

    # Processa cada arquivo
    for filepath in routes_dir.glob("*.py"):
        if filepath.name in skip_files:
            print(f"Pulando {filepath.name} (já processado)")
            continue

        try:
            process_file(filepath)
        except Exception as e:
            print(f"  ✗ Erro em {filepath.name}: {e}")

    print("\n✓ Processamento concluído!")

if __name__ == "__main__":
    main()
