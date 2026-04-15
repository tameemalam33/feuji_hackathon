"""AutoQA Pro — Flask application entrypoint."""
from __future__ import annotations

import os
import sys

# Ensure package imports resolve when launched from project root
_ROOT = os.path.abspath(os.path.dirname(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from flask import Flask, redirect, render_template, url_for, session

from config import BASE_DIR
from models.database import Database
from routes.api import api_bp
from routes.auth import auth_bp
from routes.users import users_bp
from routes.projects import projects_bp
from routes.bugs import bugs_bp
from routes.saas_qa import saas_qa_bp

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)

# Configure session
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'True') == 'True'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

app.register_blueprint(api_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(projects_bp)
app.register_blueprint(bugs_bp)
app.register_blueprint(saas_qa_bp)

_db = Database()
_db.init_db()


@app.route("/")
def root():
    # Check if user is logged in
    user_id = session.get('user_id')
    if user_id:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/projects")
def projects():
    return render_template("projects.html")


@app.route("/project/<project_id>")
def project_detail(project_id):
    return render_template("project_detail.html", project_id=project_id)


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
