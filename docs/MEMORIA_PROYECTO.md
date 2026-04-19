# Memoria de Proyecto - Radar de Capital Público

Fecha: 20 de abril de 2026

## Resumen ejecutivo

Se ha construido un MVP funcional para detectar oportunidades de subvenciones y transformarlas en leads priorizados para gestorías/consultoras.

El sistema ya cubre:

- captura de convocatorias y señales públicas (BDNS + BOE/BOCM),
- detección de empresas candidatas,
- scoring técnico + comercial,
- interfaz web de operación,
- proceso comercial integrado (funnel + seguimiento por lead).

## Hitos completados

1. Pipeline operativo end-to-end.
2. Descubrimiento automático de empresas reales (sin demo fija).
3. Interfaz web con:
   - run selector
   - descarga de entregables
   - tabla comercial enriquecida
   - actualización de estado/canal/notas/seguimiento
4. Personalización de contenidos por lead:
   - por qué califica
   - siguiente acción
5. Robustez de señales de boletín:
   - BOE con ventana de días y tolerancia a 404/no edición
   - deduplicación de señales

## Entregables actuales

- `leads.csv`
- `boletines_signals.csv`
- `resumen.md`
- base comercial local: `data/sales_pipeline.db` (no versionada)

## Validación pendiente prioritaria

- Validación cualitativa con 1-2 gestorías de confianza.
- Confirmar si:
  - la calidad del lead ahorra tiempo real,
  - la explicación es suficiente para activar contacto,
  - falta algún dato para convertir en reunión.

## Próximo sprint (2 semanas)

1. Ejecutar pruebas con gestorías amigas.
2. Ajustar scoring y copy comercial con feedback real.
3. Cerrar primera prueba de pago.

