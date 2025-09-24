from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List
import pandas as pd


def tag_lineage(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """
    Añade linaje:
      - source_file: nombre/identificador del origen.
      - ingested_at: timestamp UTC ISO 8601 (mismo para todas las filas del df).
    """
    stamped = df.copy()
    ts = datetime.now(timezone.utc).isoformat()
    stamped["source_file"] = source_name
    stamped["ingested_at"] = ts
    return stamped


def concat_bronze(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    """
    Concatena varios DataFrames ya normalizados y con linaje.
    Devuelve el esquema en este orden:
      ['date', 'partner', 'amount', 'source_file', 'ingested_at']
    Si alguna columna falta en un frame, se crea como NaN.
    """
    cols: List[str] = ["date", "partner", "amount", "source_file", "ingested_at"]
    prepared: List[pd.DataFrame] = []

    for f in frames:
        g = f.copy()
        for c in cols:
            if c not in g.columns:
                g[c] = pd.NA
        prepared.append(g[cols])

    if not prepared:
        return pd.DataFrame(columns=cols)

    bronze = pd.concat(prepared, ignore_index=True)
    return bronze

