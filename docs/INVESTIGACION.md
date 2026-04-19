# Investigación y Validación - AI Income Snapshot

Fecha de validación: **20 de abril de 2026** (Europa/Madrid).

## 1) Tesis de negocio

La hipótesis es sólida: hay volumen alto y continuo de convocatorias públicas, con fricción real en filtrado y priorización, y clientes (consultoras/gestorías) dispuestos a pagar por reducción de tiempo + mayor tasa de cierre.

## 2) Validación técnica (fuentes oficiales)

### 2.1 BOE

- API oficial de sumarios disponible en:
  - `GET /datosabiertos/api/boe/sumario/{fecha}`
  - Documentación: https://www.boe.es/datosabiertos/api/api.php
- Se ha verificado respuesta real en JSON/XML para `20260418`.

### 2.2 BDNS / SNPSAP

- API REST pública documentada en el propio portal (JSON, acceso público):
  - https://www.infosubvenciones.es/bdnstrans/estaticos/doc/snpsap-api.json
  - Swagger público: https://www.infosubvenciones.es/bdnstrans/doc/swagger
- Endpoints relevantes verificados:
  - `/convocatorias/busqueda`
  - `/concesiones/busqueda`
  - `/terceros`
  - `/regiones`
- Evidencia de cobertura y operatividad:
  - El portal publica convocatorias y concesiones con actualización continua.
  - En consultas recientes se han obtenido concesiones con fecha 2026-04-17.

### 2.3 BOCM

- XML diario accesible desde portada (sumario estructurado con `disposicion`):
  - Ejemplo verificado: `https://www.bocm.es/boletin/CM_Boletin_BOCM/2026/04/18/BOCM-20260418091.xml`
- Incluye enlaces por disposición a HTML/XML/PDF, útil para ingestión robusta.

## 3) Validación de demanda operativa

Métricas rápidas ejecutadas sobre SNPSAP (periodo 01/01/2026–17/04/2026):

- Búsqueda por `"subvención"`: **9.229** convocatorias.
- Volumen por temática (España):
  - digitalizacion: 29
  - industria: 163
  - eficiencia energetica: 50
  - innovacion: 134
  - sostenibilidad: 26
- Región Madrid (árbol NUTS en SNPSAP con ids 25/26/27) devuelve volumen no trivial de convocatorias recientes.

Conclusión: hay suficiente caudal para producto recurrente de alertas + scoring.

## 4) Validación comercial (benchmark competitivo)

Referencias visibles en mercado (abril 2026):

- FANDIT precios públicos: https://fandit.es/precios
- AyudaScan precios: https://www.ayudascan.com/precios
- Subventis (BOE alerting): https://www.subventis.es/

Patrón observado:

- Rango de ticket SaaS desde ~20 €/mes hasta varios cientos €/mes según funcionalidades/white-label/API.
- Tu propuesta (750–1.200 €/mes por sector/región) **sí encaja** en segmento premium B2B si el output se centra en leads listos para venta y no solo "alertas".

## 5) Riesgos y guardrails

### 5.1 Riesgo de datos

- SNPSAP avisa de posibles limitaciones ante abuso y cambios dinámicos de datos.
- Guardrail recomendado:
  - cache local
  - paginación controlada
  - ritmo de peticiones moderado
  - reintentos con backoff

### 5.2 Riesgo legal

- Reutilización permitida con condiciones (SNPSAP/BOE), revisar aviso legal del portal.
- Evitar scraping de LinkedIn:
  - User Agreement y prohibición de crawlers/bots: https://www.linkedin.com/legal/user-agreement
  - política de software prohibido: https://www.linkedin.com/help/linkedin/answer/a1341387/prohibited-software-and-extensions
- RGPD/LOPDGDD para contacto B2B:
  - RGPD art. 6 (interés legítimo): https://eur-lex.europa.eu/eli/reg/2016/679/oj
  - LOPDGDD art. 19 (datos de contacto profesionales): https://www.boe.es/eli/es/lo/2018/12/05/3/con

### 5.3 Riesgo de calidad de scoring

- Guardrail recomendado:
  - backtesting mensual contra concesiones reales (precision@k)
  - umbral mínimo de score para entrega comercial
  - etiqueta de confianza por lead

## 6) Unit economics (<100 €/mes)

Posible stack operativo dentro de presupuesto:

- n8n self-hosted (Community): 0 € licencias
- VPS pequeño (Hetzner/OVH/Railway hobby): 5–20 €/mes
- Base de datos (SQLite/Postgres pequeño): 0–15 €/mes
- LLM: uso muy dirigido (solo clasificación/resumen de top leads): 20–50 €/mes
- Email/Slack/Webhook: 0–15 €/mes

Total típico: **25–85 €/mes** si se limita inferencia IA al tramo de mayor valor.

Referencias de costes:

- n8n pricing: https://n8n.io/pricing
- Railway pricing: https://railway.com/pricing
- Anthropic pricing: https://www.anthropic.com/pricing

## 7) Mejoras propuestas sobre tu planteamiento inicial

1. Priorizar **BDNS como spine** y usar BOE/BOCM como señal temprana secundaria.
2. Cambiar “scraping LinkedIn/directorios” por:
   - cartera propia del cliente (CSV/CRM)
   - ficheros públicos permitidos
   - enriquecimiento semántico web opcional
3. Separar salida en dos productos:
   - `Radar Diario` (alerta temprana)
   - `Leads Priorizados` (score + razonamiento + siguiente acción)
4. Introducir métrica contractual de calidad:
   - `% leads aceptados por consultora`
   - `tiempo de activación`
   - `ratio lead->reunión`

## 8) Go / No-Go

**Go condicionado**.

- **Go** técnico: sí, fuentes oficiales disponibles y explotables.
- **Go** económico: sí, viable bajo 100 €/mes en MVP.
- **Go** comercial: sí, si vendes “tiempo ganado + leads accionables” y no mera monitorización.

Riesgo principal no es técnico, es de **calidad comercial del scoring**. Se resuelve con backtest y calibración semanal en las primeras 6–8 semanas.

## 9) Estado actual del producto (20 abril 2026)

Estado implementado en MVP:

- interfaz web operativa con ejecución de runs y gestión comercial por lead
- embudo de ventas por estado (`NUEVO`, `CONTACTADO`, `RESPONDIDO`, `REUNION`, `OFERTA`, `CERRADO_*`, `DESCARTADO`)
- columnas comerciales accionables:
  - enlace de convocatoria
  - resumen de convocatoria
  - por qué califica (personalizado por empresa/oportunidad)
  - siguiente acción (personalizada por lead)
  - contacto sugerido (email + confianza + fuente)
- persistencia en SQLite de runs y evolución comercial
- captura BOE/BOCM reforzada:
  - BOE con escaneo de varios días para evitar vacíos en fines de semana/no publicación
  - deduplicación de señales

## 10) Plan de monetización inicial (30 días, sin equipo)

Objetivo: validar necesidad real y cerrar primer piloto de pago.

Semana 1:

- validar con 1-2 gestorías cercanas (sin coste)
- recoger feedback estructurado de calidad de leads y utilidad comercial

Semana 2:

- ajustar scoring/prompts según feedback
- preparar oferta piloto cerrada (2 semanas, volumen y alcance claros)

Semana 3-4:

- outreach a 30-50 gestorías/consultoras (Madrid + sector digitalización/eficiencia)
- convertir 1-2 pilotos de pago

Pricing orientativo de arranque:

- Piloto: 150-250 € (2 semanas)
- Mensual base: 450-750 € (según volumen y exclusividad de nicho)
- Alternativa: coste por lead validado (35-60 €)

## 11) Guardrails comerciales y legales para outreach

- No usar scraping de LinkedIn para captación automática.
- Comunicar de forma transparente finalidad comercial y ofrecer oposición/baja simple.
- Priorizar contactos profesionales B2B y minimizar datos personales.
- Mantener trazabilidad de fuente y fecha en cada lead para defensa de calidad.

Referencias clave:

- LSSI (art. 21 comunicaciones comerciales): https://www.boe.es/buscar/pdf/2002/BOE-A-2002-13758-consolidado.pdf
- AEPD (publicidad no deseada): https://www.aepd.es/areas-de-actuacion/publicidad-no-deseada
- SNPSAP (reutilización y API pública): https://www.infosubvenciones.es/bdnstrans/estaticos/ayuda/AYUDA%20-%20Sistema%20Nacional%20de%20Publicidad%20de%20Subvenciones%20y%20Ayudas%20P%C3%BAblicas%20v2023.pdf
