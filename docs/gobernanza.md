
# 🛡️ Gobernanza de Datos

Este documento define las prácticas mínimas para asegurar la **calidad, seguridad y trazabilidad** del almacén de datos.

---

## 1. Origen y Linaje
- Todo dataset debe registrar:
  - Fuente de origen (CSV, API, sistema interno).
  - Fecha/hora de ingesta.
  - Responsable del dataset.
- Cada transformación (Bronze → Silver) debe documentarse en logs automáticos.

---

## 2. Validaciones Mínimas
- **Formato de fecha**: obligatorio `YYYY-MM-DD`.
- **Partner**: no vacío, sin caracteres especiales no permitidos.
- **Amount**:
  - Numérico en euros.
  - No nulo.
  - Rango razonable definido por el negocio (ej. `-1e6 ≤ amount ≤ 1e6`).

---

## 3. Política de Mínimos Privilegios
- Acceso diferenciado por capas:
  - **Raw/Bronze**: solo ingenieros de datos.
  - **Silver/Gold**: analistas y científicos de datos.
- Claves/API/credenciales nunca deben estar en repositorios públicos.
- Todo acceso es **read-only** salvo para el rol que mantenga la capa correspondiente.

---

## 4. Trazabilidad
- Cada fila debe poder rastrearse hasta su origen (campo `source_file`, `ingestion_ts`).
- Uso de logs estructurados en cada etapa de ETL.
- Hashes o checksums opcionales para verificar integridad.

---

## 5. Roles
- **Data Engineer**: ingesta, validación, normalización, creación de capas Bronze/Silver.
- **Data Analyst**: explotación de datos en Silver/Gold, generación de KPIs.
- **Data Steward**: asegura calidad, documenta diccionario de datos y políticas.
- **Admin**: gestiona accesos, permisos y cumplimiento de políticas de seguridad.

---
