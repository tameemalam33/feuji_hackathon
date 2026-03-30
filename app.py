"""AutoQA Pro — Flask application entrypoint."""
from __future__ import annotations

import os
import sys

# Ensure package imports resolve when launched from project root
_ROOT = os.path.abspath(os.path.dirname(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from flask import Flask, redirect, render_template, url_for

from config import BASE_DIR
from models.database import Database
from routes.api import api_bp

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.register_blueprint(api_bp)

_db = Database()
_db.init_db()


@app.route("/")
def root():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/history")
def history():
    return render_template("history.html")


@app.route("/test-cases")
def test_cases_page():
    return render_template("test_cases.html")


@app.route("/visualization")
def visualization():
    return render_template("visualization.html")


@app.route("/pages")
def pages_view():
    return render_template("pages.html")


@app.route("/report/<int:run_id>")
def report_view(run_id: int):
    """Interactive HTML report (summary, charts, failures, lazy-loaded test table)."""
    return render_template("report.html", run_id=run_id)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("DEBUG") == "1")
