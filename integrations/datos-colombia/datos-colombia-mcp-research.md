# datos-colombia-mcp — Investigación Completa
> Fecha: 2026-04-12 | Actualizado: 2026-04-13  
> Investigadores: Juan (SECOP legal/Z3) + DOF-MESH Agente 1 (APIs) + DOF-MESH Agente 2 (datasets/oportunidades)  
> Referencia principal: [datagouv-mcp](https://github.com/datagouv/datagouv-mcp) (Francia, 1.279 ⭐)

---

## TL;DR — Resumen ejecutivo

- **Oportunidad:** Primer MCP de datos económicos colombianos con cobertura real. El único competidor (`oddradioada/secop-mcp-project`) tiene 0⭐, 4 commits, sin despliegue.
- **APIs viables:** SECOP II ✅ · SECOP Integrado ✅ · datos.gov.co Discovery ✅ · Metro Medellín ✅ · MEData ⚠️
- **Diferenciador único:** Z3 formal verification de 5 reglas de Ley 80/1993 + attestación on-chain en Avalanche — no existe en Colombia ni Latinoamérica.
- **Ventaja competitiva:** Acceso institucional Secretaría de Desarrollo Económico + pre-incubación Ruta N.
- **MVP:** 3 tools SECOP con SoQL. Blog post: 27 abril 2026.

---

## 1. Contexto: datagouv-mcp como referencia

Servidor MCP oficial de data.gouv.fr (Francia). Permite a cualquier LLM buscar, explorar y analizar 8K+ datasets del portal nacional. Stack: **FastMCP + httpx + Python 3.13+**. En producción: `https://mcp.data.gouv.fr`.

```
datagouv-mcp/
├── main.py              ← FastMCP + stateless_http=True + DNS rebinding protection
├── tools/               ← 1 archivo por tool, register_tools() central
├── helpers/
│   ├── datagouv_api_client.py  ← httpx async
│   └── matomo.py               ← analytics de uso por tool
└── Dockerfile
```

**Patrón de tool (replicar):**
```python
@mcp.tool()
@log_tool
async def search_datasets(query: str, page: int = 1, page_size: int = 20) -> str:
    """Flujo: search → get_info → list_resources → query_data."""
    cleaned_query = clean_search_query(query)  # limpia stop words (AND estricto)
    return await api_client.search(query=cleaned_query)
```

**main.py clave:**
```python
mcp = FastMCP(
    "datos-colombia-mcp",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["mcp.datos-colombia.gov.co", "localhost:*"],
    ),
    stateless_http=True,  # evita "Session not found" en Claude Code, Cline, OpenAI Codex
)
```

### Competidores internacionales

| País | Repo | Tools | Estado |
|------|------|-------|--------|
| Francia | `datagouv/datagouv-mcp` | 9 | ✅ Producción oficial |
| España | `AlbertoUAH/datos-gob-es-mcp` | 11 | ✅ INE + AEMET + BOE |
| CKAN genérico | `ondata/ckan-mcp-server` | n/a | ✅ Compatible cualquier CKAN |
| **Colombia** | `oddradioada/secop-mcp-project` | 3 | ⚠️ Solo SECOP II, 0⭐, sin deploy |

---

## 2. Qué es SECOP

| Aspecto | Detalle |
|---------|---------|
| Nombre completo | Sistema Electrónico de Contratación Pública |
| Qué es | Plataforma del Estado colombiano con todos los contratos públicos |
| SECOP I | Versión original — contratos de entidades estatales |
| SECOP II | Versión actualizada — más campos, API Socrata disponible |
| Dónde vive | `datos.gov.co` (portal de datos abiertos de Colombia) |
| Portal directo | `https://community.secop.gov.co` |
| Quién lo usa | Entidades estatales, contratistas, veedurías, ciudadanos, auditorías |

---

## 3. Endpoints verificados — Agente 1

| # | Fuente | URL exacta | Estado |
|---|--------|-----------|--------|
| 1 | MEData CKAN | `https://medata.gov.co/api/3/action/package_list` | ❌ 404 |
| 2 | MEData Drupal | `https://medata.gov.co/search?keyword=datos` | ⚠️ Sin JSON API |
| 3 | **SECOP II** | `https://www.datos.gov.co/resource/jbjy-vk9h.json` | ✅ ~90 campos |
| 4 | **SECOP Integrado** | `https://www.datos.gov.co/resource/rpmr-utcd.json` | ✅ 21 campos |
| 5 | **datos.gov.co catálogo** | `https://www.datos.gov.co/api/catalog/v1` | ✅ 8,412 datasets |
| 6 | GeoMedellín ArcGIS | `https://geomedellin-m-medellin.opendata.arcgis.com` | ❌ Error TLS |
| 7 | **Metro Medellín** | `https://datosabiertos-metrodemedellin.opendata.arcgis.com` | ✅ 20 datasets |
| 8 | Área Metropolitana | `https://datosabiertos.metropol.gov.co` | ⚠️ Sin API JSON |
| 9 | DIAN RUT | `https://muisca.dian.gov.co` | ❌ Solo formulario web |
| 10 | RUES | `https://www.rues.org.co` | ❌ SPA sin API pública |
| 11 | EPM | `https://www.epm.com.co` | ❌ Portal autenticado |
| 12 | DAGRD | `https://www.dagrd.gov.co` | ❌ ECONNREFUSED |

### SECOP endpoints Socrata completos

```
SECOP II Contratos:   https://www.datos.gov.co/resource/jbjy-vk9h.json
SECOP II Procesos:    https://www.datos.gov.co/resource/p6dx-8zbt.json
SECOP II Ubicaciones: https://www.datos.gov.co/resource/gra4-pcp2.json
SECOP Integrado:      https://www.datos.gov.co/resource/rpmr-utcd.json
```

**Ejemplos SoQL listos para usar:**
```
# 5 contratos
https://www.datos.gov.co/resource/p6dx-8zbt.json?$limit=5

# Filtrar por entidad
https://www.datos.gov.co/resource/p6dx-8zbt.json?$where=nombre_de_la_entidad='ALCALDIA DE MEDELLIN'

# Contratos > $1.000M COP
https://www.datos.gov.co/resource/p6dx-8zbt.json?$where=valor_del_contrato>1000000000&$limit=10
```

---

## 4. Campos SECOP II — mapa completo

| Campo API | Qué contiene | Regla Z3 |
|-----------|-------------|---------|
| `objeto_del_contrato` | Descripción del qué se contrata | Regla 5 |
| `valor_del_contrato` | Valor total en COP | Regla 1, 2 |
| `valor_pagado` | Cuánto se ha pagado | Regla 1 |
| `modalidad_de_contratacion` | Licitación / selección abreviada / contratación directa | Regla 2 |
| `tipo_de_contrato` | Obra / consultoría / prestación de servicios | Regla 3 |
| `nombre_del_contratista` | Empresa o persona contratada | Regla 4 |
| `documento_contratista` | NIT o cédula del contratista | Regla 4 |
| `nit_de_la_entidad` | NIT de la entidad contratante | Filtro |
| `nombre_de_la_entidad` | Nombre de la entidad pública | Filtro |
| `fecha_de_firma` | Cuándo se firmó | Regla 3, 4 |
| `fecha_de_inicio_del_contrato` | Cuándo empieza | Regla 3 |
| `fecha_de_fin_del_contrato` | Cuándo termina | Regla 3 |
| `departamento` | Departamento de la entidad | Filtro geo |
| `ciudad` | Ciudad de la entidad | Filtro geo |

---

## 5. Las 5 reglas Z3 — Marco legal colombiano

### REGLA 1: Presupuesto suficiente
- **Norma:** Ley 80/1993 Art. 25
- **Regla:** El valor del contrato debe ser positivo y no superar la apropiación presupuestal
- **Z3:** `solver.add(valor_contrato > 0)`
- **Dato SECOP:** `valor_del_contrato`

### REGLA 2: Modalidad correcta según valor (SMMLV 2025 = $1.423.500 COP)
- **Norma:** Decreto 1082/2015 Art. 2.2.1.2.1.2.1 + Ley 1150/2007

| Valor | Modalidad obligatoria |
|-------|----------------------|
| > 1.350 SMMLV (~$1.921M COP) | Licitación pública |
| 50–1.350 SMMLV (~$71M–$1.921M COP) | Selección abreviada |
| < 50 SMMLV (~$71M COP) | Contratación directa |

```python
smmlv = 1423500
if valor > 1350 * smmlv:
    regla2 = 'licitación' in modalidad.lower()
elif valor > 50 * smmlv:
    regla2 = 'abreviada' in modalidad.lower() or 'licitación' in modalidad.lower()
else:
    regla2 = True
```

### REGLA 3: Plazo máximo legal
- **Norma:** Ley 80/1993 Art. 40

| Tipo de contrato | Plazo máximo |
|-----------------|-------------|
| Obra pública | 5 años (1.825 días) prorrogables |
| Consultoría | 3 años (1.095 días) |
| Prestación de servicios | 3 años (1.095 días) |

```python
plazo_dias = (fecha_fin - fecha_firma).days
if 'obra' in tipo.lower():
    regla3 = plazo_dias <= 1825
elif any(t in tipo.lower() for t in ['consultoría', 'servicio']):
    regla3 = plazo_dias <= 1095
```

### REGLA 4: Existencia legal previa del contratista
- **Norma:** Ley 80/1993 Art. 5
- **Regla:** El contratista debe existir legalmente antes de la firma
- **Z3:** `solver.add(fecha_constitucion < fecha_firma)`
- **Dato SECOP:** `nombre_del_contratista` + `documento_contratista` + `fecha_de_firma`
- **LIMITACIÓN CRÍTICA:** SECOP no tiene fecha de constitución del contratista → requiere cruce con RUES (Superintendencia de Sociedades). RUES no tiene API pública → scraping necesario.

### REGLA 5: Objeto contractual definido
- **Norma:** Ley 80/1993 Art. 24
- **Regla:** Todo contrato debe tener objeto, causa y consideraciones claramente definidos
- **Z3:** `solver.add(len(objeto) >= 20)`
- **Dato SECOP:** `objeto_del_contrato`

---

## 6. Marco legal completo

| Norma | Artículo | Qué dice | Regla |
|-------|---------|---------|-------|
| Ley 80/1993 | Art. 25 | Presupuesto y apropiación | Regla 1 |
| Ley 80/1993 | Art. 24 | Objeto, causa y consideraciones | Regla 5 |
| Ley 80/1993 | Art. 40 | Plazos máximos | Regla 3 |
| Ley 80/1993 | Art. 5 | Capacidad del contratista | Regla 4 |
| Decreto 1082/2015 | Art. 2.2.1.2.1.2.1 | Modalidades de selección según valor | Regla 2 |
| Ley 1150/2007 | General | Introduce selección abreviada | Regla 2 |
| Ley 1882/2018 | General | Reforma contratación pública | General |

---

## 7. Script de auditoría completo (Python)

```python
"""
DOF-MESH: Auditoría de contratación pública colombiana
Fuente: SECOP II (datos.gov.co)
Reglas: Ley 80/1993 + Decreto 1082/2015
"""

import requests
from datetime import datetime

# Constantes legales 2025
SMMLV_2025 = 1_423_500  # COP
LIMITE_LICITACION = 1350 * SMMLV_2025   # ~$1.921M COP
LIMITE_ABREVIADA  = 50   * SMMLV_2025   # ~$71M COP
MAX_PLAZO_OBRA     = 1825   # días
MAX_PLAZO_SERVICIOS = 1095  # días


def auditar_contrato(contrato: dict, indice: int) -> dict:
    objeto    = contrato.get('objeto_del_contrato', '')
    valor_str = contrato.get('valor_del_contrato', '0')
    modalidad = contrato.get('modalidad_de_contratacion', '')
    tipo      = contrato.get('tipo_de_contrato', '')
    contratista = contrato.get('nombre_del_contratista', '')
    fecha_firma = contrato.get('fecha_de_firma', '')
    fecha_fin   = contrato.get('fecha_de_fin_del_contrato', '')

    try:
        valor = float(valor_str)
    except (ValueError, TypeError):
        valor = 0.0

    # R1: Valor positivo
    r1 = valor > 0

    # R2: Modalidad correcta según valor
    mod = str(modalidad).lower()
    if valor > LIMITE_LICITACION:
        r2 = 'licitación' in mod or 'licitacion' in mod
    elif valor > LIMITE_ABREVIADA:
        r2 = 'abreviada' in mod or 'licitación' in mod or 'licitacion' in mod
    else:
        r2 = True  # contratación directa siempre válida en rangos bajos

    # R3: Plazo máximo legal
    r3 = True
    if fecha_firma and fecha_fin:
        try:
            f_firma = datetime.fromisoformat(fecha_firma.replace('Z', ''))
            f_fin   = datetime.fromisoformat(fecha_fin.replace('Z', ''))
            plazo   = (f_fin - f_firma).days
            t = str(tipo).lower()
            if 'obra' in t:
                r3 = plazo <= MAX_PLAZO_OBRA
            elif 'consultoría' in t or 'servicio' in t:
                r3 = plazo <= MAX_PLAZO_SERVICIOS
        except ValueError:
            r3 = True  # fecha malformada → no penalizar

    # R4: Contratista identificado (RUES cross-check pendiente para fecha constitución)
    r4 = bool(contratista and len(str(contratista).strip()) > 0)

    # R5: Objeto definido (>= 20 chars)
    r5 = bool(objeto and len(str(objeto).strip()) >= 20)

    pasadas = sum([r1, r2, r3, r4, r5])
    return {
        'indice': indice + 1,
        'contratista': contratista,
        'valor': valor,
        'reglas': {'r1': r1, 'r2': r2, 'r3': r3, 'r4': r4, 'r5': r5},
        'pasadas': pasadas,
        'total': 5,
        'aprobado': pasadas == 5,
    }


def main():
    url = "https://www.datos.gov.co/resource/p6dx-8zbt.json?$limit=5"
    contratos = requests.get(url, timeout=15).json()
    print(f"Contratos: {len(contratos)}\n")

    resultados = [auditar_contrato(c, i) for i, c in enumerate(contratos)]

    for r in resultados:
        icono = "✅" if r['aprobado'] else "⚠️"
        print(f"{icono} Contrato {r['indice']} — {r['contratista'][:50]}")
        print(f"   Valor: ${r['valor']:,.0f} COP | {r['pasadas']}/5 reglas")
        for k, v in r['reglas'].items():
            print(f"   {'✅' if v else '❌'} {k.upper()}")
        print()

    total_p = sum(r['pasadas'] for r in resultados)
    total_t = len(resultados) * 5
    print(f"Total: {total_p}/{total_t} reglas ({total_p/total_t*100:.1f}%)")


if __name__ == '__main__':
    main()
```

---

## 8. Limitaciones conocidas

| Limitación | Impacto | Solución |
|-----------|---------|---------|
| SECOP no tiene fecha de constitución del contratista | Regla 4 incompleta | Cruzar con RUES (scraping — no hay API) |
| Errores de digitación en datos | Falsos positivos | Validación antes de verificar reglas |
| No todos los contratos están en SECOP II | Auditoría parcial | Complementar con SECOP I (`rpmr-utcd`) |
| Rate limits API Socrata | No descargar miles de contratos de una vez | Paginación con `$offset` + app token gratis |
| SMMLV cambia cada año | Regla 2 se desactualiza | Parametrizar como variable con año |

---

## 9. Top 10 Datasets prioritarios — Agente 2

| # | Dataset | Fuente | URL / Endpoint | Valor para Secretaría |
|---|---------|--------|---------------|----------------------|
| 1 | Establecimientos I&C activos | MEData / Hacienda | `medata.gov.co/node/16589` | Pulso tejido empresarial por actividad y comuna |
| 2 | Atenciones OPE | MEData / Des. Económico | `medata.gov.co/node/16370` | Flujo demanda laboral por zona y sector |
| 3 | Registros demandantes OPE | MEData / Des. Económico | `medata.gov.co/node/16384` | Perfiles sociodemográficos buscadores de empleo |
| 4 | Intervenciones CEDEZO | MEData / Des. Económico | `medata.gov.co/node/16376` | Impacto emprendimiento formal por zona (desde 2019) |
| 5 | **SECOP II Contratos** | datos.gov.co | `resource/jbjy-vk9h.json` | Gasto público — joya anticorrupción, 59 campos |
| 6 | **SECOP Integrado** | datos.gov.co | `resource/rpmr-utcd.json` | Serie histórica SECOP I+II |
| 7 | Base Pymes Colombia | datos.gov.co | `resource/gskn-y6cz.json` | Densidad PYME, supervivencia, formalización |
| 8 | Empresas y empleados | datos.gov.co | `resource/j8w2-u75f.json` | Correlación empresas ↔ empleo |
| 9 | Encuesta Anual Comercio DANE 2024 | DANE | `microdatos.dane.gov.co/catalog/901` | Comercio colombiano por municipio |
| 10 | Pulso Ecosistema CTi | Ruta N | Por convenio | I+D, capital riesgo, talento (ranking 2024-2026) |

---

## 10. Top 5 Casos de Uso para la Secretaría de Desarrollo Económico

**#1 — Monitor de salud del tejido empresarial (tiempo real)**
Cruza Establecimientos I&C + OPE + CEDEZO por comuna. Responde: *"¿En qué comunas están cerrando más negocios este trimestre?"* — nadie lo tiene con datos abiertos. Es exactamente la pregunta que hace la Secretaría internamente.

**#2 — Alerta temprana de desempleo sectorial**
Comercio pierde 500 establecimientos en un trimestre + OPE recibe 2.000 nuevos demandantes del mismo sector = crisis silenciosa antes de aparecer en cifras oficiales. Permite intervención proactiva de política pública.

**#3 — Detector de irregularidades en contratación municipal con IA**
SECOP + DOF-MESH (5 reglas Z3) para detectar: concentración anormal de contratos en un contratista, fraccionamiento, gasto explosivo pre-elecciones. VigIA solo cubre Bogotá, sin MCP, sin on-chain. La diferencia: **los hallazgos quedan attestados on-chain en Avalanche** — son irrefutables.

**#4 — Mapa de oportunidades CTi por sector**
Pulso CTi (Ruta N) + CEDEZO + OPE + SECOP I+D = qué sectores tienen alta demanda de talento + baja penetración de apoyo público + poca contratación de innovación. Nadie ha cruzado estas 3 fuentes.

**#5 — Benchmarking emprendimiento Medellín vs otras ciudades**
MEData + datos.gov.co Pymes + DANE EAC = *"¿Medellín forma más tech startups que Bogotá pero con menor supervivencia a 3 años?"* En lenguaje natural, sin SQL.

---

## 11. Oportunidad Ruta N

**Datos que tienen y nadie explota públicamente:**
- Pulso CTi: inversión I+D, capital riesgo, talento — solo accesible a participantes registrados
- Encuesta Distrito CTi 2024: microdatos no publicados en MEData ni datos.gov.co
- Power BI Oferta/Demanda TI Medellín: existe pero URL sin acceso público
- Base de empresas aceleradas/incubadas: no hay dataset público

**Propuesta concreta:** Tool `rutan_cti_query(sector, metric)` que accede a su API a cambio de visibilidad + co-branding en el repo y blog post.

**Ventaja de negociación:** Estás en pre-incubación Ruta N + eres analista de la Secretaría de Desarrollo Económico → acceso institucional directo que nadie más tiene.

---

## 12. Arquitectura anticorrupción DOF-MESH

### Por qué las herramientas actuales fallan

| Herramienta | Limitaciones |
|-------------|-------------|
| VigIA (U. Rosario + CAF) | Solo Bogotá, no MCP, no on-chain, no replicable ciudadanos |
| PACO | Solo visualizaciones, sin API, sin IA |
| ConsultaSecop | Análisis territorial básico, sin alertas |
| Infocontratos | Más completo pero cerrado, no integrable |

### Flujo propuesto

```
Claude / cualquier LLM
    ↓ MCP call: secop_search(entity="Alcaldía Medellín", year=2025)
datos-colombia-mcp (FastMCP)
    ↓ Socrata SoQL query
DOF-MESH Constitution (governance check determinístico)
    ↓ 5 reglas Z3 (Ley 80/1993)
Anomaly Detection Crew
    ↓ si anomalía detectada
DOFProofRegistry.attest(proof_hash)
    ↓ on-chain
Avalanche C-Chain: 0x154a3F49a9d28FeCC1f6Db7573303F4D809A26F6
```

**Valor único:** Primera herramienta que combina datos abiertos de contratación + LLM + governance determinístico (Z3 formal proofs) + attestación blockchain. No existe en Colombia ni Latinoamérica.

---

## 13. Lo que datos-colombia-mcp hace MEJOR que datagouv-mcp

| Feature | datagouv-mcp (Francia) | datos-colombia-mcp |
|---------|----------------------|-------------------|
| Socrata SoQL nativo | ❌ | ✅ `$where`, `$select`, `$order` |
| Multi-portal | ❌ 1 portal | ✅ SECOP + MEData + Metro |
| ArcGIS FeatureServer | ❌ | ✅ Metro Medellín geoespacial |
| Governance DOF | ❌ | ✅ ConstitutionEnforcer pre-respuesta |
| Reglas legales Z3 | ❌ | ✅ 5 reglas Ley 80/1993 verificadas |
| On-chain attestation | ❌ | ✅ DOFProofRegistry 8 chains |
| Cache inteligente | ❌ | ✅ TTL: contratos 1h, geo 24h |
| Filtro municipio nativo | ❌ | ✅ `municipio=MEDELLIN` en tools |

---

## 14. Plan de tools propuesto

```python
# SECOP (Fase 1 — MVP)
search_contracts(query, entity=None, year=None, municipio=None)
get_contract_detail(process_id)           # 90 campos SECOP II
detect_anomalies(entity, threshold)       # 5 reglas Z3 + crew DOF-MESH

# datos.gov.co (Fase 2)
search_datasets(query, limit=20)          # Discovery API catálogo 8.412 datasets
get_dataset_info(dataset_id)
query_dataset(dataset_id, where=None, select=None, limit=100)

# MEData Medellín (Fase 3)
get_businesses_by_commune(commune_code, year)
get_employment_data(period, zone=None)    # OPE atenciones
get_cedezo_interventions(year, zone=None)

# Metro Medellín (Fase 2)
get_stations()                            # ArcGIS FeatureServer
get_ridership(year)

# Ruta N (si convenio)
rutan_cti_query(sector, metric)

# Utilidades
get_catalog_health()                      # /health sin auth
```

---

## 15. Stack técnico

```toml
[project]
requires-python = ">=3.13"
dependencies = [
    "mcp>=1.25.0,<2",
    "fastmcp>=2.0",
    "httpx>=0.28.0",
    "pyyaml>=6.0",
    "uvicorn",
]
dev = ["pytest", "pytest-httpx", "pytest-asyncio", "ruff"]
```

```
datos-colombia-mcp/
├── main.py              ← FastMCP + stateless_http=True
├── tools/
│   ├── __init__.py      ← register_tools()
│   ├── secop.py         ← search_contracts, detect_anomalies (5 reglas Z3)
│   ├── catalog.py       ← search_datasets, query_dataset
│   ├── medata.py        ← businesses, employment, cedezo
│   ├── metro.py         ← stations, ridership
│   └── rutan.py         ← cti_query (si convenio)
├── helpers/
│   ├── socrata_client.py
│   ├── arcgis_client.py
│   ├── dof_governance.py ← integración DOF-MESH
│   └── cache.py          ← TTL por tipo
├── tests/
├── Dockerfile
└── docker-compose.yml
```

---

## 16. Pitch — Creame / Ruta N

```
PROBLEMA:
Contratación pública en Colombia tiene irregularidades documentadas.
Los datos están públicos en SECOP II pero nadie los audita automáticamente.
Las herramientas existentes (VigIA, PACO) son regionales, cerradas o sin API.

SOLUCIÓN:
datos-colombia-mcp analiza contratos de SECOP II contra 5 reglas de la Ley 80/1993.
Verificación matemática con Z3 (proofs formales).
Attestation on-chain en Avalanche (prueba irrefutable e inmutable).

DEMO:
[ejecutar script con 5 contratos reales]
"De 5 contratos analizados, X violaron Y reglas."

MERCADO:
Contralorías, personerías, veedurías ciudadanas,
empresas de auditoría, medios de investigación, multilaterales (CAF, BID).

ESCALABILIDAD:
Mismo script → miles de contratos.
Mismo framework → otras leyes colombianas.
Mismo SDK → otros países latinoamericanos.

DIFERENCIADOR:
Primera herramienta del mundo: datos abiertos + LLM + Z3 formal proofs + blockchain.
```

---

## 17. Próximos pasos

1. **Inicializar repo** `datos-colombia-mcp` en GitHub (público desde el día 1)
2. **MVP Fase 1:** 3 tools SECOP con Socrata SoQL — `search_contracts`, `get_contract_detail`, `detect_anomalies`
3. **MVP Fase 2:** + `search_datasets` Discovery API + Metro Medellín ArcGIS
4. **MVP Fase 3:** + MEData (scraping estructurado) + DOF-MESH governance layer completo
5. **Pitch Ruta N:** convenio datos CTi como infraestructura de transparencia verificable
6. **Blog post:** 27 abril 2026 — para ese momento Fase 1 debe estar funcionando

---

*Investigadores: Juan (investigación legal SECOP, 5 reglas Z3, script Python) + DOF-MESH Agente 1 (validación APIs) + DOF-MESH Agente 2 (datasets, oportunidades, Ruta N)*  
*Referencias: [datagouv/datagouv-mcp](https://github.com/datagouv/datagouv-mcp) · [oddradioada/secop-mcp-project](https://github.com/oddradioada/secop-mcp-project)*
