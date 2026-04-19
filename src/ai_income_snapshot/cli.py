from __future__ import annotations

import argparse
from pathlib import Path

from .pipeline import RadarCapitalPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="radar-capital",
        description="Radar de Capital Publico: genera snapshot de leads a partir de BOE/BOCM/BDNS",
    )

    parser.add_argument(
        "run",
        nargs="?",
        default="run",
        help="Comando principal (run).",
    )
    parser.add_argument(
        "--companies",
        default="data/sample_companies.csv",
        help="CSV con empresas candidatas (default: data/sample_companies.csv)",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directorio base para resultados (default: outputs)",
    )
    parser.add_argument(
        "--topics",
        default="",
        help="Lista de temas separada por coma. Ej: digitalizacion,innovacion,eficiencia energetica",
    )
    parser.add_argument(
        "--calibration-file",
        default="config/calibracion_despacho.json",
        help="JSON de calibración comercial del despacho (default: config/calibracion_despacho.json)",
    )
    parser.add_argument(
        "--auto-discover-companies",
        action="store_true",
        help="Descubre empresas automáticamente desde BDNS/concesiones (ignora --companies).",
    )
    parser.add_argument(
        "--max-discovered-companies",
        type=int,
        default=100,
        help="Límite de empresas a descubrir automáticamente (default: 100).",
    )
    parser.add_argument(
        "--discovery-region-filter",
        default="",
        help="Filtro textual de región para descubrimiento automático (ej: madrid).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.run != "run":
        parser.error("Comando no soportado. Usa: radar-capital run ...")

    topics = [topic.strip() for topic in args.topics.split(",") if topic.strip()]
    companies_path = Path(args.companies)
    if not args.auto_discover_companies and companies_path.name == "clientes_produccion_template.csv":
        parser.error(
            "Estás usando la plantilla demo en modo manual. "
            "Activa --auto-discover-companies o pasa un CSV real."
        )

    pipeline = RadarCapitalPipeline()
    result = pipeline.run(
        companies_csv_path=None if args.auto_discover_companies else companies_path,
        output_dir=Path(args.output_dir),
        topics=topics or None,
        calibration_file=Path(args.calibration_file),
        auto_discover_companies=args.auto_discover_companies,
        max_discovered_companies=args.max_discovered_companies,
        discovery_region_filter=args.discovery_region_filter,
    )

    print("Snapshot generado correctamente")
    print(f"Directorio de salida: {result.run_directory}")
    print(f"Empresas origen: {result.companies_source}")
    print(f"Empresas entrada: {result.companies_input_count}")
    print(f"Empresas filtradas fuera: {result.companies_filtered_out_count}")
    print(f"Empresas procesadas: {result.companies_count}")
    print(f"Leads evaluados: {len(result.leads)}")
    print(f"Convocatorias analizadas: {result.opportunities_count}")
    print(f"Señales BOE/BOCM detectadas: {result.bulletin_signals_count}")


if __name__ == "__main__":
    main()
