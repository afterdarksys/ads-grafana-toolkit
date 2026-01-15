"""Flask web application for ads-grafana-toolkit."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, render_template, send_from_directory

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library import list_templates, create_from_template, get_template
from ads_grafana_toolkit.simple.converter import convert_config
from ads_grafana_toolkit.nlp_interface import generate_from_text
from ads_grafana_toolkit.web.database import init_db, get_db


def create_app(db_path: str = None, static_folder: str = None) -> Flask:
    """Create Flask application."""
    if static_folder is None:
        static_folder = str(Path(__file__).parent / "static")

    template_folder = str(Path(__file__).parent / "templates")

    app = Flask(
        __name__,
        static_folder=static_folder,
        template_folder=template_folder,
    )

    # Initialize database
    db_path = db_path or os.environ.get("DATABASE_PATH", "dashboards.db")
    init_db(db_path)

    # Routes
    @app.route("/")
    def index():
        """Serve the main page."""
        return render_template("index.html")

    @app.route("/api/health")
    def health():
        """Health check endpoint."""
        return jsonify({"status": "ok", "version": "0.1.0"})

    @app.route("/api/stats")
    def stats():
        """Get database statistics."""
        db = get_db()
        return jsonify(db.get_stats())

    # Dashboard endpoints
    @app.route("/api/dashboards", methods=["GET"])
    def list_dashboards():
        """List all dashboards."""
        db = get_db()
        search = request.args.get("search")
        tags = request.args.getlist("tags")
        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        dashboards = db.list_dashboards(search=search, tags=tags, limit=limit, offset=offset)
        return jsonify({"dashboards": dashboards})

    @app.route("/api/dashboards", methods=["POST"])
    def create_dashboard():
        """Create a new dashboard."""
        db = get_db()
        data = request.get_json()

        # Create dashboard from different sources
        source = data.get("source", "sdk")

        if source == "template":
            template_name = data.get("template")
            datasource = data.get("datasource", "Prometheus")
            variables = data.get("variables", {})

            dashboard = create_from_template(template_name, datasource, **variables)
            if data.get("title"):
                dashboard.title = data["title"]

        elif source == "nlp":
            prompt = data.get("prompt")
            datasource = data.get("datasource", "Prometheus")

            dashboard = generate_from_text(
                prompt,
                datasource=datasource,
                use_openai=data.get("use_openai", True),
            )

        elif source == "config":
            config = data.get("config")
            dashboard = convert_config(config)

        else:  # SDK / direct
            dashboard = Dashboard(
                title=data.get("title", "Untitled"),
                description=data.get("description", ""),
                tags=data.get("tags", []),
            )

            ds_name = data.get("datasource", "Prometheus")
            dashboard.datasource = Datasource(name=ds_name, type="prometheus")

            for panel_data in data.get("panels", []):
                panel = dashboard.add_panel(
                    panel_data.get("title", "Panel"),
                    query=panel_data.get("query"),
                    panel_type=panel_data.get("type", "timeseries"),
                    unit=panel_data.get("unit", "short"),
                )
                for query in panel_data.get("queries", [])[1:]:
                    panel.add_query(query.get("expr", ""), legend=query.get("legend", ""))

        # Save to database
        db.save_dashboard(
            uid=dashboard.uid,
            title=dashboard.title,
            json_data=dashboard.to_dict(),
            description=dashboard.description,
            tags=dashboard.tags,
            template_name=data.get("template"),
        )

        return jsonify({
            "uid": dashboard.uid,
            "title": dashboard.title,
            "json": dashboard.to_dict(),
        })

    @app.route("/api/dashboards/<uid>", methods=["GET"])
    def get_dashboard(uid: str):
        """Get a dashboard by UID."""
        db = get_db()
        dashboard = db.get_dashboard(uid)

        if not dashboard:
            return jsonify({"error": "Dashboard not found"}), 404

        return jsonify(dashboard)

    @app.route("/api/dashboards/<uid>", methods=["PUT"])
    def update_dashboard(uid: str):
        """Update a dashboard."""
        db = get_db()
        data = request.get_json()

        existing = db.get_dashboard(uid)
        if not existing:
            return jsonify({"error": "Dashboard not found"}), 404

        db.save_dashboard(
            uid=uid,
            title=data.get("title", existing["title"]),
            json_data=data.get("json_data", existing["json_data"]),
            description=data.get("description", existing["description"]),
            tags=data.get("tags", existing["tags"]),
            template_name=existing.get("template_name"),
        )

        return jsonify({"status": "updated", "uid": uid})

    @app.route("/api/dashboards/<uid>", methods=["DELETE"])
    def delete_dashboard(uid: str):
        """Delete a dashboard."""
        db = get_db()
        if db.delete_dashboard(uid):
            return jsonify({"status": "deleted"})
        return jsonify({"error": "Dashboard not found"}), 404

    @app.route("/api/dashboards/<uid>/history", methods=["GET"])
    def get_dashboard_history(uid: str):
        """Get dashboard history."""
        db = get_db()
        limit = int(request.args.get("limit", 10))
        history = db.get_dashboard_history(uid, limit=limit)
        return jsonify({"history": history})

    @app.route("/api/dashboards/<uid>/export", methods=["GET"])
    def export_dashboard(uid: str):
        """Export dashboard JSON."""
        db = get_db()
        dashboard = db.get_dashboard(uid)

        if not dashboard:
            return jsonify({"error": "Dashboard not found"}), 404

        return jsonify(dashboard["json_data"])

    # Template endpoints
    @app.route("/api/templates", methods=["GET"])
    def get_templates():
        """List available templates."""
        category = request.args.get("category")
        templates = list_templates(category)
        return jsonify({"templates": templates})

    @app.route("/api/templates/<name>", methods=["GET"])
    def get_template_info(name: str):
        """Get template details."""
        try:
            template = get_template(name)
            return jsonify({
                "name": template.name,
                "description": template.description,
                "category": template.category,
                "tags": template.tags,
                "variables": [
                    {
                        "name": v.name,
                        "description": v.description,
                        "default": v.default,
                        "required": v.required,
                    }
                    for v in template.variables
                ],
            })
        except KeyError:
            return jsonify({"error": "Template not found"}), 404

    @app.route("/api/templates/<name>/preview", methods=["POST"])
    def preview_template(name: str):
        """Preview a template with given parameters."""
        try:
            data = request.get_json() or {}
            datasource = data.get("datasource", "Prometheus")
            variables = data.get("variables", {})

            dashboard = create_from_template(name, datasource, **variables)
            return jsonify({
                "title": dashboard.title,
                "panels": len(dashboard.panels),
                "json": dashboard.to_dict(),
            })
        except KeyError:
            return jsonify({"error": "Template not found"}), 404

    # NLP endpoint
    @app.route("/api/generate", methods=["POST"])
    def generate_dashboard():
        """Generate dashboard from natural language."""
        data = request.get_json()
        prompt = data.get("prompt")

        if not prompt:
            return jsonify({"error": "prompt is required"}), 400

        datasource = data.get("datasource", "Prometheus")
        use_openai = data.get("use_openai", True)

        dashboard = generate_from_text(prompt, datasource=datasource, use_openai=use_openai)

        return jsonify({
            "title": dashboard.title,
            "panels": len(dashboard.panels),
            "json": dashboard.to_dict(),
        })

    # Datasource endpoints
    @app.route("/api/datasources", methods=["GET"])
    def list_datasources():
        """List configured datasources."""
        db = get_db()
        return jsonify({"datasources": db.list_datasources()})

    @app.route("/api/datasources", methods=["POST"])
    def create_datasource():
        """Create a new datasource."""
        db = get_db()
        data = request.get_json()

        db.save_datasource(
            name=data["name"],
            ds_type=data.get("type", "prometheus"),
            uid=data.get("uid"),
            is_default=data.get("is_default", False),
        )

        return jsonify({"status": "created", "name": data["name"]})

    @app.route("/api/datasources/<name>", methods=["DELETE"])
    def delete_datasource(name: str):
        """Delete a datasource."""
        db = get_db()
        if db.delete_datasource(name):
            return jsonify({"status": "deleted"})
        return jsonify({"error": "Datasource not found"}), 404

    return app


def run_server(host: str = "0.0.0.0", port: int = 8080, debug: bool = False, db_path: str = None):
    """Run the web server."""
    app = create_app(db_path=db_path)
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server(debug=True)
