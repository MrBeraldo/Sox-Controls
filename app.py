import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime
import sqlite3
from pathlib import Path
import uuid

# ========================================
# CONFIGURAÇÃO INICIAL
# ========================================
st.set_page_config(page_title="SOX Controls Executive Report", layout="wide")

DB_DIR = Path("data")
DB_PATH = DB_DIR / "sox.db"
TABLE_NAME = "controls"


# ========================================
# BANCO DE DADOS (SQLite)
# ========================================
def init_db():
    DB_DIR.mkdir(exist_ok=True, parents=True)

def get_conn():
    init_db()
    return sqlite3.connect(DB_PATH)

def save_to_db(df: pd.DataFrame, filename: str):
    conn = get_conn()
    uid = str(uuid.uuid4())
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df2 = df.copy()
    df2.insert(0, "upload_id", uid)
    df2.insert(1, "uploaded_at", ts)
    df2.insert(2, "source_filename", filename)

    df2.to_sql(TABLE_NAME, conn, if_exists="append", index=False)
    conn.close()
    return uid

def load_all():
    conn = get_conn()
    df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME}", conn)
    conn.close()
    return df

def load_by_uid(uid: str):
    conn = get_conn()
    df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME} WHERE upload_id=?", conn, params=[uid])
    conn.close()
    return df

def delete_uid(uid: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {TABLE_NAME} WHERE upload_id=?", (uid,))
    conn.commit()
    n = cur.rowcount
    conn.close()
    return n

def get_summary():
    if not DB_PATH.exists():
        return pd.DataFrame()

    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT upload_id, uploaded_at, source_filename, COUNT(*) AS rows
        FROM controls
        GROUP BY upload_id, uploaded_at, source_filename
        ORDER BY uploaded_at DESC
    """, conn)
    conn.close()
    return df


# ========================================
# FUNÇÕES AUXILIARES
# ========================================
@st.cache_data(show_spinner=False)
def load_excel(file):
    if file is None:
        return pd.DataFrame()
    df = pd.read_excel(file)
    df.columns = df.columns.str.strip()

    # REMOVE "(Não Modificar)"
    df = df[[c for c in df.columns if not c.startswith("(Não Modificar)")]]
    
    expected = [
        "IT Solution","MICS ID","BU Country/Owner","Zone","Control Owner",
        "Control Tester","Control Reviewer",
        "ControlExecutor (ZCM Lookup) (MICS_ZonalControlMaster)",
        "Control Status","Test Conclusion (OE1)","Test Conclusion (OE2)",
        "Test Conclusion (YE)"
    ]
    for col in expected:
        if col not in df.columns:
            df[col] = ""
    return df


def df_to_excel_bytes(df):
    buff = BytesIO()
    with pd.ExcelWriter(buff, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    buff.seek(0)
    return buff


def map_conclusion(v):
    if not isinstance(v, str) or v.strip() == "":
        return "Not Tested", 0.0
    t = v.lower().strip()
    if t.startswith("pass") or t in ["effective","ok","success"]:
        return "Effective", 1.0
    if t in ["fail","failed","ineffective","nok"]:
        return "Ineffective", 0.5
    return "Not Tested", 0.0


# ========================================
# CSS DO TEMA AZUL CORPORATIVO
# ========================================
st.markdown("""
<style>
body { background-color: #0d1117; color: #c9d1d9; }
h1, h2, h3 { color: #2f81f7; font-weight: 700; }
section[data-testid="stSidebar"] { background-color: #161b22; }
</style>
""", unsafe_allow_html=True)


# ========================================
# SESSION STATE
# ========================================
if "mode" not in st.session_state:
    st.session_state["mode"] = "upload"
if "uid" not in st.session_state:
    st.session_state["uid"] = None


# ========================================
# SIDEBAR (Upload / Base / Carregar / Remover)
# ========================================
with st.sidebar:
    st.header("📤 Upload")
    uploaded_file = st.file_uploader("Carregar arquivo Excel", type=["xlsx"])
    uploaded_df = load_excel(uploaded_file) if uploaded_file else pd.DataFrame()

    st.header("💾 Base SQLite")
    summary_df = get_summary()

    if summary_df.empty:
        st.caption("Nenhum registro salvo ainda.")
    else:
        st.caption(f"{summary_df['rows'].sum()} registros salvos")

    if st.button("Salvar arquivo na base"):
        if uploaded_df.empty:
            st.warning("Envie um arquivo primeiro.")
        else:
            new_uid = save_to_db(uploaded_df, uploaded_file.name)
            st.success(f"Upload salvo com ID: {new_uid}")
            st.session_state["mode"] = "db_uid"
            st.session_state["uid"] = new_uid

    st.subheader("📥 Carregar dados")
    options = []
    upload_map = {}

    if not summary_df.empty:
        for _, row in summary_df.iterrows():
            label = f"{row['uploaded_at']} - {row['source_filename']} ({row['rows']} linhas)"
            options.append(label)
            upload_map[label] = row["upload_id"]

    selected_load = st.selectbox("Selecione upload", ["<Selecione>"] + options)

    colA, colB = st.columns(2)
    with colA:
        if st.button("Carregar TODOS"):
            st.session_state["mode"] = "db_all"
            st.session_state["uid"] = None
    with colB:
        if st.button("Carregar selecionado"):
            if selected_load != "<Selecione>":
                st.session_state["mode"] = "db_uid"
                st.session_state["uid"] = upload_map[selected_load]

    st.subheader("🗑️ Remover upload")
    selected_del = st.selectbox("Selecione p/ excluir", ["<Selecione>"] + options, key="del")
    if st.button("Excluir upload"):
        if selected_del != "<Selecione>":
            removed = delete_uid(upload_map[selected_del])
            st.success(f"Removidas {removed} linhas.")
            if st.session_state["uid"] == upload_map[selected_del]:
                st.session_state["mode"] = "upload"
                st.session_state["uid"] = None


# ============================
# ESCOLHA DA FONTE DE DADOS
# ============================
mode = st.session_state["mode"]
uid = st.session_state["uid"]

if mode == "db_all":
    base_df = load_all()
elif mode == "db_uid":
    base_df = load_by_uid(uid) if uid else pd.DataFrame()
else:
    base_df = uploaded_df

if base_df.empty:
    st.warning("Nenhum dado carregado.")
    st.stop()

# Garantir colunas essenciais
required_cols = [
    "IT Solution","MICS ID","BU Country/Owner","Zone","Control Owner",
    "Control Tester","Control Reviewer",
    "ControlExecutor (ZCM Lookup) (MICS_ZonalControlMaster)",
    "Control Status","Test Conclusion (OE1)","Test Conclusion (OE2)","Test Conclusion (YE)"
]
for c in required_cols:
    if c not in base_df.columns:
        base_df[c] = ""

# ========================================
# FILTROS
# ========================================
with st.sidebar:
    st.header("🔍 Filtros")

    f_owner = st.multiselect("Control Owner", sorted(base_df["Control Owner"].dropna().unique()))
    f_zone  = st.multiselect("Zone", sorted(base_df["Zone"].dropna().unique()))
    f_status = st.multiselect("Control Status", sorted(base_df["Control Status"].dropna().unique()))
    f_mics = st.multiselect("MICS ID", sorted(base_df["MICS ID"].dropna().unique()))
    f_exec = st.multiselect(
        "Control Executor",
        sorted(base_df["ControlExecutor (ZCM Lookup) (MICS_ZonalControlMaster)"].dropna().unique())
    )

    show_chart = st.checkbox("📊 Exibir gráfico OE1 / OE2 / YE", value=False)


# ========================================
# APLICANDO FILTROS
# ========================================
mask = pd.Series(True, index=base_df.index)

if f_owner: mask &= base_df["Control Owner"].isin(f_owner)
if f_zone: mask &= base_df["Zone"].isin(f_zone)
if f_status: mask &= base_df["Control Status"].isin(f_status)
if f_mics: mask &= base_df["MICS ID"].isin(f_mics)
if f_exec: mask &= base_df["ControlExecutor (ZCM Lookup) (MICS_ZonalControlMaster)"].isin(f_exec)

df = base_df.loc[mask].copy()


# ========================================
# MÉTRICAS
# ========================================
st.markdown("## 📊 SOX Controls Executive Report — Blue Corporate")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Controls", len(df))

with col2:
    st.metric("Fails", int((df["Control Status"].str.lower() == "fail").sum()))

with col3:
    in_prog = df["Control Status"].fillna("").str.contains("progress", case=False).sum()
    st.metric("In Progress", int(in_prog))

st.markdown("---")


# ========================================
# GRÁFICO OE1 / OE2 / YE LADO A LADO
# ========================================
if show_chart and not df.empty:
    st.markdown("### 📈 Test Conclusions (OE1 / OE2 / YE) — Side-by-Side")

    # Mapear conclusões
    for col in ["Test Conclusion (OE1)", "Test Conclusion (OE2)", "Test Conclusion (YE)"]:
        mapped = df[col].apply(map_conclusion)
        df[col + " Text"] = mapped.apply(lambda x: x[0])
        df[col + " Num"] = mapped.apply(lambda x: x[1])

    phases = ["OE1", "OE2", "YE"]
    color_map = {
        "Effective": "#2ea043",    # verde corporate
        "Ineffective": "#f85149",  # vermelho corporate
        "Not Tested": "#8b949e",   # cinza corporate
    }

    fig = go.Figure()

    for phase in phases:
        num_col = f"Test Conclusion ({phase}) Num"
        txt_col = f"Test Conclusion ({phase}) Text"

        fig.add_trace(go.Bar(
            y=df["MICS ID"],
            x=df[num_col],
            orientation="h",
            name=phase,
            text=df[txt_col],
            textposition="inside",
            marker_color=df[txt_col].map(color_map),
            hovertemplate="<b>MICS ID:</b> %{y}<br>"
                          f"<b>Phase:</b> {phase}<br>"
                          "<b>Status:</b> %{text}<extra></extra>"
        ))

    fig.update_layout(
        barmode="group",
        bargroupgap=0.18,
        bargap=0.28,
        height=650,
        template="plotly_dark",
        plot_bgcolor="#0d1117",
        paper_bgcolor="#0d1117",
        font=dict(color="#c9d1d9")
    )

    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")


# ========================================
# TABELA — ocultando "(Não Modificar)"
# ========================================
st.markdown("### 📋 Detailed Controls Table")

# Colunas a ocultar
hidden_cols = [
    "upload_id",
    "uploaded_at",
    "source_filename"
]

# Ocultar também colunas técnicas "(Não Modificar)"
hidden_cols += [c for c in df.columns if c.startswith("(Não Modificar)")]

# Criar DF final de exibição
df_visible = df.drop(columns=hidden_cols, errors="ignore")


st.dataframe(df_visible, use_container_width=True)


# ========================================
# DOWNLOADS
# ========================================
csv_data = df_visible.to_csv(index=False).encode("utf-8")
excel_data = df_to_excel_bytes(df_visible)

col_d1, col_d2 = st.columns(2)

with col_d1:
    st.download_button(
        "📥 Baixar CSV",
        data=csv_data,
        file_name="sox_controls_filtered.csv",
        mime="text/csv"
    )

with col_d2:
    st.download_button(
        "📥 Baixar Excel",
        data=excel_data,
        file_name="sox_controls_filtered.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
