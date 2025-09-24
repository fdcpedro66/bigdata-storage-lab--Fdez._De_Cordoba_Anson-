from __future__ import annotations

import pandas as pd


def _normalize_amount_series(s: pd.Series) -> pd.Series:
    """
    Convierte imports con formato EU/US a float (EUR).
    - Quita símbolos y espacios (€, $, etc.).
    - Si hay ',' y '.':
        * Si el último '.' está DESPUÉS del último ',', asumimos decimal '.' (US) -> quitamos comas.
        * Si el último ',' está DESPUÉS del último '.', asumimos decimal ',' (EU) -> quitamos puntos y ',' -> '.'
    - Si solo hay ',', la tratamos como decimal -> ',' -> '.'
    - Si solo hay '.', ya es decimal.
    """
    def _one(x: object) -> float | None:
        t = str(x).strip()
        # Deja solo dígitos, separadores y signo
        import re
        t = re.sub(r"[^\d,.\-]", "", t)

        if "," in t and "." in t:
            last_dot = t.rfind(".")
            last_comma = t.rfind(",")
            if last_dot > last_comma:
                # US: 1,234.56 -> quitar comas
                t = t.replace(",", "")
            else:
                # EU: 1.234,56 -> quitar puntos y cambiar coma por punto
                t = t.replace(".", "").replace(",", ".")
        elif "," in t:
            # Asumimos decimal con coma
            t = t.replace(",", ".")
        # else: solo '.' o solo dígitos -> ya válido

        try:
            return float(t)
        except Exception:
            return None

    return s.map(_one)


def normalize_columns(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """
    Renombra columnas según 'mapping' (origen -> 'date'/'partner'/'amount'),
    parsea 'date' a datetime, normaliza 'amount' (€, formato EU/US) y limpia 'partner'.

    Parameters
    ----------
    df : DataFrame con columnas de origen.
    mapping : dict, p.ej {'Fecha':'date','Cliente':'partner','Total €':'amount'}

    Returns
    -------
    DataFrame con columnas canónicas: ['date','partner','amount']
    """
    if not mapping:
        raise ValueError("El parámetro 'mapping' no puede estar vacío.")

    out = df.rename(columns=mapping).copy()

    # date -> datetime (acepta dd/mm/yyyy y yyyy-mm-dd). dayfirst=True ayuda con formatos EU.
    if "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce", dayfirst=True)

    # partner -> sin espacios extremos ni dobles espacios intermedios
    if "partner" in out.columns:
        out["partner"] = (
            out["partner"]
            .astype(str)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )

    # amount -> float EUR
    if "amount" in out.columns:
        out["amount"] = _normalize_amount_series(out["amount"])

    # Devuelve solo canónicas, en orden
    keep = [c for c in ["date", "partner", "amount"] if c in out.columns]
    return out[keep]


def to_silver(bronze: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega 'amount' por partner y mes.
    - Crea 'month' como inicio de mes (Timestamp).
    - Suma 'amount' por ['partner','month'].

    Requiere: columns ['date','partner','amount'] con 'date' en datetime.
    """
    required = {"date", "partner", "amount"}
    missing = required - set(bronze.columns)
    if missing:
        raise ValueError(f"Faltan columnas en bronze: {missing}")
    if not pd.api.types.is_datetime64_any_dtype(bronze["date"]):
        raise TypeError("La columna 'date' debe ser datetime antes de agregar.")

    df = bronze.copy()
    # Period('M') -> timestamp al inicio de mes (Month Start)
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp("MS")

    silver = (
        df.groupby(["partner", "month"], as_index=False, dropna=False)["amount"]
        .sum()
        .rename(columns={"amount": "amount"})
    )
    return silver[["partner", "month", "amount"]]
