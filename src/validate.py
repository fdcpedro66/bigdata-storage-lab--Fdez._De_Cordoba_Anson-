from __future__ import annotations

from typing import List
import pandas as pd


def basic_checks(df: pd.DataFrame) -> List[str]:
    """
    Devuelve lista de errores de validación básica sobre el esquema canónico.
    Reglas:
      - Columnas presentes: date, partner, amount.
      - 'date' es datetime64 y sin NaT.
      - 'amount' es numérico, no nulo y >= 0.
    """
    errors: List[str] = []

    # 1) Columnas presentes
    required = {"date", "partner", "amount"}
    missing = required - set(df.columns)
    if missing:
        errors.append(f"Faltan columnas canónicas: {sorted(missing)}")
        return errors  # sin columnas, el resto no tiene sentido

    # 2) date en datetime y sin NaT
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        errors.append("La columna 'date' no es de tipo datetime.")
    else:
        n_nat = int(df["date"].isna().sum())
        if n_nat > 0:
            errors.append(f"'date' contiene {n_nat} valores NaT (no parseables).")

    # 3) amount numérico y >= 0
    if not pd.api.types.is_numeric_dtype(df["amount"]):
        errors.append("La columna 'amount' no es numérica.")
    else:
        n_nan = int(df["amount"].isna().sum())
        n_neg = int((df["amount"] < 0).sum())
        if n_nan > 0:
            errors.append(f"'amount' contiene {n_nan} valores nulos.")
        if n_neg > 0:
            errors.append(f"'amount' contiene {n_neg} valores negativos.")

    # 4) partner no vacío
    if df["partner"].isna().any() or (df["partner"].astype(str).str.strip() == "").any():
        errors.append("Existen 'partner' vacíos o nulos.")

    return errors

