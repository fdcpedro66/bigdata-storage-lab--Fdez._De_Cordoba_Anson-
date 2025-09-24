from __future__ import annotations

import io
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

# Importa utilidades del pipeline (ya creadas en src/)
from src.transform import normalize_columns, to_silver
from src.validate import basic_checks
from src.ingest import tag_lineage, concat_bronze


# ---------- Utilidades internas de la app ----------

def _read_csv_safely(uploaded_file) -> pd.DataFrame:
    """
    Lee un CSV intentando primero UTF-8 y, si falla, Latin-1.
    Usa inferencia de separador (sep=None, engine='python').
    """
    raw: bytes = uploaded_file.read()
    # Prepara dos intentos de decodificación
    for enc in ("utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            return pd.read_csv(io.StringIO(text), sep=None, engine="python")
        except Exception:
            continue
    # Si todo falla, relanza el último error
    raise ValueError(f"No se pudo leer el CSV '{uploaded_file.name}' con UTF-8 ni Latin-1.")


def _parse_candidates(text: str) -> List[str]:
    """Divide el input por comas para permitir sinónimos: 'Fecha, transaction_date'."""
    if not text:
        return []
    return [t.strip() for t in text.split(",") if t.strip()]


def _find_first_match(columns: List[str], candidates: List[str]) -> Optional[str]:
    """
    Busca la primera coincidencia (case-insensitive, trim) de 'candidates' en 'columns'.
    Devuelve el nombre real de la columna si la encuentra.
    """
    norm_map = {c.lower().strip(): c for c in columns}
    for cand in candidates:
        key = cand.lower().strip()
        if key in norm_map:
            return norm_map[key]
    return None


def _build_mapping_for_df(df: pd.DataFrame, user_map_inputs: Dict[str, str]) -> Dict[str, str]:
    """
    Construye un mapping origen->canónico específico para el DF usando
    posibles sinónimos introducidos por el usuario.
      user_map_inputs = {'date': 'Fecha, transaction_date', 'partner': 'Cliente', 'amount': 'Total €'}
    Devuelve: {'Fecha':'date'} o {'transaction_date':'date'}, etc. según lo que exista en df.columns.
    """
    mapping: Dict[str, str] = {}
    cols = list(df.columns)

    for target in ("date", "partner", "amount"):
        candidates = _parse_candidates(user_map_inputs.get(target, ""))
        match = _find_first_match(cols, candidates)
        if match:
            mapping[match] = target  # origen -> canónico
    return mapping


def _kpis_bronze(df: pd.DataFrame) -> Dict[str, object]:
    """KPIs simples para la tabla bronze."""
    out: Dict[str, object] = {}
    out["filas"] = int(len(df))
    out["partners_unicos"] = int(df["partner"].nunique(dropna=True)) if "partner" in df else 0
    if "amount" in df:
        out["importe_total_eur"] = float(pd.to_numeric(df["amount"], errors="coerce").sum(skipna=True))
    else:
        out["importe_total_eur"] = 0.0

    if "date" in df and pd.api.types.is_datetime64_any_dtype(df["date"]) and not df["date"].dropna().empty:
        out["rango_fechas"] = f"{df['date'].min().date()} → {df['date'].max().date()}"
    else:
        out["rango_fechas"] = "N/D"
    return out


# ---------- UI principal ----------

st.set_page_config(page_title="Almacén Analítico – Bronze/Silver", layout="wide")

st.title("De CSVs heterogéneos a un almacén analítico confiable")
st.markdown(
    "Sube uno o varios **CSV** heterogéneos, define el **mapeo de columnas** en la barra lateral "
    "y obtén una capa **Bronze** unificada. Si pasa las validaciones, se derivará la capa **Silver**."
)

# Barra lateral: mapeos de columnas de origen -> canónicas
st.sidebar.header("Mapeos de columnas (origen → canónico)")
st.sidebar.caption(
    "Puedes escribir varias opciones separadas por coma para cada campo. "
    "Ej.: `Fecha, transaction_date`"
)

date_input = st.sidebar.text_input("Columna(s) para `date`", value="Fecha, transaction_date")
partner_input = st.sidebar.text_input("Columna(s) para `partner`", value="Cliente, vendor_name")
amount_input = st.sidebar.text_input("Columna(s) para `amount`", value="Total €, amount_eur")

user_map_inputs = {"date": date_input, "partner": partner_input, "amount": amount_input}

# Uploader de múltiples CSV
uploaded = st.file_uploader(
    "Sube tus CSV (puedes arrastrar varios a la vez):",
    type=["csv"],
    accept_multiple_files=True,
    help="La app intentará UTF-8 y, si falla, Latin-1. El separador se infiere automáticamente."
)

bronze_frames: List[pd.DataFrame] = []
read_errors: List[str] = []

if uploaded:
    st.subheader("Archivos subidos")
    for file in uploaded:
        st.write(f"• **{file.name}**")

    with st.spinner("Procesando archivos..."):
        for file in uploaded:
            try:
                df_raw = _read_csv_safely(file)
                # IMPORTANTE: reposicionar el cursor del fichero si se vuelve a leer
                file.seek(0)

                # Construye mapping adecuado a este DF según inputs de usuario
                mapping = _build_mapping_for_df(df_raw, user_map_inputs)
                if not mapping:
                    st.warning(f"[{file.name}] No se encontró ninguna columna que coincida con los mapeos indicados.")
                    continue

                # Normaliza columnas y añade linaje
                df_norm = normalize_columns(df_raw, mapping)
                df_tagged = tag_lineage(df_norm, source_name=file.name)
                bronze_frames.append(df_tagged)

            except Exception as e:
                read_errors.append(f"{file.name}: {e}")

# Consolida bronze
bronze = concat_bronze(bronze_frames) if bronze_frames else pd.DataFrame(
    columns=["date", "partner", "amount", "source_file", "ingested_at"]
)

# Mostrar posibles errores de lectura
if read_errors:
    st.error("Algunos archivos no pudieron procesarse:")
    for err in read_errors:
        st.write(f"- {err}")

# Tabla Bronze unificada
st.subheader("Capa Bronze (unificada)")
st.dataframe(bronze, use_container_width=True)

# Validaciones sobre columnas canónicas
st.subheader("Validaciones (basic_checks)")
if bronze.empty:
    st.info("Sube archivos y define correctamente los mapeos para generar Bronze.")
    errors: List[str] = []
else:
    # Solo validamos las columnas canónicas (date/partner/amount)
    to_check = bronze[["date", "partner", "amount"]].copy()
    errors = basic_checks(to_check)

if errors:
    st.error("❌ Hay problemas que debes corregir antes de generar Silver:")
    for e in errors:
        st.write(f"- {e}")
else:
    st.success("✅ Validaciones superadas. Se puede derivar la capa Silver.")

# KPIs y Silver (solo si pasa validaciones y no está vacío)
if not bronze.empty and not errors:
    st.subheader("Capa Silver (partner × mes)")

    # Derivar silver desde las canónicas
    silver = to_silver(bronze[["date", "partner", "amount"]])

    # KPIs básicos de Bronze (visión rápida)
    kpi = _kpis_bronze(bronze)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Filas Bronze", kpi["filas"])
    c2.metric("Partners únicos", kpi["partners_unicos"])
    c3.metric("Importe total (EUR)", f"{kpi['importe_total_eur']:.2f}")
    c4.metric("Rango de fechas", kpi["rango_fechas"])

    st.markdown("**Tabla Silver**")
    st.dataframe(silver, use_container_width=True)

    # Gráfico simple: importe por mes
    st.markdown("**Importe por mes (Silver)**")
    by_month = silver.groupby("month", as_index=False)["amount"].sum()
    # Streamlit usa su propio tema; no configuramos colores ni estilos
    st.bar_chart(by_month, x="month", y="amount")

    # Descargas
    st.markdown("### Descargas")
    bronze_csv = bronze.to_csv(index=False).encode("utf-8")
    silver_csv = silver.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Descargar bronze.csv", data=bronze_csv, file_name="bronze.csv", mime="text/csv")
    st.download_button("⬇️ Descargar silver.csv", data=silver_csv, file_name="silver.csv", mime="text/csv")
else:
    # Aun así, permite descargar Bronze si existe
    if not bronze.empty:
        st.markdown("### Descarga Bronze")
        bronze_csv = bronze.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Descargar bronze.csv", data=bronze_csv, file_name="bronze.csv", mime="text/csv")


# Pie de página sobrio
st.caption(
    "Tip: en los mapeos puedes escribir múltiples sinónimos separados por coma. "
    "Ej.: `Fecha, Fec_Oper, transaction_date`."
)

