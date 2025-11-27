# Implementação de Múltiplas Bases de Dados

## 🎯 Objetivo
Criar 4 bases de dados independentes, uma para cada aba, com sidebar vinculada à aba ativa.

## 📊 Estrutura de Bases de Dados

### 1. **Control Status** → `data/sox.db`
- Tabela: `controls`
- Usado para: Controles SOX

### 2. **Mics Tickets** → `data/MicsTickets.db`
- Tabela: `tickets`
- Usado para: Tickets MICS

### 3. **Mics Effort** → `data/MicsEffort.db`
- Tabela: `effort`
- Usado para: Esforço/Horas MICS

### 4. **Mics SA** → `data/MicsSA.db`
- Tabela: `service_agreements`
- Usado para: Service Agreements MICS

## 🔧 Mudanças Técnicas Necessárias

### 1. Configuração de Bancos (✅ FEITO)
```python
DB_CONFIGS = {
    "Control Status": {
        "db_path": DB_DIR / "sox.db",
        "table_name": "controls"
    },
    # ... outros configs
}
```

### 2. Funções de Banco de Dados (PRÓXIMO)
- Modificar todas as funções para aceitar `db_path` e `table_name` como parâmetros
- `init_db(db_path, table_name)`
- `get_conn(db_path)`
- `save_to_db(df, filename, db_path, table_name)`
- etc.

### 3. Session State para Aba Ativa (PRÓXIMO)
```python
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "Control Status"
```

### 4. Sidebar Dinâmico (PRÓXIMO)
- Sidebar detecta qual aba está ativa
- Usa a base de dados correta para aquela aba
- Operações afetam apenas a base de dados da aba ativa

### 5. Tabs Atualizados (PRÓXIMO)
- Cada tab define `st.session_state["active_tab"]`
- Cada tab carrega dados do seu próprio banco

## 🎨 Fluxo de Funcionamento

```
Usuário clica em "Mics Tickets"
  ↓
Session state atualiza: active_tab = "Mics Tickets"
  ↓
Sidebar detecta: aba ativa = "Mics Tickets"
  ↓
Sidebar usa: MicsTickets.db
  ↓
Upload/Save/Load afeta apenas MicsTickets.db
  ↓
Outras abas não são afetadas
```

## ⚠️ Status da Implementação

- ✅ Configuração de múltiplos bancos
- ✅ Modificação das funções de banco
- ✅ Implementação de session state
- ✅ Sidebar dinâmico com seletor de base de dados
- ✅ Atualização das tabs

## 🎉 Implementação Concluída!

### Como Funciona:

1. **Seletor de Base de Dados**: No topo do sidebar, há um dropdown que permite selecionar qual base de dados está ativa
2. **Isolamento Total**: Cada base de dados é completamente independente:
   - Control Status → sox.db (tabela: controls)
   - Mics Tickets → MicsTickets.db (tabela: tickets)
   - Mics Effort → MicsEffort.db (tabela: effort)
   - Mics SA → MicsSA.db (tabela: service_agreements)

3. **Operações por Base**: Todas as operações do sidebar (upload, salvar, carregar, deletar) afetam apenas a base selecionada

4. **Visualização Clara**: O sidebar mostra o arquivo e tabela ativos

### Exemplo de Uso:

1. Selecione "Mics Tickets" no dropdown
2. Faça upload de um arquivo Excel
3. Salve na base
4. Mude para "Control Status" no dropdown
5. Os dados de "Mics Tickets" não aparecem
6. Cada aba mantém seus próprios dados isolados

## 📝 Próximos Passos (Opcionais)

1. Adicionar validação de colunas específicas para cada tipo de base
2. Criar visualizações específicas para cada tab
3. Implementar exportação customizada por tipo de dado
