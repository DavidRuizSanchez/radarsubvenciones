# Plantilla n8n - Radar de Capital Público

## Flujo recomendado

1. `Cron`
- Frecuencia: diaria
- Hora: 07:00

2. `Execute Command`
- Comando:
  ```bash
  radar-capital run --companies /data/clientes.csv --output-dir /data/outputs --calibration-file /data/calibracion_despacho.json
  ```

3. `Read Binary File` (opcional)
- Archivo: `/data/outputs/<run_id>/resumen.md`

4. `Slack` o `Email Send`
- Asunto: `Radar de Capital Público - Diario`
- Adjuntar:
  - `leads.csv`
  - `resumen.md`

## Variables útiles

- `SNPSAP_VPD=GE`
- `LOOKBACK_DAYS=45`
- `MAX_PAGES_PER_KEYWORD=2`

## Guardrails de operación

- Si falla el flujo, reintento al día siguiente (no intervención manual inmediata).
- Limitar peticiones concurrentes para evitar bloqueo por abuso.
- Registrar cada ejecución con timestamp y tamaño de salida.
