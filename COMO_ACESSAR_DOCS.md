# 🚀 Como Acessar a Documentação Scalar

## ⚡ Passos Rápidos

### 1. **PARE o servidor atual** (se estiver rodando)

```bash
# Pressione Ctrl+C no terminal onde o servidor está rodando
```

### 2. **REINICIE o servidor**

```bash
cd backend
python -m app.main
```

Aguarde ver esta mensagem:

```
Server started successfully
Goin' Fast @ http://0.0.0.0:8000
```

### 3. **ACESSE a documentação**

Abra o navegador em: **<http://localhost:8000/scalar>**

---

## 🔍 Verificações

### ✅ Verificar se o servidor está rodando

Em outro terminal:

```bash
curl http://localhost:8000/
```

Deve retornar JSON com `"scalar_docs": "/scalar"`

### ✅ Verificar se ENABLE_DOCS está true

```bash
# Windows
type backend\.env | findstr ENABLE_DOCS

# Linux/Mac
grep ENABLE_DOCS backend/.env
```

Deve mostrar: `ENABLE_DOCS=true`

### ✅ Testar o endpoint diretamente

```bash
curl http://localhost:8000/scalar
```

Deve retornar HTML com "Scalar"

---

## 🎯 Opções de Acesso

### Opção 1: Via Servidor (Recomendado)

1. Servidor rodando
2. Acesse: <http://localhost:8000/scalar>

### Opção 2: Arquivo HTML Standalone

1. Abra o arquivo: `backend/test_scalar_standalone.html` no navegador
2. Ele se conectará automaticamente ao servidor

### Opção 3: Especificação OpenAPI Raw

1. Acesse: <http://localhost:8000/api/docs/openapi.json>
2. Copie o JSON
3. Importe em Postman/Insomnia

---

## ❌ Problemas Comuns

### Problema 1: "Cannot GET /scalar" ou 404

**Causa**: Servidor não foi reiniciado após as mudanças

**Solução**:

```bash
# 1. Pare o servidor (Ctrl+C)
# 2. Reinicie
cd backend
python -m app.main
# 3. Aguarde "Server started"
# 4. Acesse http://localhost:8000/scalar
```

### Problema 2: Página em branco

**Causa**: JavaScript do Scalar não carregou

**Solução**:

1. Abra o Console do navegador (F12)
2. Veja se há erros
3. Verifique sua conexão com internet (CDN precisa de internet)
4. Tente recarregar a página (Ctrl+F5)

### Problema 3: "Documentation is disabled"

**Causa**: ENABLE_DOCS=false no .env

**Solução**:

```bash
# Edite backend/.env
ENABLE_DOCS=true  # Mude para true

# Reinicie o servidor
```

### Problema 4: Servidor não inicia

**Causa**: Dependências faltando

**Solução**:

```bash
cd backend
pip install -r requirements.txt
python -m app.main
```

---

## 📸 Como Deve Parecer

Quando funcionar, você verá:

```
✅ Interface roxa/purple com dark mode
✅ Sidebar à esquerda com lista de endpoints
✅ Painel central com detalhes da API
✅ Botão "Authorize" no topo
✅ Search box (atalho: tecla K)
✅ Seções: Authentication, Market Data, etc.
```

---

## 🆘 Ainda não funciona?

### Execute este teste completo

```bash
# 1. Pare qualquer servidor rodando
# Ctrl+C

# 2. Verifique o código
cd backend
grep -c "scalar" app/main.py
# Deve retornar um número > 0

# 3. Verifique .env
cat .env | grep ENABLE
# Deve mostrar ENABLE_DOCS=true

# 4. Limpe e reinstale
pip install --upgrade sanic sanic-ext

# 5. Inicie servidor em modo debug
python -m app.main

# 6. Em OUTRO terminal, teste
curl -v http://localhost:8000/scalar

# 7. Veja os logs do servidor
# Deve mostrar: GET /scalar 200
```

### Compartilhe estes detalhes

Se ainda não funcionar, me envie:

1. **Saída do curl**:

   ```bash
   curl -v http://localhost:8000/scalar > resultado.txt 2>&1
   ```

2. **Logs do servidor** ao acessar /scalar

3. **Console do navegador** (F12 → Console → erros em vermelho)

4. **Screenshot** da página que você vê

---

## ✨ Teste Alternativo

Enquanto resolve, você pode usar o **Swagger UI** padrão:

1. Edite `backend/app/main.py` linha 32:

   ```python
   app.config.OAS_UI_DEFAULT = "swagger"  # Mude de None para "swagger"
   ```

2. Reinicie servidor

3. Acesse: <http://localhost:8000/docs>

---

## 📞 Próximos Passos

Depois que funcionar:

1. ✅ Faça login via `/auth/login`
2. ✅ Copie o token JWT
3. ✅ Clique em "Authorize" no Scalar
4. ✅ Cole: `Bearer seu-token-aqui`
5. ✅ Teste os endpoints protegidos!

🎉 Boa documentação!
