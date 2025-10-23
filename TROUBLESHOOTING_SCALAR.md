# Troubleshooting - Documentação Scalar

## Problema: Endpoint /scalar não funciona

### Solução 1: Reiniciar o Servidor

O servidor precisa ser reiniciado para carregar as mudanças:

**Windows:**
```bash
# 1. Pare o servidor (Ctrl+C no terminal onde está rodando)

# 2. Reinicie o servidor
cd backend
python -m app.main
```

**Verificação:**
```bash
# Teste se o endpoint existe
curl http://localhost:8000/scalar

# Ou acesse no navegador
http://localhost:8000/
```

### Solução 2: Verificar ENABLE_DOCS

Certifique-se que a documentação está habilitada no `.env`:

```bash
# backend/.env
ENABLE_DOCS=true
```

Se estava `false`, mude para `true` e reinicie o servidor.

### Solução 3: Verificar porta

Certifique-se que o servidor está na porta correta:

```bash
# backend/.env
PORT=8000
HOST=0.0.0.0
```

Acesse: `http://localhost:8000/scalar`

### Solução 4: Limpar cache do navegador

1. Abra o navegador no modo anônimo/privado
2. Ou limpe o cache do navegador (Ctrl+Shift+Delete)
3. Tente acessar novamente

### Solução 5: Verificar logs do servidor

Ao acessar `/scalar`, o servidor deve mostrar:

```
GET /scalar 200 OK
```

Se mostrar erro 404, o servidor não foi reiniciado.

### Solução 6: Testar OpenAPI primeiro

Antes de testar o Scalar, verifique se o OpenAPI está funcionando:

```bash
curl http://localhost:8000/api/docs/openapi.json
```

Deve retornar um JSON grande com a especificação OpenAPI.

### Solução 7: Verificar se Sanic-Ext está instalado

```bash
pip install sanic-ext --upgrade
```

Reinicie o servidor após a instalação.

## Checklist de Verificação

- [ ] Servidor foi reiniciado após as mudanças
- [ ] `ENABLE_DOCS=true` no arquivo `.env`
- [ ] Servidor está rodando em `http://localhost:8000`
- [ ] Endpoint `/` retorna `scalar_docs` no JSON
- [ ] Endpoint `/api/docs/openapi.json` retorna JSON válido
- [ ] Cache do navegador foi limpo
- [ ] Sanic-Ext está instalado

## Teste Manual Completo

Execute estes comandos em ordem:

```bash
# 1. Parar servidor atual (se estiver rodando)
# Ctrl+C

# 2. Verificar que as mudanças estão no código
cd backend
grep "scalar" app/main.py
# Deve mostrar várias linhas com "scalar"

# 3. Verificar .env
cat .env | grep ENABLE_DOCS
# Deve mostrar: ENABLE_DOCS=true

# 4. Reinstalar dependências (opcional)
pip install -r requirements.txt

# 5. Iniciar servidor
python -m app.main

# 6. Em outro terminal, testar:
curl http://localhost:8000/
# Deve conter "scalar_docs": "/scalar"

curl http://localhost:8000/scalar
# Deve retornar HTML com "Scalar"

# 7. Abrir no navegador
# http://localhost:8000/scalar
```

## Ainda não funciona?

Se após todas as soluções ainda não funcionar:

1. **Verifique a versão do Python**:
   ```bash
   python --version
   # Deve ser 3.11+
   ```

2. **Verifique erros no console do servidor**:
   - Procure por erros em vermelho
   - Compartilhe os logs de erro

3. **Teste o HTML diretamente**:
   Crie um arquivo `test_scalar.html` com o conteúdo abaixo e abra no navegador:

   ```html
   <!DOCTYPE html>
   <html>
   <head>
       <title>Test Scalar</title>
       <meta charset="utf-8" />
       <meta name="viewport" content="width=device-width, initial-scale=1" />
   </head>
   <body>
       <script
           id="api-reference"
           data-url="http://localhost:8000/api/docs/openapi.json"
       ></script>
       <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
   </body>
   </html>
   ```

   Se funcionar, o problema é no servidor. Se não funcionar, pode ser problema de rede/firewall.

## Alternativa: Usar Swagger UI

Se o Scalar não funcionar, você pode usar o Swagger UI padrão do Sanic:

```python
# Em app/main.py, linha 32-35, altere:
app.config.OAS_UI_DEFAULT = "swagger"  # Era None

# Acesse: http://localhost:8000/docs
```

## Contato para Suporte

Se nenhuma solução funcionar, forneça:
- Versão do Python (`python --version`)
- Logs completos do servidor ao acessar `/scalar`
- Screenshot do erro no navegador
- Resultado de `curl http://localhost:8000/`
