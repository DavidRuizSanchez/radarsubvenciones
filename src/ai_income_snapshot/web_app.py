from __future__ import annotations

import argparse
import re
import threading
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_file

from .jobs import JobTracker
from .pipeline import RadarCapitalPipeline
from .sales_process import (
    CHANNEL_OPTIONS,
    STATUS_OPTIONS,
    count_leads_email_buckets,
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
EMAIL_FILTER_VALUES = {"all", "with", "without"}


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")
    app.config["RUN_DIRECTORIES"] = {}
    app.config["SALES_DB_PATH"] = SALES_DB_PATH
    app.config["JOB_TRACKER"] = JobTracker()
    init_sales_db(SALES_DB_PATH)

    @app.route("/", methods=["GET", "POST"])
    def index() -> str:
        form_data = _default_pipeline_form()

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
            "email_filter": "all",
            "email_counts": {"all": 0, "with": 0, "without": 0},
        }

        sales_db = app.config["SALES_DB_PATH"]
        selected_run_id = (request.args.get("run_id") or "").strip()
        email_filter = (request.args.get("email_filter") or "all").strip()
        if email_filter not in EMAIL_FILTER_VALUES:
            email_filter = "all"
        context["email_filter"] = email_filter

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
                form_data.update(read_pipeline_form(request.form, form_data))
                context["form_data"] = form_data
                context["error_message"] = (
                    "La ejecución del pipeline ahora es asíncrona. "
                    "Pulsa el botón con JavaScript activado para ver la barra de progreso."
                )

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
                context["leads"] = get_leads_for_run(sales_db, selected_run_id, email_filter)
                context["email_counts"] = count_leads_email_buckets(sales_db, selected_run_id)
                context["funnel"] = funnel_stats(sales_db, selected_run_id)

        return render_template("index.html", **context)

    @app.route("/pipeline/start", methods=["POST"])
    def start_pipeline():
        tracker: JobTracker = app.config["JOB_TRACKER"]
        payload = request.get_json(silent=True) or request.form

        try:
            form_snapshot = read_pipeline_form(payload, _default_pipeline_form())
            companies_path = Path(form_snapshot["companies_path"])
            output_dir = Path(form_snapshot["output_dir"])
            calibration_file = Path(form_snapshot["calibration_file"])
            topics = parse_topics(form_snapshot["topics"])
            auto_discover = bool(form_snapshot["auto_discover_companies"])
            max_discovered_companies = parse_positive_int(form_snapshot["max_discovered_companies"], default=100)
            discovery_region_filter = form_snapshot["discovery_region_filter"]

            if not auto_discover and companies_path.name == "clientes_produccion_template.csv":
                raise ValueError(
                    "Estás en modo CSV manual con la plantilla demo. "
                    "Activa descubrimiento automático o usa un CSV real."
                )
        except Exception as error:  # noqa: BLE001
            return jsonify({"error": str(error)}), 400

        job = tracker.create()

        sales_db = app.config["SALES_DB_PATH"]
        run_directories = app.config["RUN_DIRECTORIES"]

        def worker() -> None:
            def progress(current: int, total: int, stage: str) -> None:
                tracker.set_progress(job.job_id, current=current, total=total, stage=stage)

            try:
                pipeline = RadarCapitalPipeline()
                result = pipeline.run(
                    companies_csv_path=None if auto_discover else companies_path,
                    output_dir=output_dir,
                    topics=topics or None,
                    calibration_file=calibration_file,
                    auto_discover_companies=auto_discover,
                    max_discovered_companies=max_discovered_companies,
                    discovery_region_filter=discovery_region_filter,
                    progress_callback=progress,
                )
                run_id = result.run_directory.name
                run_directories[run_id] = result.run_directory

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
                tracker.mark_completed(job.job_id, run_id)
            except Exception as error:  # noqa: BLE001
                tracker.mark_failed(job.job_id, str(error))

        thread = threading.Thread(target=worker, name=f"pipeline-{job.job_id[:8]}", daemon=True)
        thread.start()

        return jsonify({"job_id": job.job_id, "state": tracker.get(job.job_id).as_dict()})

    @app.route("/pipeline/progress/<job_id>", methods=["GET"])
    def pipeline_progress(job_id: str):
        tracker: JobTracker = app.config["JOB_TRACKER"]
        job = tracker.get(job_id)
        if job is None:
            abort(404)
        return jsonify(job.as_dict())

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


def _default_pipeline_form() -> dict:
    return {
        "companies_path": "data/clientes_produccion_template.csv",
        "output_dir": "outputs",
        "calibration_file": "config/calibracion_despacho.json",
        "topics": "",
        "auto_discover_companies": "1",
        "max_discovered_companies": "100",
        "discovery_region_filter": "",
    }


def read_pipeline_form(source, defaults: dict) -> dict:
    def pick(key: str) -> str:
        raw = source.get(key, "") if hasattr(source, "get") else ""
        if raw is None:
            raw = ""
        return str(raw).strip() or defaults.get(key, "")

    return {
        "companies_path": pick("companies_path"),
        "output_dir": pick("output_dir"),
        "calibration_file": pick("calibration_file"),
        "topics": pick("topics"),
        "auto_discover_companies": "1" if source.get("auto_discover_companies") else "",
        "max_discovered_companies": pick("max_discovered_companies"),
        "discovery_region_filter": pick("discovery_region_filter"),
    }


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
