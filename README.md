# AI Income Snapshot - Radar de Capital Publico

Motor de inteligencia B2B para captar leads de alta conversión en subvenciones, cruzando:

- Convocatorias oficiales (SNPSAP/BDNS)
- Señales tempranas en BOE y BOCM
- Señales de intención en webs de empresas candidatas
- Histórico de concesiones por CIF

El resultado es un `snapshot` accionable en marca blanca con ranking de leads y argumentos de priorización.

## Qué hace este MVP

1. Descarga convocatorias recientes desde `infosubvenciones.es`.
2. Filtra por temas estratégicos (`digitalizacion`, `innovacion`, `eficiencia energetica`, etc.).
3. Cruza ese universo con empresas candidatas (CSV propio).
4. Puntúa cada lead con un score compuesto:
   - `fit_score` (encaje empresa↔convocatoria)
   - `intent_score` (señales de inversión en su web)
   - `history_score` (tracción histórica en BDNS por CIF)
   - `dispatch_score` (prioridad real de despacho: urgencia, ticket, relación, foco sectorial)
   - `lead_tier` (`HOT`, `WARM`, `COLD`) para priorizar acción comercial
5. Filtra calidad comercial:
   - sólo empresas privadas (heurística CIF + forma jurídica)
   - exclusión de organismos públicos por palabras clave
   - ticket mínimo y región permitida (configurable)
6. Exporta:
   - `leads.csv`
   - `boletines_signals.csv`
   - `resumen.md`
   - en web: enlace convocatoria + resumen + motivo de calificación + email sugerido

## Instalación

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Ejecución

```bash
radar-capital run --companies data/sample_companies.csv --output-dir outputs --calibration-file config/calibracion_despacho.json
```

Descubrimiento automático de empresas (sin CSV):

```bash
radar-capital run \
  --auto-discover-companies \
  --max-discovered-companies 150 \
  --discovery-region-filter madrid \
  --output-dir outputs \
  --calibration-file config/calibracion_despacho.json
```

También puedes usar:

```bash
python -m ai_income_snapshot run --companies data/sample_companies.csv
```

## Interfaz Web

Levanta la interfaz web con:

```bash
radar-capital-web --host 127.0.0.1 --port 8080
```

Luego abre:

- `http://127.0.0.1:8080`

Desde esa pantalla puedes:

- indicar CSV de empresas
- activar descubrimiento automático de empresas BDNS
- filtrar descubrimiento por región y limitar número de empresas
- ajustar fichero de calibracion
- ejecutar snapshot
- ver y gestionar runs históricos en un selector
- visualizar embudo comercial por estado (`NUEVO`, `CONTACTADO`, `OFERTA`, etc.)
- actualizar estado, canal, próxima fecha de seguimiento y notas por lead
- usar pitch comercial sugerido por lead para primer contacto
- descargar `leads.csv`, `resumen.md` y `boletines_signals.csv`

Además, cada lead ya incluye en tabla:

- enlace directo a la convocatoria
- resumen de la convocatoria
- motivo explícito de por qué el lead califica
- siguiente acción comercial personalizada
- email sugerido con nivel de confianza y fuente

Nota:

- si desactivas auto-discovery y usas `data/clientes_produccion_template.csv`, la app bloquea la ejecución para evitar resultados demo por error.

## Modo Producción (despacho)

1. Duplica la plantilla:
   - `data/clientes_produccion_template.csv`
2. Rellena cartera real con columnas comerciales:
   - mínimo obligatorio: `name`
   - `strategic_priority` (1-5)
   - `urgency_level` (1-5)
   - `estimated_ticket_eur` (importe esperado)
   - `relationship_level` (`cold`, `warm`, `hot`, `existing_client`)
   - `service_focus_tags` y `preferred_regions`
3. Ajusta pesos en:
   - `config/calibracion_despacho.json`
4. Ejecuta:

```bash
radar-capital run \
  --companies data/clientes_produccion_template.csv \
  --output-dir outputs \
  --calibration-file config/calibracion_despacho.json
```

## Estructura

- `src/ai_income_snapshot/clients/`: conectores BOE, BOCM y BDNS
- `src/ai_income_snapshot/intel/`: matching, señales web y scoring
- `src/ai_income_snapshot/pipeline.py`: orquestación end-to-end
- `src/ai_income_snapshot/web_app.py`: interfaz web para operar sin terminal
- `data/sample_companies.csv`: dataset de ejemplo
- `docs/INVESTIGACION.md`: validación de mercado, riesgos y mejoras

## Integración con n8n (sugerida)

1. Nodo `Cron` diario (07:00).
2. Nodo `Execute Command`:
   - `radar-capital run --companies /ruta/clientes.csv --output-dir /ruta/outputs --calibration-file /ruta/calibracion_despacho.json`
3. Nodo `Read Binary File` + `Send Email` / `Slack` con `resumen.md` y `leads.csv`.

Plantilla orientativa en: `templates/n8n/radar_capital_publico.md`.

## Notas de cumplimiento

- El acceso BDNS/SNPSAP es público e irrestricto, pero sujeto a condiciones de reutilización.
- Evita scraping de LinkedIn para captación automatizada: sus términos lo prohíben.
- Si tratas datos personales, limita a datos profesionales necesarios y aplica RGPD/LOPDGDD.

## Validación Comercial Rápida

Si quieres validar la propuesta con una gestoría de confianza antes de vender:

1. genera un snapshot real con 10-20 leads
2. exporta `resumen.md` y `leads.csv`
3. usa la plantilla de email:
   - `docs/comercial/EMAIL_VALIDACION_GESTORIA.md`
4. pide feedback concreto sobre:
   - calidad de leads
   - claridad de "por qué califica"
   - utilidad de "siguiente acción"
   - datos faltantes para cerrar una llamada comercial

Objetivo recomendado de validación inicial:

- cerrar 2 pruebas reales (sin coste) y convertir al menos 1 en piloto de pago.

## Estado

MVP funcional para validación comercial y técnica.

Actualizado con:

- flujo comercial en interfaz web (embudo, estado, canal, notas y seguimiento),
- explicación y siguiente acción personalizadas por lead,
- captura de señales BOE/BOCM robusta (escaneo de varios días para evitar huecos de publicación),
- persistencia comercial en SQLite por `run`.
