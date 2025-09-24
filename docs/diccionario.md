# 📖 Diccionario de Datos Canónico

Este documento define el **esquema canónico** que se usará en la capa Silver del almacén.

---

## Esquema Canónico

| Campo    | Tipo       | Descripción                               | Ejemplo           |
|----------|------------|-------------------------------------------|-------------------|
| `date`   | `string` (YYYY-MM-DD) | Fecha de la transacción en formato ISO.  | `2025-09-24`      |
| `partner`| `string`   | Nombre de la contraparte o entidad.       | `"ACME Corp"`     |
| `amount` | `float` EUR| Importe en euros, decimales con punto.    | `1234.56`         |

---

## Mapeos Origen → Canónico

Ejemplos de cómo distintos CSVs heterogéneos se normalizan al esquema canónico:

| Origen (columna)   | Ejemplo valor     | Canónico (`date`) | Canónico (`partner`) | Canónico (`amount`) |
|--------------------|-------------------|-------------------|-----------------------|----------------------|
| `Fecha`            | `24/09/2025`     | `2025-09-24`      | —                     | —                    |
| `Cliente`          | `ACME SA`        | —                 | `ACME SA`             | —                    |
| `Total €`          | `1.234,56`       | —                 | —                     | `1234.56`            |
| `transaction_date` | `2025/09/24`     | `2025-09-24`      | —                     | —                    |
| `vendor_name`      | `Proveedor X`    | —                 | `Proveedor X`         | —                    |
| `amount_eur`       | `987.65`         | —                 | —                     | `987.65`             |

---

> ℹ️ La tabla de mapeos debe expandirse a medida que se encuentren nuevos orígenes heterogéneos.

