from __future__ import annotations

import argparse
import re
from pathlib import Path

from flask import Flask, abort, render_template, request, send_file

from .pipeline import RadarCapitalPipeline
from .sales_process import (
    CHANNEL_OPTIONS,
    STATUS_OPTIONS,
    funnel_stats,
    get_leads_for_run,
    get_run,
    init_sales_db,
    list_runs,
    save_run_and_leads,
    update_lead_progress,
)

ALLOWED_OUTPUT_FILES = {"leads.csv", "resumen.md", "boletines_signals.csv"}
SALES_DB_PATH = Path("data/sales_pipeline.db")


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")
    app.config["RUN_DIRECTORIES"] = {}
    app.config["SALES_DB_PATH"] = SALES_DB_PATH
    init_sales_db(SALES_DB_PATH)

    @app.route("/", methods=["GET", "POST"])
    def index() -> str:
        form_data = {
            "companies_path": "data/clientes_produccion_template.csv",
            "output_dir": "outputs",
            "calibration_file": "config/calibracion_despacho.json",
            "topics": "",
            "auto_discover_companies": "1",
            "max_discovered_companies": "100",
            "discovery_region_filter": "",
        }

        context = {
            "form_data": form_data,
            "error_message": "",
            "success_message": "",
            "summary": None,
            "leads": [],
            "download_links": [],
            "runs": [],
            "selected_run_id": "",
            "funnel": None,
            "status_options": STATUS_OPTIONS,
            "channel_options": CHANNEL_OPTIONS,
        }

        sales_db = app.config["SALES_DB_PATH"]
        selected_run_id = (request.args.get("run_id") or "").strip()

        if request.method == "POST":
            action = (request.form.get("action") or "run_pipeline").strip()

            if action == "update_lead":
                selected_run_id = (request.form.get("selected_run_id") or "").strip()
                lead_id = parse_positive_int(request.form.get("lead_id") or "", default=0)
                status = (request.form.get("status") or "NUEVO").strip()
                channel = (request.form.get("channel") or "").strip()
                next_follow_up_date = (request.form.get("next_follow_up_date") or "").strip()
                notes = (request.form.get("notes") or "").strip()

                try:
                    if lead_id <= 0:
                        raise ValueError("Lead no válido para actualizar.")
                    update_lead_progress(
                        db_path=sales_db,
                        lead_id=lead_id,
                        status=status,
                        notes=notes,
                        channel=channel,
                        next_follow_up_date=next_follow_up_date,
                    )
                    context["success_message"] = "Lead comercial actualizado correctamente."
                except Exception as error:  # noqa: BLE001
                    context["error_message"] = f"Error actualizando lead: {error}"

            else:
                form_data["companies_path"] = (request.form.get("companies_path") or "").strip() or form_data["companies_path"]
                form_data["output_dir"] = (request.form.get("output_dir") or "").strip() or form_data["output_dir"]
                form_data["calibration_file"] = (
                    (request.form.get("calibration_file") or "").strip() or form_data["calibration_file"]
                )
                form_data["topics"] = (request.form.get("topics") or "").strip()
                form_data["auto_discover_companies"] = "1" if request.form.get("auto_discover_companies") else ""
                form_data["max_discovered_companies"] = (
                    (request.form.get("max_discovered_companies") or "").strip() or form_data["max_discovered_companies"]
                )
                form_data["discovery_region_filter"] = (request.form.get("discovery_region_filter") or "").strip()
                context["form_data"] = form_data

                try:
                    companies_path = Path(form_data["companies_path"])
                    output_dir = Path(form_data["output_dir"])
                    calibration_file = Path(form_data["calibration_file"])
                    topics = parse_topics(form_data["topics"])
                    auto_discover = bool(form_data["auto_discover_companies"])
                    max_discovered_companies = parse_positive_int(form_data["max_discovered_companies"], default=100)
                    discovery_region_filter = form_data["discovery_region_filter"]

                    if not auto_discover and companies_path.name == "clientes_produccion_template.csv":
                        raise ValueError(
                            "Estás en modo CSV manual con la plantilla demo. "
                            "Activa descubrimiento automático o usa un CSV real."
                        )

                    pipeline = RadarCapitalPipeline()
                    result = pipeline.run(
                        companies_csv_path=None if auto_discover else companies_path,
                        output_dir=output_dir,
                        topics=topics or None,
                        calibration_file=calibration_file,
                        auto_discover_companies=auto_discover,
                        max_discovered_companies=max_discovered_companies,
                        discovery_region_filter=discovery_region_filter,
                    )

                    run_id = result.run_directory.name
                    selected_run_id = run_id
                    app.config["RUN_DIRECTORIES"][run_id] = result.run_directory

                    save_run_and_leads(
                        db_path=sales_db,
                        run_metadata={
                            "run_id": run_id,
                            "run_directory": str(result.run_directory),
                            "companies_source": result.companies_source,
                            "companies_input_count": result.companies_input_count,
                            "companies_count": result.companies_count,
                            "companies_filtered_out_count": result.companies_filtered_out_count,
                            "opportunities_count": result.opportunities_count,
                            "bulletin_signals_count": result.bulletin_signals_count,
                            "topics": ",".join(topics),
                        },
                        leads=result.leads,
                    )

                    context["success_message"] = "Pipeline ejecutado y proceso comercial creado correctamente."
                except Exception as error:  # noqa: BLE001
                    context["error_message"] = f"Error ejecutando el pipeline: {error}"

        context["form_data"] = form_data

        runs = list_runs(sales_db)
        context["runs"] = runs

        if not selected_run_id and runs:
            selected_run_id = str(runs[0]["run_id"])
        context["selected_run_id"] = selected_run_id

        if selected_run_id:
            run_info = get_run(sales_db, selected_run_id)
            if run_info:
                run_directory = Path(run_info["run_directory"])
                app.config["RUN_DIRECTORIES"][selected_run_id] = run_directory

                context["summary"] = {
                    "run_id": run_info["run_id"],
                    "run_directory": run_info["run_directory"],
                    "leads_count": run_info["companies_count"],
                    "companies_count": run_info["companies_count"],
                    "companies_input_count": run_info["companies_input_count"],
                    "companies_filtered_out_count": run_info["companies_filtered_out_count"],
                    "companies_source": humanize_companies_source(run_info["companies_source"]),
                    "opportunities_count": run_info["opportunities_count"],
                    "bulletin_signals_count": run_info["bulletin_signals_count"],
                    "topics": run_info.get("topics", ""),
                    "created_at": run_info.get("created_at", ""),
                }

                context["download_links"] = [
                    {"filename": filename, "run_id": selected_run_id}
                    for filename in sorted(ALLOWED_OUTPUT_FILES)
                ]
                context["leads"] = get_leads_for_run(sales_db, selected_run_id)
                context["funnel"] = funnel_stats(sales_db, selected_run_id)

        return render_template("index.html", **context)

    @app.route("/download/<run_id>/<filename>", methods=["GET"])
    def download_output(run_id: str, filename: str):
        if filename not in ALLOWED_OUTPUT_FILES or not is_safe_run_id(run_id):
            abort(404)

        run_directories: dict[str, Path] = app.config.get("RUN_DIRECTORIES", {})
        run_directory = run_directories.get(run_id)

        if run_directory is None:
            run_info = get_run(app.config["SALES_DB_PATH"], run_id)
            if run_info:
                run_directory = Path(run_info["run_directory"])
            else:
                run_directory = Path("outputs") / run_id

        file_path = run_directory / filename
        if not file_path.exists() or not file_path.is_file():
            abort(404)

        return send_file(file_path, as_attachment=True, download_name=f"{run_id}_{filename}")

    return app


def parse_topics(raw_topics: str) -> list[str]:
    return [topic.strip() for topic in raw_topics.split(",") if topic.strip()]


def parse_positive_int(raw_value: str, default: int = 100) -> int:
    try:
        value = int(raw_value)
    except ValueError:
        return default
    if value <= 0:
        return default
    return value


def humanize_companies_source(source: str) -> str:
    mapping = {
        "csv": "CSV manual",
        "auto_discovery_bdns": "Auto BDNS",
    }
    return mapping.get(source, source)


def is_safe_run_id(run_id: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_-]+", run_id))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="radar-capital-web",
        description="Interfaz web para ejecutar Radar de Capital Publico",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host de escucha (default: 127.0.0.1)")
    parser.add_argument("--port", default=8080, type=int, help="Puerto HTTP (default: 8080)")
    parser.add_argument("--debug", action="store_true", help="Activa modo debug de Flask")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    app = create_app()
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
