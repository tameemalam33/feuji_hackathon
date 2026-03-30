"""Professional PDF reports (ReportLab + matplotlib charts)."""
from __future__ import annotations

import io
import os
from typing import Any, Dict, List
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from services.report_payload import build_report_payload

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    plt = None  # type: ignore


def _pie_chart_png(labels: List[str], values: List[float], title: str) -> io.BytesIO:
    buf = io.BytesIO()
    if plt is None or not sum(values):
        buf.seek(0)
        return buf
    fig, ax = plt.subplots(figsize=(4.2, 4.2))
    colors_pie = ["#22c55e", "#ef4444", "#94a3b8"]
    ax.pie(values, labels=labels, autopct="%1.0f%%", startangle=90, colors=colors_pie[: len(values)])
    ax.set_title(title, fontsize=11)
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return buf


def _bar_chart_png(labels: List[str], values: List[float], title: str, ylabel: str) -> io.BytesIO:
    buf = io.BytesIO()
    if plt is None:
        buf.seek(0)
        return buf
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    c = ["#dc2626", "#ea580c", "#ca8a04", "#64748b"]
    ax.bar(labels, values, color=[c[i % len(c)] for i in range(len(labels))])
    ax.set_title(title, fontsize=11)
    ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return buf


def _bar_chart_png_single_color(labels: List[str], values: List[float], title: str) -> io.BytesIO:
    buf = io.BytesIO()
    if plt is None:
        buf.seek(0)
        return buf
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.bar(labels, values, color="#6366f1")
    ax.set_title(title, fontsize=11)
    ax.set_ylabel("Count")
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return buf


def _p(text: str, style) -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def build_pdf(
    run: Dict[str, Any],
    test_cases: List[Dict[str, Any]],
    charts: Dict[str, Any],
    out_path: str,
    pages_audit: List[Dict[str, Any]] | None = None,
) -> str:
    """Write PDF to out_path; return absolute path."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    payload = build_report_payload(run, test_cases, charts, pages_audit or [])

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        spaceAfter=14,
        fontSize=18,
        textColor=colors.HexColor("#0f172a"),
    )
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], spaceAfter=8, fontSize=13, textColor=colors.HexColor("#1e293b"))
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=12)
    small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#475569"))

    story: List[Any] = []

    story.append(Paragraph("<b>AutoQA Pro — Test Report</b>", title_style))
    story.append(Paragraph(f"<i>Run #{escape(str(payload['meta'].get('runId', '')))}</i>", styles["Normal"]))
    story.append(Spacer(1, 0.12 * inch))

    meta = payload["meta"]
    story.append(_p(f"Target URL: {meta.get('url') or '—'}", body))
    story.append(_p(f"Timestamp: {meta.get('timestamp') or '—'}", body))
    story.append(Spacer(1, 0.14 * inch))

    # --- Summary ---
    story.append(Paragraph("<b>1. Executive summary</b>", h2))
    s = payload["summary"]
    summary_data = [
        ["Total tests", "Passed", "Failed", "Coverage %", "Critical issues", "Health score %"],
        [
            str(s["total"]),
            f"{s['passed']} ✅",
            f"{s['failed']} ❌",
            f"{s['coverage']:.1f}",
            str(s["critical"]),
            f"{s['healthScore']:.1f}",
        ],
    ]
    tbl = Table(summary_data, colWidths=[1.0 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.1 * inch, 1.1 * inch])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 0.08 * inch))
    rd = payload["recommendationDetail"]
    story.append(Paragraph(f"<b>Verdict:</b> {escape(rd['label'])}", body))
    story.append(_p(rd["verdict"], small))
    story.append(Spacer(1, 0.18 * inch))

    # --- Charts ---
    story.append(Paragraph("<b>2. Visual overview</b>", h2))
    pf = charts.get("pass_fail") or {}
    plabels = pf.get("labels", ["Passed", "Failed"])
    pdata = pf.get("data", [s["passed"], s["failed"]])
    if plt and sum(float(x) for x in pdata) > 0:
        buf = _pie_chart_png(plabels[:3], [float(x) for x in pdata[:3]], "Pass vs Fail")
        if buf.getbuffer().nbytes > 0:
            story.append(Image(buf, width=3.8 * inch, height=3.4 * inch))
            story.append(Spacer(1, 0.1 * inch))

    ip = payload["issuePrioritization"]["countsBySeverity"]
    if plt and sum(ip.values()):
        buf2 = _bar_chart_png(list(ip.keys()), [float(ip[k]) for k in ip.keys()], "Failures by severity", "Count")
        if buf2.getbuffer().nbytes > 0:
            story.append(Image(buf2, width=6.2 * inch, height=3.4 * inch))
            story.append(Spacer(1, 0.1 * inch))

    tbc = charts.get("tests_by_category") or {}
    tl, td = tbc.get("labels", []), tbc.get("data", [])
    if plt and tl and td:
        buf3 = _bar_chart_png_single_color([str(x) for x in tl], [float(x) for x in td], "Tests per category")
        if buf3.getbuffer().nbytes > 0:
            story.append(Image(buf3, width=6.2 * inch, height=3.4 * inch))

    story.append(PageBreak())

    # --- Prioritization ---
    story.append(Paragraph("<b>3. Issue prioritization</b>", h2))
    pri_rows = [["Severity", "Failed count"]] + [[k, str(ip[k])] for k in ["Critical", "High", "Medium", "Low"]]
    pt = Table(pri_rows, colWidths=[2.5 * inch, 2 * inch])
    pt.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef2f2")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ]
        )
    )
    story.append(pt)
    story.append(Spacer(1, 0.25 * inch))

    # --- Failed details (critical first) ---
    story.append(Paragraph("<b>4. Failed test details (actionable)</b>", h2))
    fails = payload["failures"]
    if not fails:
        story.append(_p("No failed tests in this run.", body))
    else:
        for i, f in enumerate(fails[:35], 1):
            sev = f.get("severity") or ""
            badge = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}.get(sev, "•")
            story.append(Paragraph(f"<b>{badge} {escape(str(i))}. {escape(f.get('name') or '')}</b> <i>[{escape(sev)}]</i>", body))
            story.append(_p(f"Test ID: {f.get('testId')}", small))
            if f.get("page"):
                story.append(_p(f"Page: {f['page']}", small))
            steps = f.get("steps") or []
            if steps:
                story.append(Paragraph("<b>Steps performed</b>", small))
                for st in steps[:12]:
                    story.append(_p(f"  • {st}", small))
            story.append(_p(f"Expected: {f.get('expected') or '—'}", body))
            story.append(_p(f"Actual: {f.get('actual') or '—'}", body))
            story.append(_p(f"Root cause: {f.get('rootCause') or '—'}", body))
            story.append(_p(f"Suggested fix: {f.get('suggestedFix') or '—'}", body))
            logs = f.get("logs") or []
            if logs:
                story.append(Paragraph("<b>Console / logs (sample)</b>", small))
                for line in logs[:8]:
                    story.append(_p(line[:200], small))
            if f.get("screenshotUrl"):
                story.append(_p(f"Screenshot: {f['screenshotUrl']}", small))
            story.append(Spacer(1, 0.12 * inch))

        if len(fails) > 35:
            story.append(_p(f"… {len(fails) - 35} additional failure(s) omitted in PDF — see HTML report or JSON export.", small))

    story.append(PageBreak())

    # --- Performance ---
    story.append(Paragraph("<b>5. Performance insights</b>", h2))
    perf = payload["performance"]
    story.append(
        _p(
            f"Avg crawl load (ms): {perf.get('loadTime', 0):.1f} | "
            f"Slowest page (crawl, ms): {perf.get('slowestPageMs', 0):.1f} | "
            f"Run performance score: {perf.get('performanceScore', 0):.1f}",
            body,
        )
    )
    if perf.get("largestContentfulPaintMs"):
        story.append(_p(f"Largest Contentful Paint (max sampled, ms): {perf['largestContentfulPaintMs']}", body))
    if perf.get("avgTtfbMs") is not None:
        story.append(_p(f"Avg TTFB from timing probes (ms): {perf['avgTtfbMs']}", body))
    sp = perf.get("slowPages") or []
    if sp:
        story.append(Paragraph("<b>Slowest pages (by response time)</b>", small))
        for row in sp[:8]:
            story.append(
                _p(
                    f"  • {row.get('url', '')[:90]} — {row.get('responseTimeMs', 0):.0f} ms"
                    + (f" | LCP ~{row.get('lcpMs', 0):.0f} ms" if row.get("lcpMs") else ""),
                    small,
                )
            )
    story.append(Spacer(1, 0.2 * inch))

    # --- All tests compact table ---
    story.append(Paragraph("<b>6. Full test case listing (compact)</b>", h2))
    compact: List[List[str]] = [["ID", "Name", "Status", "Severity", "Category"]]
    for t in payload["tests"][:80]:
        compact.append(
            [
                str(t.get("id") or "")[:14],
                (t.get("name") or "")[:42],
                t.get("status") or "",
                str(t.get("severity") or "")[:10],
                str(t.get("category") or "")[:14],
            ]
        )
    ct = Table(compact, colWidths=[0.9 * inch, 2.4 * inch, 0.7 * inch, 0.85 * inch, 1.0 * inch])
    ct.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.2, colors.grey),
            ]
        )
    )
    story.append(ct)
    if len(payload["tests"]) > 80:
        story.append(_p(f"… {len(payload['tests']) - 80} more rows in JSON/HTML export.", small))

    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("<b>7. Final recommendation</b>", h2))
    story.append(Paragraph(f"<b>{escape(rd['label'])}</b>", body))
    story.append(_p(rd["verdict"], body))
    if rd.get("blockingIssues"):
        story.append(Paragraph("<b>Blocking issues</b>", small))
        for b in rd["blockingIssues"]:
            story.append(_p(f"• {b}", small))
    if rd.get("keyImprovements"):
        story.append(Paragraph("<b>Key improvements</b>", small))
        for k in rd["keyImprovements"]:
            story.append(_p(f"• {k}", small))

    doc = SimpleDocTemplate(
        out_path,
        pagesize=letter,
        rightMargin=48,
        leftMargin=48,
        topMargin=48,
        bottomMargin=48,
        title="AutoQA Report",
    )
    doc.build(story)
    return os.path.abspath(out_path)
