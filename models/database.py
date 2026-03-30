"""SQLite persistence for runs and test cases."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Generator, List, Optional

from config import DATABASE_PATH


def _migrate_runs(conn: sqlite3.Connection) -> None:
    for col, ddl in (
        ("batch_id", "ALTER TABLE runs ADD COLUMN batch_id TEXT"),
        ("health_score", "ALTER TABLE runs ADD COLUMN health_score REAL"),
        ("coverage", "ALTER TABLE runs ADD COLUMN coverage REAL"),
        ("performance_score", "ALTER TABLE runs ADD COLUMN performance_score REAL"),
        ("insights_json", "ALTER TABLE runs ADD COLUMN insights_json TEXT"),
        ("accessibility_score", "ALTER TABLE runs ADD COLUMN accessibility_score REAL"),
        ("security_score", "ALTER TABLE runs ADD COLUMN security_score REAL"),
        ("synthetic_dataset_json", "ALTER TABLE runs ADD COLUMN synthetic_dataset_json TEXT"),
    ):
        try:
            conn.execute(ddl)
        except sqlite3.OperationalError:
            pass


def _migrate_test_cases(conn: sqlite3.Connection) -> None:
    for ddl in (
        "ALTER TABLE test_cases ADD COLUMN severity TEXT",
        "ALTER TABLE test_cases ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE test_cases ADD COLUMN screenshot_path TEXT",
        "ALTER TABLE test_cases ADD COLUMN page TEXT",
        "ALTER TABLE test_cases ADD COLUMN root_cause TEXT",
        "ALTER TABLE test_cases ADD COLUMN user_story TEXT",
        "ALTER TABLE test_cases ADD COLUMN scenario TEXT",
        "ALTER TABLE test_cases ADD COLUMN test_type TEXT",
        "ALTER TABLE test_cases ADD COLUMN logs_json TEXT",
        "ALTER TABLE test_cases ADD COLUMN component TEXT",
        "ALTER TABLE test_cases ADD COLUMN page_class TEXT",
        "ALTER TABLE test_cases ADD COLUMN element_selector TEXT",
        "ALTER TABLE test_cases ADD COLUMN issue_type TEXT",
        "ALTER TABLE test_cases ADD COLUMN message TEXT",
    ):
        try:
            conn.execute(ddl)
        except sqlite3.OperationalError:
            pass


def _migrate_page_audits(conn: sqlite3.Connection) -> None:
    for ddl in (
        "ALTER TABLE page_audits ADD COLUMN load_status TEXT",
        "ALTER TABLE page_audits ADD COLUMN response_time_ms REAL",
        "ALTER TABLE page_audits ADD COLUMN error_type TEXT",
        "ALTER TABLE page_audits ADD COLUMN error_message TEXT",
        "ALTER TABLE page_audits ADD COLUMN js_errors_json TEXT",
        "ALTER TABLE page_audits ADD COLUMN performance_json TEXT",
        "ALTER TABLE page_audits ADD COLUMN performance_score REAL",
        "ALTER TABLE page_audits ADD COLUMN issues_json TEXT",
        "ALTER TABLE page_audits ADD COLUMN suggestions_json TEXT",
    ):
        try:
            conn.execute(ddl)
        except sqlite3.OperationalError:
            pass


class Database:
    def __init__(self, path: str = DATABASE_PATH) -> None:
        self.path = path

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    total INTEGER NOT NULL DEFAULT 0,
                    passed INTEGER NOT NULL DEFAULT 0,
                    failed INTEGER NOT NULL DEFAULT 0,
                    success_rate REAL NOT NULL DEFAULT 0,
                    summary_json TEXT,
                    charts_json TEXT,
                    batch_id TEXT,
                    health_score REAL,
                    coverage REAL,
                    performance_score REAL,
                    insights_json TEXT,
                    accessibility_score REAL,
                    security_score REAL,
                    synthetic_dataset_json TEXT
                );

                CREATE TABLE IF NOT EXISTS test_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    test_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    expected TEXT,
                    actual TEXT,
                    suggestion TEXT,
                    screenshot TEXT,
                    steps_json TEXT,
                    severity TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    screenshot_path TEXT,
                    page TEXT,
                    root_cause TEXT,
                    user_story TEXT,
                    scenario TEXT,
                    test_type TEXT,
                    logs_json TEXT,
                    component TEXT,
                    page_class TEXT,
                    element_selector TEXT,
                    issue_type TEXT,
                    message TEXT,
                    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_test_cases_run_id ON test_cases(run_id);

                CREATE TABLE IF NOT EXISTS page_audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    page_url TEXT NOT NULL,
                    load_status TEXT,
                    response_time_ms REAL,
                    error_type TEXT,
                    error_message TEXT,
                    js_errors_json TEXT,
                    performance_json TEXT,
                    performance_score REAL,
                    issues_json TEXT,
                    suggestions_json TEXT,
                    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_page_audits_run_id ON page_audits(run_id);

                CREATE TABLE IF NOT EXISTS visual_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    page_url TEXT NOT NULL,
                    baseline_path TEXT,
                    current_path TEXT,
                    diff_path TEXT,
                    mismatch_percent REAL NOT NULL DEFAULT 0,
                    status TEXT,
                    failed INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_visual_tests_run_id ON visual_tests(run_id);

                CREATE TABLE IF NOT EXISTS page_cache (
                    page_url TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    last_tested_run_id INTEGER,
                    last_tested_at TEXT NOT NULL,
                    last_result_json TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_page_cache_last_run ON page_cache(last_tested_run_id);
                """
            )
            _migrate_runs(conn)
            _migrate_test_cases(conn)
            _migrate_page_audits(conn)

    def insert_run(
        self,
        url: str,
        total: int,
        passed: int,
        failed: int,
        summary: dict,
        charts: dict,
        batch_id: str = "",
        health_score: Optional[float] = None,
        coverage: Optional[float] = None,
        performance_score: Optional[float] = None,
        insights: Optional[List[str]] = None,
        accessibility_score: Optional[float] = None,
        security_score: Optional[float] = None,
        synthetic_dataset_json: Optional[str] = None,
    ) -> int:
        ts = datetime.utcnow().isoformat() + "Z"
        rate = (passed / total * 100.0) if total else 0.0
        insights_json = json.dumps(insights or [])
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO runs (
                    url, timestamp, total, passed, failed, success_rate,
                    summary_json, charts_json, batch_id,
                    health_score, coverage, performance_score, insights_json,
                    accessibility_score, security_score, synthetic_dataset_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    url,
                    ts,
                    total,
                    passed,
                    failed,
                    rate,
                    json.dumps(summary),
                    json.dumps(charts),
                    batch_id,
                    health_score,
                    coverage,
                    performance_score,
                    insights_json,
                    accessibility_score,
                    security_score,
                    synthetic_dataset_json,
                ),
            )
            return int(cur.lastrowid)

    def update_run_completion(
        self,
        run_id: int,
        total: int,
        passed: int,
        failed: int,
        summary: dict,
        charts: dict,
        health_score: Optional[float],
        coverage: Optional[float],
        performance_score: Optional[float],
        insights: List[str],
        accessibility_score: Optional[float] = None,
        security_score: Optional[float] = None,
        synthetic_dataset_json: Optional[str] = None,
    ) -> None:
        rate = (passed / total * 100.0) if total else 0.0
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE runs SET
                    total = ?, passed = ?, failed = ?, success_rate = ?,
                    summary_json = ?, charts_json = ?,
                    health_score = ?, coverage = ?, performance_score = ?, insights_json = ?,
                    accessibility_score = ?, security_score = ?, synthetic_dataset_json = ?
                WHERE id = ?
                """,
                (
                    total,
                    passed,
                    failed,
                    rate,
                    json.dumps(summary),
                    json.dumps(charts),
                    health_score,
                    coverage,
                    performance_score,
                    json.dumps(insights),
                    accessibility_score,
                    security_score,
                    synthetic_dataset_json,
                    run_id,
                ),
            )

    def insert_test_case(
        self,
        run_id: int,
        test_id: str,
        name: str,
        category: str,
        priority: str,
        status: str,
        expected: str,
        actual: str,
        suggestion: str,
        screenshot: Optional[str],
        steps: List[str],
        severity: str,
        retry_count: int = 0,
        screenshot_path: Optional[str] = None,
        page: str = "",
        root_cause: str = "",
        user_story: str = "",
        scenario: str = "",
        test_type: str = "",
        logs: Optional[List[str]] = None,
        component: str = "",
        page_class: str = "",
        element_selector: str = "",
        issue_type: str = "",
        message: str = "",
    ) -> None:
        spath = screenshot_path or screenshot or ""
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO test_cases (
                    run_id, test_id, name, category, priority, status,
                    expected, actual, suggestion, screenshot, steps_json, severity,
                    retry_count, screenshot_path, page, root_cause,
                    user_story, scenario, test_type, logs_json, component, page_class,
                    element_selector, issue_type, message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    test_id,
                    name,
                    category,
                    priority,
                    status,
                    expected,
                    actual,
                    suggestion,
                    screenshot or "",
                    json.dumps(steps),
                    severity,
                    int(retry_count),
                    spath,
                    page or "",
                    root_cause or "",
                    user_story or "",
                    scenario or "",
                    test_type or "",
                    json.dumps(logs or []),
                    component or "",
                    page_class or "",
                    element_selector or "",
                    issue_type or "",
                    message or "",
                ),
            )

    def get_run(self, run_id: int) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if not row:
                return None
            return dict(row)

    def list_runs(self, limit: int = 100) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_run(self, run_id: int) -> None:
        """Delete a single run (cascades to test cases + audits)."""
        with self._conn() as conn:
            conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))

    def clear_runs(self) -> None:
        """Delete all runs (cascades to test cases + audits)."""
        with self._conn() as conn:
            conn.execute("DELETE FROM runs")

    def get_previous_run_id(self, run_id: int) -> Optional[int]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM runs WHERE id < ? ORDER BY id DESC LIMIT 1",
                (run_id,),
            ).fetchone()
            if not row:
                return None
            return int(row["id"])

    def get_test_cases_for_run(self, run_id: int) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM test_cases WHERE run_id = ? ORDER BY test_id",
                (run_id,),
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                if d.get("steps_json"):
                    d["steps"] = json.loads(d["steps_json"])
                else:
                    d["steps"] = []
                del d["steps_json"]
                if not d.get("screenshot") and d.get("screenshot_path"):
                    d["screenshot"] = d["screenshot_path"]
                d["title"] = d.get("name", "")
                d["expected_result"] = d.get("expected", "")
                d["actual_result"] = d.get("actual", "")
                lj = d.get("logs_json")
                if lj:
                    try:
                        d["logs"] = json.loads(lj)
                    except Exception:
                        d["logs"] = []
                else:
                    d["logs"] = []
                if "logs_json" in d:
                    del d["logs_json"]
                out.append(d)
            return out

    def timeline_data(self, limit: int = 20) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, timestamp, success_rate, total, passed, failed,
                       health_score, coverage, accessibility_score, security_score
                FROM runs ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows][::-1]

    def clear_page_audits(self, run_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM page_audits WHERE run_id = ?", (run_id,))

    def insert_page_audit(
        self,
        *,
        run_id: int,
        page_url: str,
        load_status: str,
        response_time_ms: float,
        error_type: str = "",
        error_message: str = "",
        js_errors: Optional[List[str]] = None,
        performance: Optional[dict] = None,
        performance_score: Optional[float] = None,
        issues: Optional[List[dict]] = None,
        suggestions: Optional[List[str]] = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO page_audits (
                    run_id, page_url, load_status, response_time_ms, error_type, error_message,
                    js_errors_json, performance_json, performance_score, issues_json, suggestions_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    page_url,
                    load_status,
                    float(response_time_ms or 0),
                    error_type or "",
                    error_message or "",
                    json.dumps(js_errors or []),
                    json.dumps(performance or {}),
                    performance_score if performance_score is not None else None,
                    json.dumps(issues or []),
                    json.dumps(suggestions or []),
                ),
            )

    def get_pages_for_run(self, run_id: int) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM page_audits WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        out: List[dict] = []
        for r in rows:
            d = dict(r)
            d["js_errors"] = json.loads(d.get("js_errors_json") or "[]")
            d["performance"] = json.loads(d.get("performance_json") or "{}")
            d["issues"] = json.loads(d.get("issues_json") or "[]")
            d["suggestions"] = json.loads(d.get("suggestions_json") or "[]")
            out.append(d)
        return out

    def clear_visual_tests(self, run_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM visual_tests WHERE run_id = ?", (run_id,))

    def insert_visual_test(
        self,
        *,
        run_id: int,
        page_url: str,
        baseline_path: str,
        current_path: str,
        diff_path: str,
        mismatch_percent: float,
        status: str,
        failed: bool,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO visual_tests (
                    run_id, page_url, baseline_path, current_path, diff_path, mismatch_percent, status, failed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    page_url,
                    baseline_path or "",
                    current_path or "",
                    diff_path or "",
                    float(mismatch_percent or 0),
                    status or "",
                    1 if failed else 0,
                ),
            )

    def get_visual_tests_for_run(self, run_id: int) -> List[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM visual_tests WHERE run_id = ? ORDER BY mismatch_percent DESC, id",
                (run_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_page_cache(self, page_url: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM page_cache WHERE page_url = ?",
                (page_url,),
            ).fetchone()
            return dict(row) if row else None

    def get_page_cache_bulk(self, page_urls: List[str]) -> dict:
        keys = [str(u or "").strip() for u in page_urls if str(u or "").strip()]
        if not keys:
            return {}
        placeholders = ",".join(["?"] * len(keys))
        q = f"SELECT * FROM page_cache WHERE page_url IN ({placeholders})"
        with self._conn() as conn:
            rows = conn.execute(q, tuple(keys)).fetchall()
        out = {}
        for r in rows:
            d = dict(r)
            out[str(d.get("page_url"))] = d
        return out

    def upsert_page_cache(
        self,
        *,
        page_url: str,
        content_hash: str,
        run_id: int,
        last_result: Optional[dict] = None,
    ) -> None:
        ts = datetime.utcnow().isoformat() + "Z"
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO page_cache (page_url, content_hash, last_tested_run_id, last_tested_at, last_result_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(page_url) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    last_tested_run_id = excluded.last_tested_run_id,
                    last_tested_at = excluded.last_tested_at,
                    last_result_json = excluded.last_result_json
                """,
                (
                    page_url,
                    content_hash or "",
                    int(run_id),
                    ts,
                    json.dumps(last_result or {}),
                ),
            )
