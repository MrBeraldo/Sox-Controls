import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO
from datetime import datetime
import sqlite3
from pathlib import Path
import uuid
import logging
import sys
from typing import Optional, Tuple

# ========================================
# LOGGING CONFIGURATION
# ========================================
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f'sox_dashboard_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ========================================
# CONFIGURAÇÃO INICIAL
# ========================================
st.set_page_config(page_title="SOX Controls Executive Report", layout="wide")

# Configuração de múltiplos bancos de dados
DB_DIR = Path("data")
DB_CONFIGS = {
    "Control Status": {
        "db_path": DB_DIR / "sox.db",
        "table_name": "controls"
    },
    "Mics Tickets": {
        "db_path": DB_DIR / "MicsTickets.db",
        "table_name": "tickets"
    },
    "Mics Effort": {
        "db_path": DB_DIR / "MicsEffort.db",
        "table_name": "effort"
    },
    "Mics SA": {
        "db_path": DB_DIR / "MicsSA.db",
        "table_name": "service_agreements"
    },
    "Security Tickets": {
        "db_path": DB_DIR / "SecurityTickets.db",
        "table_name": "security_tickets"
    },
    "Security Effort": {
        "db_path": DB_DIR / "SecurityEffort.db",
        "table_name": "security_effort"
    }
}

logger.info("Application started")


# ========================================
# BANCO DE DADOS (SQLite)
# ========================================

# Schemas para diferentes tipos de tabelas
TABLE_SCHEMAS = {
    "controls": """
        upload_id TEXT NOT NULL,
        uploaded_at TEXT NOT NULL,
        source_filename TEXT NOT NULL,
        "IT Solution" TEXT,
        "MICS ID" TEXT,
        "BU Country/Owner" TEXT,
        "Zone" TEXT,
        "Control Owner" TEXT,
        "Control Tester" TEXT,
        "Control Reviewer" TEXT,
        "ControlExecutor (ZCM Lookup) (MICS_ZonalControlMaster)" TEXT,
        "Control Status" TEXT,
        "Test Conclusion (OE1)" TEXT,
        "Test Conclusion (OE2)" TEXT,
        "Test Conclusion (YE)" TEXT
    """,
    "tickets": """
        upload_id TEXT NOT NULL,
        uploaded_at TEXT NOT NULL,
        source_filename TEXT NOT NULL,
        [Number] TEXT,
        [Active] TEXT,
        [State] TEXT,
        [Approval] TEXT,
        [Item] TEXT,
        [Catalogs] TEXT,
        [Created] TEXT,
        [Assignment group] TEXT,
        [Assigned to] TEXT,
        [Short description] TEXT,
        [On Behalf of] TEXT,
        [Request] TEXT,
        [Email] TEXT,
        [Approval set] TEXT,
        [Descripción] TEXT,
        [Tipo de Solicitud N2] TEXT,
        [Tipo de usuario] TEXT,
        [Employee number] TEXT,
        [ID (a 8 digitos)] TEXT,
        [Preferred Zone] TEXT,
        [Country code] TEXT,
        [KB Number] TEXT
    """,
    "effort": """
        upload_id TEXT NOT NULL,
        uploaded_at TEXT NOT NULL,
        source_filename TEXT NOT NULL
    """,
    "service_agreements": """
        upload_id TEXT NOT NULL,
        uploaded_at TEXT NOT NULL,
        source_filename TEXT NOT NULL
    """,
    "security_tickets": """
        upload_id TEXT NOT NULL,
        uploaded_at TEXT NOT NULL,
        source_filename TEXT NOT NULL,
        [Number] TEXT,
        [Active] TEXT,
        [State] TEXT,
        [Priority] TEXT,
        [Category] TEXT,
        [Subcategory] TEXT,
        [Created] TEXT,
        [Assignment group] TEXT,
        [Assigned to] TEXT,
        [Short description] TEXT,
        [Description] TEXT,
        [Caller] TEXT,
        [Resolved] TEXT,
        [Resolution code] TEXT,
        [Resolution notes] TEXT
    """,
    "security_effort": """
        upload_id TEXT NOT NULL,
        uploaded_at TEXT NOT NULL,
        source_filename TEXT NOT NULL,
        [Task] TEXT,
        [Resource] TEXT,
        [Date] TEXT,
        [Hours] TEXT,
        [Activity Type] TEXT,
        [Project] TEXT,
        [Description] TEXT
    """
}

def init_db(db_path: Path, table_name: str):
    """Initialize database directory and create table schema if needed"""
    try:
        DB_DIR.mkdir(exist_ok=True, parents=True)
        logger.info(f"Database directory initialized: {DB_DIR}")

        # Get schema for this table type
        schema = TABLE_SCHEMAS.get(table_name, TABLE_SCHEMAS["controls"])

        # Create table schema if not exists
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {schema}
            )
        """)
        conn.commit()
        conn.close()
        logger.info(f"Database schema initialized successfully for {db_path} (table: {table_name})")
    except Exception as e:
        logger.error(f"Error initializing database {db_path}: {str(e)}", exc_info=True)
        raise

def get_conn(db_path: Path, table_name: str):
    """Get database connection with error handling"""
    try:
        init_db(db_path, table_name)
        conn = sqlite3.connect(db_path)
        logger.debug(f"Database connection established: {db_path}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database {db_path}: {str(e)}", exc_info=True)
        raise

def save_to_db(df: pd.DataFrame, filename: str, db_path: Path, table_name: str) -> Optional[str]:
    """Save DataFrame to database with error handling"""
    try:
        logger.info(f"Attempting to save file '{filename}' with {len(df)} rows to {db_path}")
        conn = get_conn(db_path, table_name)
        uid = str(uuid.uuid4())
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        df2 = df.copy()
        df2.insert(0, "upload_id", uid)
        df2.insert(1, "uploaded_at", ts)
        df2.insert(2, "source_filename", filename)

        df2.to_sql(table_name, conn, if_exists="append", index=False)
        conn.close()
        logger.info(f"Successfully saved upload {uid} with {len(df)} rows to {db_path}")
        return uid
    except Exception as e:
        logger.error(f"Error saving to database {db_path}: {str(e)}", exc_info=True)
        st.error(f"❌ Error saving to database: {str(e)}")
        return None

def load_all(db_path: Path, table_name: str) -> pd.DataFrame:
    """Load all data from database with error handling"""
    try:
        logger.info(f"Loading all data from {db_path}")
        conn = get_conn(db_path, table_name)
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        logger.info(f"Loaded {len(df)} rows from {db_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading all data from {db_path}: {str(e)}", exc_info=True)
        st.error(f"❌ Error loading data: {str(e)}")
        return pd.DataFrame()

def load_by_uid(uid: str, db_path: Path, table_name: str) -> pd.DataFrame:
    """Load data by upload ID with error handling"""
    try:
        logger.info(f"Loading data for upload_id: {uid} from {db_path}")
        conn = get_conn(db_path, table_name)
        df = pd.read_sql_query(f"SELECT * FROM {table_name} WHERE upload_id=?", conn, params=[uid])
        conn.close()
        logger.info(f"Loaded {len(df)} rows for upload_id: {uid} from {db_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading data for uid {uid} from {db_path}: {str(e)}", exc_info=True)
        st.error(f"❌ Error loading data: {str(e)}")
        return pd.DataFrame()

def delete_uid(uid: str, db_path: Path, table_name: str) -> int:
    """Delete upload by ID with error handling"""
    try:
        logger.info(f"Deleting upload_id: {uid} from {db_path}")
        conn = get_conn(db_path, table_name)
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {table_name} WHERE upload_id=?", (uid,))
        conn.commit()
        n = cur.rowcount
        conn.close()
        logger.info(f"Deleted {n} rows for upload_id: {uid} from {db_path}")
        return n
    except Exception as e:
        logger.error(f"Error deleting uid {uid} from {db_path}: {str(e)}", exc_info=True)
        st.error(f"❌ Error deleting data: {str(e)}")
        return 0

def get_summary(db_path: Path, table_name: str) -> pd.DataFrame:
    """Get summary of uploads with error handling"""
    try:
        if not db_path.exists():
            logger.info(f"Database file does not exist yet: {db_path}")
            return pd.DataFrame()

        logger.info(f"Getting upload summary from {db_path}")
        conn = get_conn(db_path, table_name)
        df = pd.read_sql_query(f"""
            SELECT upload_id, uploaded_at, source_filename, COUNT(*) AS rows
            FROM {table_name}
            GROUP BY upload_id, uploaded_at, source_filename
            ORDER BY uploaded_at DESC
        """, conn)
        conn.close()
        logger.info(f"Retrieved summary with {len(df)} uploads from {db_path}")
        return df
    except Exception as e:
        logger.error(f"Error getting summary from {db_path}: {str(e)}", exc_info=True)
        return pd.DataFrame()


# ========================================
# FUNÇÕES AUXILIARES
# ========================================
def validate_excel_file(df: pd.DataFrame) -> Tuple[bool, str]:
    """Validate Excel file structure"""
    if df.empty:
        return False, "Excel file is empty"

    if len(df) > 100000:
        return False, f"File too large: {len(df)} rows (max 100,000)"

    logger.info(f"Excel validation passed: {len(df)} rows, {len(df.columns)} columns")
    return True, "Valid"

@st.cache_data(show_spinner=False)
def load_excel(file) -> pd.DataFrame:
    """Load and validate Excel file with error handling"""
    if file is None:
        return pd.DataFrame()

    try:
        logger.info(f"Loading Excel file: {file.name}")
        df = pd.read_excel(file)

        # Validate file
        is_valid, message = validate_excel_file(df)
        if not is_valid:
            logger.error(f"Excel validation failed: {message}")
            st.error(f"❌ {message}")
            return pd.DataFrame()

        # Limpar nomes das colunas
        df.columns = df.columns.str.strip()

        # REMOVE "(Não Modificar)"
        df = df[[c for c in df.columns if not c.startswith("(Não Modificar)")]]

        logger.info(f"Excel file loaded successfully: {len(df)} rows, {len(df.columns)} columns")
        logger.info(f"Columns: {df.columns.tolist()}")
        return df

    except Exception as e:
        logger.error(f"Error loading Excel file: {str(e)}", exc_info=True)
        st.error(f"❌ Error loading Excel file: {str(e)}")
        return pd.DataFrame()


def df_to_excel_bytes(df: pd.DataFrame) -> Optional[BytesIO]:
    """Convert DataFrame to Excel bytes with error handling"""
    try:
        logger.info(f"Converting DataFrame to Excel: {len(df)} rows")
        buff = BytesIO()
        with pd.ExcelWriter(buff, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)
        buff.seek(0)
        logger.info("Excel conversion successful")
        return buff
    except Exception as e:
        logger.error(f"Error converting to Excel: {str(e)}", exc_info=True)
        st.error(f"❌ Error creating Excel file: {str(e)}")
        return None


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
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "Control Status"


# ========================================
# SIDEBAR (Upload / Base / Carregar / Remover)
# ========================================
with st.sidebar:
    st.title("🎛️ Painel de Controle")

    # Mostrar qual aba está ativa
    st.markdown("### 🗄️ Base de Dados Ativa")

    # Obter configuração do banco de dados da aba ativa
    active_tab_name = st.session_state.get("active_tab", "Control Status")
    active_db_config = DB_CONFIGS[active_tab_name]
    active_db_path = active_db_config["db_path"]
    active_table_name = active_db_config["table_name"]

    # Mostrar informações do banco ativo
    st.info(f"**{active_tab_name}**")
    st.caption(f"💾 Arquivo: {active_db_path.name}")
    st.caption(f"📊 Tabela: {active_table_name}")
    st.divider()

    # ========================================
    # SEÇÃO 1: UPLOAD
    # ========================================
    with st.expander("📤 Upload de Arquivo", expanded=True):
        uploaded_file = st.file_uploader("Carregar arquivo Excel", type=["xlsx"], label_visibility="collapsed")
        uploaded_df = load_excel(uploaded_file) if uploaded_file else pd.DataFrame()

        if uploaded_file:
            st.success(f"✅ Arquivo carregado: {uploaded_file.name}")
            st.caption(f"📊 {len(uploaded_df)} linhas")

    # ========================================
    # SEÇÃO 2: BASE SQLITE
    # ========================================
    summary_df = get_summary(active_db_path, active_table_name)

    with st.expander("💾 Base SQLite", expanded=False):
        if summary_df.empty:
            st.info("📋 Nenhum registro salvo ainda.")
        else:
            st.metric("Total de Registros", summary_df['rows'].sum())
            st.caption(f"📁 {len(summary_df)} uploads salvos")

        if st.button("💾 Salvar arquivo na base", use_container_width=True):
            if uploaded_df.empty:
                st.warning("⚠️ Envie um arquivo primeiro.")
            else:
                new_uid = save_to_db(uploaded_df, uploaded_file.name, active_db_path, active_table_name)
                if new_uid:
                    st.success(f"✅ Upload salvo!")
                    st.caption(f"ID: {new_uid[:8]}...")
                    st.session_state["mode"] = "db_uid"
                    st.session_state["uid"] = new_uid
                else:
                    logger.error("Failed to save upload to database")
                    st.error("❌ Falha ao salvar arquivo.")

    # ========================================
    # SEÇÃO 3: CARREGAR DADOS
    # ========================================
    options = []
    upload_map = {}

    if not summary_df.empty:
        for _, row in summary_df.iterrows():
            label = f"{row['uploaded_at']} - {row['source_filename']} ({row['rows']} linhas)"
            options.append(label)
            upload_map[label] = row["upload_id"]

    with st.expander("📥 Carregar Dados", expanded=False):
        selected_load = st.selectbox("Selecione upload", ["<Selecione>"] + options, label_visibility="collapsed")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Todos", use_container_width=True):
                st.session_state["mode"] = "db_all"
                st.session_state["uid"] = None
                st.success("✅ Carregando todos")
        with col2:
            if st.button("📄 Selecionado", use_container_width=True):
                if selected_load != "<Selecione>":
                    st.session_state["mode"] = "db_uid"
                    st.session_state["uid"] = upload_map[selected_load]
                    st.success("✅ Carregado!")
                else:
                    st.warning("⚠️ Selecione um upload")

    # ========================================
    # SEÇÃO 4: REMOVER UPLOAD
    # ========================================
    with st.expander("🗑️ Remover Upload", expanded=False):
        selected_del = st.selectbox("Selecione p/ excluir", ["<Selecione>"] + options, key="del", label_visibility="collapsed")

        if st.button("🗑️ Excluir Upload", use_container_width=True, type="secondary"):
            if selected_del != "<Selecione>":
                removed = delete_uid(upload_map[selected_del], active_db_path, active_table_name)
                if removed > 0:
                    st.success(f"✅ {removed} linhas removidas")
                    if st.session_state["uid"] == upload_map[selected_del]:
                        st.session_state["mode"] = "upload"
                        st.session_state["uid"] = None
                else:
                    st.warning("⚠️ Nenhuma linha removida")
            else:
                st.warning("⚠️ Selecione um upload")


# ============================
# ESCOLHA DA FONTE DE DADOS
# ============================
mode = st.session_state["mode"]
uid = st.session_state["uid"]

# Usar a configuração da aba ativa
active_tab_name = st.session_state["active_tab"]
active_db_config = DB_CONFIGS[active_tab_name]
active_db_path = active_db_config["db_path"]
active_table_name = active_db_config["table_name"]

if mode == "db_all":
    base_df = load_all(active_db_path, active_table_name)
elif mode == "db_uid":
    base_df = load_by_uid(uid, active_db_path, active_table_name) if uid else pd.DataFrame()
else:
    base_df = uploaded_df

# Garantir colunas essenciais
required_cols = [
    "IT Solution","MICS ID","BU Country/Owner","Zone","Control Owner",
    "Control Tester","Control Reviewer",
    "ControlExecutor (ZCM Lookup) (MICS_ZonalControlMaster)",
    "Control Status","Test Conclusion (OE1)","Test Conclusion (OE2)","Test Conclusion (YE)"
]

# Se não há dados, criar dataframe vazio com as colunas necessárias
if base_df.empty:
    base_df = pd.DataFrame(columns=required_cols)
else:
    # Garantir que todas as colunas existem
    for c in required_cols:
        if c not in base_df.columns:
            base_df[c] = ""


# ========================================
# FILTROS NO SIDEBAR
# ========================================
with st.sidebar:
    # ========================================
    # SEÇÃO 5: FILTROS
    # ========================================
    with st.expander("🔍 Filtros", expanded=True):
        f_owner = st.multiselect("Control Owner", sorted(base_df["Control Owner"].dropna().unique()))
        f_zone  = st.multiselect("Zone", sorted(base_df["Zone"].dropna().unique()))
        f_status = st.multiselect("Control Status", sorted(base_df["Control Status"].dropna().unique()))
        f_mics = st.multiselect("MICS ID", sorted(base_df["MICS ID"].dropna().unique()))
        f_exec = st.multiselect(
            "Control Executor",
            sorted(base_df["ControlExecutor (ZCM Lookup) (MICS_ZonalControlMaster)"].dropna().unique())
        )

        st.divider()
        show_chart = st.toggle("📊 Exibir gráfico OE1 / OE2 / YE", value=False)

        # Mostrar filtros ativos
        active_filters = sum([bool(f_owner), bool(f_zone), bool(f_status), bool(f_mics), bool(f_exec)])
        if active_filters > 0:
            st.caption(f"✅ {active_filters} filtro(s) ativo(s)")


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
# ABAS (TABS) - NESTED STRUCTURE
# ========================================
parent_tab1, parent_tab2 = st.tabs(["📁 MICS", "🔒 Security"])

# ========================================
# PARENT TAB 1: MICS
# ========================================
with parent_tab1:
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Control Status", "🎫 Mics Tickets", "⏱️ Mics Effort", "🔧 Mics SA"])

# ========================================
# ABA 1: CONTROL STATUS
# ========================================
with tab1:
    # Botão invisível para detectar clique na tab
    if st.button("📊", key="tab1_btn", help="Ativar base Control Status"):
        st.session_state["active_tab"] = "Control Status"
        st.rerun()

    st.markdown("## 📊 SOX Controls Executive Report")

    # Verificar se há dados carregados
    if df.empty:
        st.info("📋 **Nenhum dado carregado**")
        st.markdown("""
        ### Como começar:
        1. 📤 **Upload**: Carregue um arquivo Excel na seção "Upload de Arquivo" no menu lateral
        2. 💾 **Salvar**: Salve o arquivo na base de dados SQLite
        3. 📥 **Carregar**: Carregue os dados salvos
        4. 🔍 **Filtrar**: Use os filtros para visualizar dados específicos
        """)
    else:
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
        # Verificar se pelo menos um filtro está preenchido
        has_filter = any([f_owner, f_zone, f_status, f_mics, f_exec])

        if show_chart:
            if not has_filter:
                st.warning("⚠️ Por favor, selecione pelo menos um filtro para exibir o gráfico.")
                logger.warning("Chart display attempted without filters")
            elif df.empty:
                st.warning("⚠️ Nenhum dado disponível para exibir o gráfico.")
                logger.warning("Chart display attempted with empty dataframe")
            else:
                logger.info(f"Displaying chart with {len(df)} rows")
                st.markdown("### 📈 Test Conclusions (OE1 / OE2 / YE) — Side-by-Side")

                for col in ["Test Conclusion (OE1)", "Test Conclusion (OE2)", "Test Conclusion (YE)"]:
                    mapped = df[col].apply(map_conclusion)
                    df[col + " Text"] = mapped.apply(lambda x: x[0])
                    df[col + " Num"] = mapped.apply(lambda x: x[1])

                phases = ["OE1","OE2","YE"]
                color_map={
                    "Effective":"#2ea043",
                    "Ineffective":"#f85149",
                    "Not Tested":"#8b949e"
                }

                fig = go.Figure()

                for phase in phases:
                    num_col = f"Test Conclusion ({phase}) Num"
                    txt_col = f"Test Conclusion ({phase}) Text"

                    fig.add_trace(go.Bar(
                        y=df["MICS ID"],
                        x=df[num_col],
                        name=phase,
                        orientation="h",
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

                st.plotly_chart(fig,use_container_width=True)

        st.markdown("---")

        # OCULTAR COLUNAS TÉCNICAS
        hidden_cols = [
            "upload_id",
            "uploaded_at",
            "source_filename"
        ]
        hidden_cols += [c for c in df.columns if c.startswith("(Não Modificar)")]

        df_visible = df.drop(columns=hidden_cols, errors="ignore")

        # ========================================
        # TABELA FINAL
        # ========================================
        st.markdown("### 📋 Detailed Controls Table")
        st.dataframe(df_visible, use_container_width=True)


        # ========================================
        # DOWNLOADS
        # ========================================
        try:
            logger.info("Preparing download files")
            csv_data = df_visible.to_csv(index=False).encode("utf-8")
            excel_data = df_to_excel_bytes(df_visible)

            col_d1, col_d2 = st.columns(2)

            with col_d1:
                st.download_button(
                    "📥 Download CSV",
                    data=csv_data,
                    file_name="sox_controls_filtered.csv",
                    mime="text/csv"
                )

            with col_d2:
                if excel_data:
                    st.download_button(
                        "📥 Download Excel",
                        data=excel_data,
                        file_name="sox_controls_filtered.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.error("❌ Erro ao gerar arquivo Excel")

            logger.info("Download buttons prepared successfully")
        except Exception as e:
            logger.error(f"Error preparing downloads: {str(e)}", exc_info=True)
            st.error(f"❌ Error preparing downloads: {str(e)}")

# ========================================
# ABA 2: MICS TICKETS
# ========================================
with tab2:
    # Botão para ativar esta aba
    if st.button("🎫", key="tab2_btn", help="Ativar base Mics Tickets"):
        st.session_state["active_tab"] = "Mics Tickets"
        st.rerun()

    st.markdown("## 🎫 Mics Tickets Dashboard")

    # Verificar se há dados carregados
    if df.empty:
        st.info("📋 **Nenhum dado carregado**")
        st.markdown("""
        ### Como começar:
        1. 🎫 **Ative esta base**: Clique no botão 🎫 acima
        2. 📤 **Upload**: Carregue um arquivo Excel de tickets no menu lateral
        3. 💾 **Salvar**: Salve o arquivo na base de dados
        4. 📥 **Carregar**: Carregue os dados salvos
        5. 🔍 **Filtrar**: Use os filtros para visualizar dados específicos
        """)
    else:
        # ========================================
        # MÉTRICAS PRINCIPAIS
        # ========================================
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total de Tickets", len(df))

        with col2:
            # Contar tickets ativos
            active_tickets = df[df["Active"].astype(str).str.lower() == "true"].shape[0] if "Active" in df.columns else 0
            st.metric("Tickets Ativos", active_tickets)

        with col3:
            # Contar tickets pendentes
            pending = df[df["State"].astype(str).str.contains("Pending", case=False, na=False)].shape[0] if "State" in df.columns else 0
            st.metric("Pendentes", pending)

        with col4:
            # Contar tickets completos
            completed = df[df["State"].astype(str).str.contains("Complete", case=False, na=False)].shape[0] if "State" in df.columns else 0
            st.metric("Completos", completed)

        st.markdown("---")

        # ========================================
        # GRÁFICOS DE VISUALIZAÇÃO
        # ========================================
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            if "State" in df.columns:
                st.markdown("### 📊 Tickets por Estado")
                state_counts = df["State"].value_counts()

                fig_state = go.Figure(data=[go.Bar(
                    x=state_counts.index,
                    y=state_counts.values,
                    marker_color='#2f81f7',
                    text=state_counts.values,
                    textposition='auto',
                )])

                fig_state.update_layout(
                    height=400,
                    template="plotly_dark",
                    plot_bgcolor="#0d1117",
                    paper_bgcolor="#0d1117",
                    font=dict(color="#c9d1d9"),
                    xaxis_title="Estado",
                    yaxis_title="Quantidade"
                )

                st.plotly_chart(fig_state, use_container_width=True)

        with col_chart2:
            if "Preferred Zone" in df.columns:
                st.markdown("### 🌍 Tickets por Zona")
                zone_counts = df["Preferred Zone"].value_counts().head(10)

                fig_zone = go.Figure(data=[go.Pie(
                    labels=zone_counts.index,
                    values=zone_counts.values,
                    hole=0.4,
                    marker_colors=['#2f81f7', '#2ea043', '#f85149', '#8b949e', '#d29922', '#bc8cff', '#ff7b72', '#56d364']
                )])

                fig_zone.update_layout(
                    height=400,
                    template="plotly_dark",
                    plot_bgcolor="#0d1117",
                    paper_bgcolor="#0d1117",
                    font=dict(color="#c9d1d9")
                )

                st.plotly_chart(fig_zone, use_container_width=True)

        st.markdown("---")

        # ========================================
        # NOVOS GRÁFICOS - TICKETS POR USUÁRIO E DIAS ABERTOS
        # ========================================
        col_chart3, col_chart4 = st.columns(2)

        with col_chart3:
            if "Assigned to" in df.columns:
                st.markdown("### 👤 Tickets por Usuário")
                # Contar tickets por usuário atribuído
                assigned_counts = df["Assigned to"].value_counts().head(15)

                fig_assigned = go.Figure(data=[go.Bar(
                    y=assigned_counts.index,
                    x=assigned_counts.values,
                    orientation='h',
                    marker_color='#2ea043',
                    text=assigned_counts.values,
                    textposition='auto',
                )])

                fig_assigned.update_layout(
                    height=500,
                    template="plotly_dark",
                    plot_bgcolor="#0d1117",
                    paper_bgcolor="#0d1117",
                    font=dict(color="#c9d1d9"),
                    xaxis_title="Quantidade de Tickets",
                    yaxis_title="Usuário",
                    yaxis=dict(autorange="reversed")
                )

                st.plotly_chart(fig_assigned, use_container_width=True)

        with col_chart4:
            if "Created" in df.columns and "State" in df.columns:
                st.markdown("### 📅 Dias Desde a Criação (Pending/Work in Progress)")
                try:
                    df_days = df.copy()
                    # Filtrar apenas tickets com status Pending ou Work in Progress
                    df_days = df_days[
                        df_days["State"].astype(str).str.contains("Pending|Work in Progress", case=False, na=False)
                    ]

                    # Converter coluna Created para datetime
                    df_days["Created_Date"] = pd.to_datetime(df_days["Created"], errors='coerce')
                    df_days = df_days.dropna(subset=["Created_Date"])

                    if not df_days.empty:
                        # Calcular dias desde a criação
                        today = pd.Timestamp.now()
                        df_days["Days_Open"] = (today - df_days["Created_Date"]).dt.days

                        # Pegar os 15 tickets mais antigos (com mais dias abertos)
                        df_oldest = df_days.nlargest(15, "Days_Open")

                        # Criar labels com número do ticket (se disponível)
                        if "Number" in df_oldest.columns:
                            labels = df_oldest["Number"].fillna("N/A").astype(str)
                        else:
                            labels = [f"Ticket {i+1}" for i in range(len(df_oldest))]

                        fig_days = go.Figure(data=[go.Bar(
                            y=labels,
                            x=df_oldest["Days_Open"],
                            orientation='h',
                            marker_color='#d29922',
                            text=[f"{d} dias" for d in df_oldest["Days_Open"]],
                            textposition='auto',
                        )])

                        fig_days.update_layout(
                            height=500,
                            template="plotly_dark",
                            plot_bgcolor="#0d1117",
                            paper_bgcolor="#0d1117",
                            font=dict(color="#c9d1d9"),
                            xaxis_title="Dias Abertos",
                            yaxis_title="Ticket",
                            yaxis=dict(autorange="reversed")
                        )

                        st.plotly_chart(fig_days, use_container_width=True)
                    else:
                        st.info("📋 Não há dados de data de criação disponíveis")
                except Exception as e:
                    logger.error(f"Error creating days open chart: {str(e)}")
                    st.warning("⚠️ Erro ao criar gráfico de dias abertos")

        st.markdown("---")

        # ========================================
        # GRÁFICO DE LINHA DO TEMPO
        # ========================================
        if "Created" in df.columns:
            st.markdown("### 📈 Tickets Criados ao Longo do Tempo")
            try:
                df_timeline = df.copy()
                df_timeline["Created_Date"] = pd.to_datetime(df_timeline["Created"], errors='coerce')
                df_timeline = df_timeline.dropna(subset=["Created_Date"])

                if not df_timeline.empty:
                    timeline_data = df_timeline.groupby(df_timeline["Created_Date"].dt.date).size().reset_index(name='count')

                    fig_timeline = go.Figure(data=[go.Scatter(
                        x=timeline_data["Created_Date"],
                        y=timeline_data["count"],
                        mode='lines+markers',
                        line=dict(color='#2f81f7', width=2),
                        marker=dict(size=6),
                        fill='tozeroy',
                        fillcolor='rgba(47, 129, 247, 0.1)'
                    )])

                    fig_timeline.update_layout(
                        height=350,
                        template="plotly_dark",
                        plot_bgcolor="#0d1117",
                        paper_bgcolor="#0d1117",
                        font=dict(color="#c9d1d9"),
                        xaxis_title="Data",
                        yaxis_title="Número de Tickets"
                    )

                    st.plotly_chart(fig_timeline, use_container_width=True)
            except Exception as e:
                logger.error(f"Error creating timeline chart: {str(e)}")
                st.warning("⚠️ Não foi possível criar o gráfico de linha do tempo")

        st.markdown("---")

        # OCULTAR COLUNAS TÉCNICAS
        hidden_cols = ["upload_id", "uploaded_at", "source_filename"]
        df_visible = df.drop(columns=hidden_cols, errors="ignore")

        # ========================================
        # TABELA DE TICKETS
        # ========================================
        st.markdown("### 📋 Tabela Detalhada de Tickets")
        st.dataframe(df_visible, use_container_width=True, height=400)

        # ========================================
        # DOWNLOADS
        # ========================================
        try:
            logger.info("Preparing download files for tickets")
            csv_data = df_visible.to_csv(index=False).encode("utf-8")
            excel_data = df_to_excel_bytes(df_visible)

            col_d1, col_d2 = st.columns(2)

            with col_d1:
                st.download_button(
                    "📥 Download CSV",
                    data=csv_data,
                    file_name="mics_tickets.csv",
                    mime="text/csv"
                )

            with col_d2:
                if excel_data:
                    st.download_button(
                        "📥 Download Excel",
                        data=excel_data,
                        file_name="mics_tickets.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.error("❌ Erro ao gerar arquivo Excel")

            logger.info("Download buttons prepared successfully for tickets")
        except Exception as e:
            logger.error(f"Error preparing downloads: {str(e)}", exc_info=True)
            st.error(f"❌ Error preparing downloads: {str(e)}")

# ========================================
# ABA 3: MICS EFFORT
# ========================================
with tab3:
    # Botão para ativar esta aba
    if st.button("⏱️", key="tab3_btn", help="Ativar base Mics Effort"):
        st.session_state["active_tab"] = "Mics Effort"
        st.rerun()

    st.markdown("## ⏱️ Mics Effort")
    st.info("📋 Esta seção está em desenvolvimento. Em breve você poderá acompanhar esforços MICS aqui.")

    # Placeholder content
    st.markdown("### Funcionalidades Planejadas:")
    st.markdown("""
    - ⏱️ Tracking de horas/esforço
    - 👥 Alocação de recursos
    - 📊 Relatórios de produtividade
    - 📈 Análise de tendências
    """)

# ========================================
# ABA 4: MICS SA
# ========================================
with tab4:
    # Botão para ativar esta aba
    if st.button("🔧", key="tab4_btn", help="Ativar base Mics SA"):
        st.session_state["active_tab"] = "Mics SA"
        st.rerun()

    st.markdown("## 🔧 Mics SA")
    st.info("📋 Esta seção está em desenvolvimento. Em breve você poderá gerenciar Mics SA aqui.")

    # Placeholder content
    st.markdown("### Funcionalidades Planejadas:")
    st.markdown("""
    - 🔧 Gestão de Service Agreements
    - 📋 Contratos e SLAs
    - 📊 Métricas de performance
    - 📈 Dashboard de compliance
    - 🔔 Alertas e notificações
    - 📄 Geração de relatórios
    """)

# ========================================
# PARENT TAB 2: SECURITY
# ========================================
with parent_tab2:
    sec_tab1, sec_tab2 = st.tabs(["🎫 Security Tickets", "⏱️ Security Effort"])

    # ========================================
    # SECURITY TAB 1: SECURITY TICKETS
    # ========================================
    with sec_tab1:
        # Botão para ativar esta aba
        if st.button("🎫", key="sec_tab1_btn", help="Ativar base Security Tickets"):
            st.session_state["active_tab"] = "Security Tickets"
            st.rerun()

        st.markdown("## 🎫 Security Tickets Dashboard")

        # Verificar se há dados carregados
        if df.empty:
            st.info("📋 **Nenhum dado carregado**")
            st.markdown("""
            ### Como começar:
            1. 🎫 **Ative esta base**: Clique no botão 🎫 acima
            2. 📤 **Upload**: Carregue um arquivo Excel de security tickets no menu lateral
            3. 💾 **Salvar**: Salve o arquivo na base de dados
            4. 📥 **Carregar**: Carregue os dados salvos
            5. 🔍 **Filtrar**: Use os filtros para visualizar dados específicos
            """)
        else:
            # ========================================
            # MÉTRICAS PRINCIPAIS
            # ========================================
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total de Tickets", len(df))

            with col2:
                # Contar tickets ativos
                active_tickets = df[df["Active"].astype(str).str.lower() == "true"].shape[0] if "Active" in df.columns else 0
                st.metric("Tickets Ativos", active_tickets)

            with col3:
                # Contar tickets de alta prioridade
                high_priority = df[df["Priority"].astype(str).str.contains("High|Critical", case=False, na=False)].shape[0] if "Priority" in df.columns else 0
                st.metric("Alta Prioridade", high_priority)

            with col4:
                # Contar tickets resolvidos
                resolved = df[df["Resolved"].notna()].shape[0] if "Resolved" in df.columns else 0
                st.metric("Resolvidos", resolved)

            st.markdown("---")

            # ========================================
            # GRÁFICOS DE VISUALIZAÇÃO
            # ========================================
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                if "State" in df.columns:
                    st.markdown("### 📊 Tickets por Estado")
                    state_counts = df["State"].value_counts()

                    fig_state = go.Figure(data=[go.Bar(
                        x=state_counts.index,
                        y=state_counts.values,
                        marker_color='#f85149',
                        text=state_counts.values,
                        textposition='auto',
                    )])

                    fig_state.update_layout(
                        height=400,
                        template="plotly_dark",
                        plot_bgcolor="#0d1117",
                        paper_bgcolor="#0d1117",
                        font=dict(color="#c9d1d9"),
                        xaxis_title="Estado",
                        yaxis_title="Quantidade"
                    )

                    st.plotly_chart(fig_state, use_container_width=True)

            with col_chart2:
                if "Priority" in df.columns:
                    st.markdown("### ⚠️ Tickets por Prioridade")
                    priority_counts = df["Priority"].value_counts()

                    fig_priority = go.Figure(data=[go.Pie(
                        labels=priority_counts.index,
                        values=priority_counts.values,
                        hole=0.4,
                        marker_colors=['#f85149', '#d29922', '#2f81f7', '#8b949e']
                    )])

                    fig_priority.update_layout(
                        height=400,
                        template="plotly_dark",
                        plot_bgcolor="#0d1117",
                        paper_bgcolor="#0d1117",
                        font=dict(color="#c9d1d9")
                    )

                    st.plotly_chart(fig_priority, use_container_width=True)

            st.markdown("---")

            # ========================================
            # GRÁFICO DE LINHA DO TEMPO
            # ========================================
            if "Created" in df.columns:
                st.markdown("### 📈 Security Tickets Criados ao Longo do Tempo")
                try:
                    df_timeline = df.copy()
                    df_timeline["Created_Date"] = pd.to_datetime(df_timeline["Created"], errors='coerce')
                    df_timeline = df_timeline.dropna(subset=["Created_Date"])

                    if not df_timeline.empty:
                        timeline_data = df_timeline.groupby(df_timeline["Created_Date"].dt.date).size().reset_index(name='count')

                        fig_timeline = go.Figure(data=[go.Scatter(
                            x=timeline_data["Created_Date"],
                            y=timeline_data["count"],
                            mode='lines+markers',
                            line=dict(color='#f85149', width=2),
                            marker=dict(size=6),
                            fill='tozeroy',
                            fillcolor='rgba(248, 81, 73, 0.1)'
                        )])

                        fig_timeline.update_layout(
                            height=350,
                            template="plotly_dark",
                            plot_bgcolor="#0d1117",
                            paper_bgcolor="#0d1117",
                            font=dict(color="#c9d1d9"),
                            xaxis_title="Data",
                            yaxis_title="Número de Tickets"
                        )

                        st.plotly_chart(fig_timeline, use_container_width=True)
                except Exception as e:
                    logger.error(f"Error creating timeline chart: {str(e)}")
                    st.warning("⚠️ Não foi possível criar o gráfico de linha do tempo")

            st.markdown("---")

            # OCULTAR COLUNAS TÉCNICAS
            hidden_cols = ["upload_id", "uploaded_at", "source_filename"]
            df_visible = df.drop(columns=hidden_cols, errors="ignore")

            # ========================================
            # TABELA DE TICKETS
            # ========================================
            st.markdown("### 📋 Tabela Detalhada de Security Tickets")
            st.dataframe(df_visible, use_container_width=True, height=400)

            # ========================================
            # DOWNLOADS
            # ========================================
            try:
                logger.info("Preparing download files for security tickets")
                csv_data = df_visible.to_csv(index=False).encode("utf-8")
                excel_data = df_to_excel_bytes(df_visible)

                col_d1, col_d2 = st.columns(2)

                with col_d1:
                    st.download_button(
                        "📥 Download CSV",
                        data=csv_data,
                        file_name="security_tickets.csv",
                        mime="text/csv"
                    )

                with col_d2:
                    if excel_data:
                        st.download_button(
                            "📥 Download Excel",
                            data=excel_data,
                            file_name="security_tickets.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.error("❌ Erro ao gerar arquivo Excel")

                logger.info("Download buttons prepared successfully for security tickets")
            except Exception as e:
                logger.error(f"Error preparing downloads: {str(e)}", exc_info=True)
                st.error(f"❌ Error preparing downloads: {str(e)}")

    # ========================================
    # SECURITY TAB 2: SECURITY EFFORT
    # ========================================
    with sec_tab2:
        # Botão para ativar esta aba
        if st.button("⏱️", key="sec_tab2_btn", help="Ativar base Security Effort"):
            st.session_state["active_tab"] = "Security Effort"
            st.rerun()

        st.markdown("## ⏱️ Security Effort Dashboard")

        # Verificar se há dados carregados
        if df.empty:
            st.info("📋 **Nenhum dado carregado**")
            st.markdown("""
            ### Como começar:
            1. ⏱️ **Ative esta base**: Clique no botão ⏱️ acima
            2. 📤 **Upload**: Carregue um arquivo Excel de security effort no menu lateral
            3. 💾 **Salvar**: Salve o arquivo na base de dados
            4. 📥 **Carregar**: Carregue os dados salvos
            5. 🔍 **Filtrar**: Use os filtros para visualizar dados específicos
            """)
        else:
            # ========================================
            # MÉTRICAS PRINCIPAIS
            # ========================================
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total de Tarefas", len(df))

            with col2:
                # Calcular total de horas
                total_hours = 0
                if "Hours" in df.columns:
                    try:
                        total_hours = pd.to_numeric(df["Hours"], errors='coerce').sum()
                    except:
                        total_hours = 0
                st.metric("Total de Horas", f"{total_hours:.1f}")

            with col3:
                # Contar recursos únicos
                unique_resources = df["Resource"].nunique() if "Resource" in df.columns else 0
                st.metric("Recursos", unique_resources)

            with col4:
                # Contar projetos únicos
                unique_projects = df["Project"].nunique() if "Project" in df.columns else 0
                st.metric("Projetos", unique_projects)

            st.markdown("---")

            # ========================================
            # GRÁFICOS DE VISUALIZAÇÃO
            # ========================================
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                if "Activity Type" in df.columns:
                    st.markdown("### 📊 Horas por Tipo de Atividade")
                    try:
                        df_hours = df.copy()
                        df_hours["Hours_Num"] = pd.to_numeric(df_hours["Hours"], errors='coerce').fillna(0)
                        activity_hours = df_hours.groupby("Activity Type")["Hours_Num"].sum().sort_values(ascending=False)

                        fig_activity = go.Figure(data=[go.Bar(
                            x=activity_hours.index,
                            y=activity_hours.values,
                            marker_color='#2ea043',
                            text=[f"{h:.1f}h" for h in activity_hours.values],
                            textposition='auto',
                        )])

                        fig_activity.update_layout(
                            height=400,
                            template="plotly_dark",
                            plot_bgcolor="#0d1117",
                            paper_bgcolor="#0d1117",
                            font=dict(color="#c9d1d9"),
                            xaxis_title="Tipo de Atividade",
                            yaxis_title="Horas"
                        )

                        st.plotly_chart(fig_activity, use_container_width=True)
                    except Exception as e:
                        logger.error(f"Error creating activity chart: {str(e)}")
                        st.warning("⚠️ Erro ao criar gráfico de atividades")

            with col_chart2:
                if "Project" in df.columns:
                    st.markdown("### 📁 Horas por Projeto")
                    try:
                        df_hours = df.copy()
                        df_hours["Hours_Num"] = pd.to_numeric(df_hours["Hours"], errors='coerce').fillna(0)
                        project_hours = df_hours.groupby("Project")["Hours_Num"].sum().sort_values(ascending=False).head(10)

                        fig_project = go.Figure(data=[go.Pie(
                            labels=project_hours.index,
                            values=project_hours.values,
                            hole=0.4,
                            marker_colors=['#2ea043', '#2f81f7', '#d29922', '#8b949e', '#bc8cff', '#ff7b72', '#56d364', '#f85149']
                        )])

                        fig_project.update_layout(
                            height=400,
                            template="plotly_dark",
                            plot_bgcolor="#0d1117",
                            paper_bgcolor="#0d1117",
                            font=dict(color="#c9d1d9")
                        )

                        st.plotly_chart(fig_project, use_container_width=True)
                    except Exception as e:
                        logger.error(f"Error creating project chart: {str(e)}")
                        st.warning("⚠️ Erro ao criar gráfico de projetos")

            st.markdown("---")

            # ========================================
            # GRÁFICO DE LINHA DO TEMPO
            # ========================================
            if "Date" in df.columns:
                st.markdown("### 📈 Horas Trabalhadas ao Longo do Tempo")
                try:
                    df_timeline = df.copy()
                    df_timeline["Date_Parsed"] = pd.to_datetime(df_timeline["Date"], errors='coerce')
                    df_timeline["Hours_Num"] = pd.to_numeric(df_timeline["Hours"], errors='coerce').fillna(0)
                    df_timeline = df_timeline.dropna(subset=["Date_Parsed"])

                    if not df_timeline.empty:
                        timeline_data = df_timeline.groupby(df_timeline["Date_Parsed"].dt.date)["Hours_Num"].sum().reset_index()
                        timeline_data.columns = ["Date", "Hours"]

                        fig_timeline = go.Figure(data=[go.Scatter(
                            x=timeline_data["Date"],
                            y=timeline_data["Hours"],
                            mode='lines+markers',
                            line=dict(color='#2ea043', width=2),
                            marker=dict(size=6),
                            fill='tozeroy',
                            fillcolor='rgba(46, 160, 67, 0.1)'
                        )])

                        fig_timeline.update_layout(
                            height=350,
                            template="plotly_dark",
                            plot_bgcolor="#0d1117",
                            paper_bgcolor="#0d1117",
                            font=dict(color="#c9d1d9"),
                            xaxis_title="Data",
                            yaxis_title="Horas"
                        )

                        st.plotly_chart(fig_timeline, use_container_width=True)
                except Exception as e:
                    logger.error(f"Error creating timeline chart: {str(e)}")
                    st.warning("⚠️ Não foi possível criar o gráfico de linha do tempo")

            st.markdown("---")

            # OCULTAR COLUNAS TÉCNICAS
            hidden_cols = ["upload_id", "uploaded_at", "source_filename"]
            df_visible = df.drop(columns=hidden_cols, errors="ignore")

            # ========================================
            # TABELA DE EFFORT
            # ========================================
            st.markdown("### 📋 Tabela Detalhada de Security Effort")
            st.dataframe(df_visible, use_container_width=True, height=400)

            # ========================================
            # DOWNLOADS
            # ========================================
            try:
                logger.info("Preparing download files for security effort")
                csv_data = df_visible.to_csv(index=False).encode("utf-8")
                excel_data = df_to_excel_bytes(df_visible)

                col_d1, col_d2 = st.columns(2)

                with col_d1:
                    st.download_button(
                        "📥 Download CSV",
                        data=csv_data,
                        file_name="security_effort.csv",
                        mime="text/csv"
                    )

                with col_d2:
                    if excel_data:
                        st.download_button(
                            "📥 Download Excel",
                            data=excel_data,
                            file_name="security_effort.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.error("❌ Erro ao gerar arquivo Excel")

                logger.info("Download buttons prepared successfully for security effort")
            except Exception as e:
                logger.error(f"Error preparing downloads: {str(e)}", exc_info=True)
                st.error(f"❌ Error preparing downloads: {str(e)}")
