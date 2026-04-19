# Calibración de Scoring para Despacho

## Objetivo

Ajustar el ranking de leads para que no dependa solo de señales técnicas (encaje, intención, histórico), sino de la realidad comercial del despacho.

## Fichero de calibración

Ruta por defecto:

- `config/calibracion_despacho.json`

Campos clave:

- `dispatch_weight`: peso comercial sobre score final (0-1).
- `strategic_priority_weight`: peso de `strategic_priority` del cliente potencial.
- `urgency_weight`: peso de `urgency_level`.
- `ticket_weight`: peso de ajuste al ticket objetivo.
- `relationship_weight`: peso del estado de relación comercial.
- `sector_alignment_weight`: peso de encaje entre `service_focus_tags` y `topic_tags` de oportunidad.
- `target_ticket_min_eur` / `target_ticket_max_eur`: rango óptimo de ticket.
- `relationship_scores`: puntuación por estado (`cold`, `warm`, `hot`, `existing_client`).
- `only_private_companies`: filtra sólo empresa privada.
- `excluded_name_keywords`: excluye organismos no objetivo.
- `min_estimated_ticket_eur`: ticket mínimo aceptado.
- `allowed_regions`: regiones permitidas.
- `hot_threshold`, `warm_threshold`, `hot_dispatch_min`: reglas del semáforo comercial.

## CSV de producción

Plantilla:

- `data/clientes_produccion_template.csv`

Columnas comerciales:

- `strategic_priority` (1-5): prioridad estratégica interna.
- `urgency_level` (1-5): urgencia de activación comercial.
- `estimated_ticket_eur`: facturación esperada.
- `relationship_level`: `cold` / `warm` / `hot` / `existing_client`.
- `service_focus_tags`: líneas de servicio del despacho.
- `preferred_regions`: regiones objetivo.

## Receta recomendada de calibración

1. Semana 1-2: `dispatch_weight = 0.25`.
2. Semana 3-4: revisar ratio lead->reunión y subir a `0.30` o `0.35` si prioriza mejor.
3. Si hay poco tiempo comercial disponible:
   - subir `urgency_weight`
   - bajar `ticket_weight`
4. Si buscas rentabilidad por cuenta:
   - subir `ticket_weight`
   - ajustar `target_ticket_min_eur`.

## Ejecución

```bash
radar-capital run \
  --companies data/clientes_produccion_template.csv \
  --output-dir outputs \
  --calibration-file config/calibracion_despacho.json
```

## Señal de calidad mínima (operativa)

Como regla práctica, empieza contactando solo leads con:

- `final_score >= 0.55`
- o `dispatch_score >= 0.70` cuando haya relación `warm/hot`.

## Semáforo comercial

- `HOT`: prioridad inmediata.
- `WARM`: seguimiento en 48-72h.
- `COLD`: mantener en nurturing y revisar en ciclo semanal.

## Personalización comercial por lead

El sistema no se queda en un mensaje genérico por semáforo. Ahora genera:

- `qualification_reason` contextualizado por:
  - empresa concreta
  - convocatoria concreta
  - señales de encaje/intent/histórico
  - prioridad comercial
- `next_action` contextualizado por:
  - tier (`HOT/WARM/COLD`)
  - canal disponible (email sugerido o búsqueda de contacto)
  - referencia de convocatoria
  - histórico de concesiones

Recomendación práctica:

- revisa semanalmente los 10 primeros leads para detectar frases repetitivas
- si detectas demasiada repetición, ajusta:
  - `service_focus_tags` en cartera de empresas
  - temas (`topics`) del run
  - pesos de calibración (`dispatch_weight`, `sector_alignment_weight`)
