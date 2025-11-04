import io
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="SOX Controls Dashboard – Streamlit (Gold Edition)", layout="wide")

# --- Theme accents (works with config.toml, but we also style some bits here) ---
GOLD = "#FFD700"
DARK = "#111111"

st.markdown(
    f'''
    <style>
        .block-container {{ padding-top: 1.5rem; }}
        .stApp {{ background: linear-gradient(180deg, #000, #1a1a1a); color: {GOLD}; }}
        .stMarkdown, .stText, .stDownloadButton>button, .stSelectbox label, .stMultiSelect label {{ color: {GOLD} !important; }}
        .stSelectbox>div>div, .stMultiSelect>div>div, .stTextInput>div>div>input {{
            background-color: {DARK} !important; border: 1px solid #B8860B !important; color: {GOLD} !important;
        }}
        table {{ color: #f5f5dc !important; }}
        thead tr th {{ background-color: #111 !important; color: {GOLD} !important; border-bottom: 2px solid #B8860B !important; }}
    </style>
    ''', unsafe_allow_html=True
)

st.markdown(f"<h1 style='text-align:center; color:{GOLD}; text-shadow:0 0 10px #B8860B;'>SOX Controls Dashboard – Streamlit (Gold Edition)</h1>", unsafe_allow_html=True)

# --- Helper functions ---
def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {c: c.strip().lower() for c in df.columns}
    return df.rename(columns=mapping)

def pick(row: pd.Series, *candidates):
    for c in candidates:
        if c in row and pd.notna(row[c]):
            return row[c]
    return ""

def consolidate_fail_reason(df: pd.DataFrame) -> pd.Series:
    cols = [c for c in df.columns if ("failure" in c and "reason" in c)] + ([c for c in df.columns if c == "fail reason"])
    def joiner(r):
        vals = [str(r[c]) for c in cols if c in r and pd.notna(r[c]) and str(r[c]).strip()]
        return " | ".join(vals)
    return df.apply(joiner, axis=1)

def consolidate_root_cause(df: pd.DataFrame) -> pd.Series:
    cols = [c for c in df.columns if ("root" in c and "cause" in c)] + ([c for c in df.columns if c == "root cause"])
    def joiner(r):
        vals = [str(r[c]) for c in cols if c in r and pd.notna(r[c]) and str(r[c]).strip()]
        return " | ".join(vals)
    return df.apply(joiner, axis=1)

def find_column_value(row: pd.Series, includes):
    for c in row.index:
        if all(k in c for k in includes):
            v = row[c]
            if pd.notna(v) and str(v).strip():
                return str(v)
    return ""

def consolidate_test_conclusion(df: pd.DataFrame) -> pd.Series:
    def build(row):
        oe1 = find_column_value(row, ["test", "conclusion", "oe1"])
        oe2 = find_column_value(row, ["test", "conclusion", "oe2"])
        ye  = find_column_value(row, ["test", "conclusion", "ye"])
        parts = []
        if oe1: parts.append(f"OE1: {oe1}")
        if oe2: parts.append(f"OE2: {oe2}")
        if ye:  parts.append(f"YE: {ye}")
        return " | ".join(parts)
    return df.apply(build, axis=1)

def load_dataframe(file) -> pd.DataFrame:
    if file.name.lower().endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file, engine="openpyxl")
    df = normalize_columns(df)

    # Build the working frame
    out = pd.DataFrame()
    out["IT Solution"] = df.get("it solution", df.get("it solutions", ""))
    out["MICS ID"] = df.get("mics id", df.get("micsid", df.get("mics", "")))
    out["Control Owner"] = df.get("control owner", df.get("owner", ""))
    out["Control Executer"] = df.get("control executer", df.get("control executor", df.get("executor", "")))
    out["Control Status"] = df.get("control status", df.get("status", ""))

    # Consolidated Test Conclusion before Fail Reason
    out["Test Conclusion (OE1 / OE2 / YE)"] = consolidate_test_conclusion(df)

    # Consolidated Fail Reason
    out["Fail Reason"] = consolidate_fail_reason(df)

    # Consolidated Root Cause
    out["Root Cause"] = consolidate_root_cause(df)

    return out

# --- UI ---
uploaded = st.file_uploader("Carregue seu arquivo (.xlsx ou .csv) com a mesma estrutura-base", type=["xlsx", "csv"])

if uploaded is None:
    st.info("▶️ Carregue um arquivo para iniciar. O app reconhece variações de nomes de colunas automaticamente (ex.: 'root cause', 'Root_Cause_YE', 'test conclusion - OE1', etc.).")
    st.stop()

df = load_dataframe(uploaded)

# Sidebar filters
st.sidebar.markdown(f"""<h3 style='color:{GOLD}'>Filtros</h3>""", unsafe_allow_html=True)
def multiselect_filter(label, col):
    options = sorted([x for x in df[col].dropna().unique().tolist() if str(x).strip()])
    chosen = st.sidebar.multiselect(label, options, default=[])
    if chosen:
        return df[col].astype(str).isin([str(x) for x in chosen])
    return pd.Series([True]*len(df))

mask = (
    multiselect_filter("IT Solution", "IT Solution") &
    multiselect_filter("MICS ID", "MICS ID") &
    multiselect_filter("Control Owner", "Control Owner") &
    multiselect_filter("Control Executer", "Control Executer") &
    multiselect_filter("Control Status", "Control Status")
)

filtered = df[mask].copy()

# Stats row
left, mid, right = st.columns(3)
left.metric("Total de Controles", len(df))
mid.metric("Filtrados", len(filtered))
status_counts = filtered["Control Status"].fillna("Unknown").value_counts()
right.metric("Status distintos", len(status_counts))

# Table
st.markdown("### Tabela de Controles")
st.dataframe(filtered, use_container_width=True, height=480)

# Download filtered
csv_bytes = filtered.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Exportar CSV (filtrado)", data=csv_bytes, file_name="SOX_Controls_Export.csv", mime="text/csv")

# Simple status chart (bar)
try:
    import altair as alt
    chart_df = status_counts.reset_index()
    chart_df.columns = ["Control Status", "count"]
    st.markdown("### Distribuição por Control Status")
    st.altair_chart(
        alt.Chart(chart_df).mark_bar().encode(
            x=alt.X("Control Status:N", sort='-y'),
            y="count:Q",
            tooltip=["Control Status", "count"]
        ).properties(height=320),
        use_container_width=True
    )
except Exception as e:
    st.caption("Gráfico indisponível (faltou dependência 'altair'). O restante do app funciona normalmente.")
