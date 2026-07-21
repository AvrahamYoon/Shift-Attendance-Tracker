"""PDF reports via ReportLab."""

from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from workers.attendance import (
    attendance_summary_for_term,
    occurrence_label,
    summary_overall_status,
)
from workers.models import AttendanceRecord
from workers.roster import enrollment_for, term_has_roster


def safe_filename(part):
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in str(part)).strip("-") or "report"


def pdf_http_response(filename, pdf_bytes):
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Heading1"],
            fontSize=16,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ReportMeta",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.grey,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=8,
        )
    )
    return styles


def _status_label(summary):
    status = summary_overall_status(summary)
    if status == "over":
        return "OVER LIMIT"
    if status == "at_limit":
        return "At limit"
    return "OK"


def _count_cell(info):
    return f"{info['count']}/{info['limit']}"


def _table_style(header_color):
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), header_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def _doc_setup():
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    return buffer, doc


def _report_header(story, styles, title, term, generated_by):
    story.append(Paragraph(title, styles["ReportTitle"]))
    story.append(
        Paragraph(
            f"<b>{term.name}</b> ({term.start_date:%b %d, %Y} &ndash; {term.end_date:%b %d, %Y})",
            styles["Normal"],
        )
    )
    generated = timezone.localtime()
    by = generated_by.get_full_name() or generated_by.username
    story.append(
        Paragraph(
            f"Generated {generated:%Y-%m-%d %I:%M %p} by {by}",
            styles["ReportMeta"],
        )
    )
    story.append(Spacer(1, 0.15 * inch))


def _worker_building_name(worker, term):
    if term and term_has_roster(term):
        enrollment = enrollment_for(worker, term)
        if enrollment:
            return enrollment.building.name
    return worker.building.name


def build_term_attendance_pdf(workers, term, generated_by, budgets=None):
    buffer, doc = _doc_setup()
    styles = _styles()
    story = []

    _report_header(story, styles, "Term Attendance Report", term, generated_by)

    header = ["Building", "Worker", "I-Number", "Absences", "Tardy", "No show", "Status"]
    data = [header]
    worker_list = list(workers.select_related("building"))
    worker_list.sort(
        key=lambda worker: (_worker_building_name(worker, term), worker.name)
    )
    for worker in worker_list:
        summary = attendance_summary_for_term(worker, term)
        data.append(
            [
                _worker_building_name(worker, term),
                worker.name,
                worker.i_number,
                _count_cell(summary["absence"]),
                _count_cell(summary["tardy"]),
                _count_cell(summary["no_show"]),
                _status_label(summary),
            ]
        )

    if len(data) == 1:
        data.append(["—", "No workers in scope", "", "", "", "", ""])

    table = Table(
        data,
        repeatRows=1,
        colWidths=[1.1 * inch, 1.45 * inch, 0.9 * inch, 0.75 * inch, 0.65 * inch, 0.75 * inch, 0.85 * inch],
    )
    table.setStyle(_table_style(colors.HexColor("#1e40af")))
    story.append(table)

    if budgets is not None:
        budget_rows = list(budgets.select_related("building").order_by("building__name"))
        if budget_rows:
            story.append(Paragraph("Budget overview", styles["SectionHeading"]))
            budget_data = [["Building", "Allocated", "Actual", "Variance"]]
            for budget in budget_rows:
                variance = budget.headcount_variance
                prefix = "+" if variance > 0 else ""
                budget_data.append(
                    [
                        budget.building.name,
                        str(budget.allocated_headcount),
                        str(budget.actual_headcount),
                        f"{prefix}{variance}",
                    ]
                )
            budget_table = Table(
                budget_data,
                repeatRows=1,
                colWidths=[2.5 * inch, 1 * inch, 1 * inch, 1 * inch],
            )
            budget_table.setStyle(_table_style(colors.HexColor("#334155")))
            story.append(budget_table)

    doc.build(story)
    return buffer.getvalue()


def build_worker_pdf(worker, term, generated_by):
    buffer, doc = _doc_setup()
    styles = _styles()
    story = []

    _report_header(story, styles, "Worker Attendance Report", term, generated_by)

    supervisor = worker.current_supervisor
    supervisor_name = (
        supervisor.get_full_name() or supervisor.username if supervisor else "—"
    )
    building_name = _worker_building_name(worker, term)
    enrollment = enrollment_for(worker, term) if term else None
    term_status = (
        enrollment.get_term_status_display()
        if enrollment
        else worker.get_term_status_display()
    )
    status_label = (
        enrollment.get_status_display() if enrollment else worker.get_status_display()
    )
    shift = enrollment.shift if enrollment else worker.shift
    info_lines = [
        f"<b>Name:</b> {worker.name}",
        f"<b>I-Number:</b> {worker.i_number}",
        f"<b>Building:</b> {building_name}",
        f"<b>Shift:</b> {shift or '—'}",
        f"<b>Status:</b> {status_label}",
        f"<b>Term status:</b> {term_status}",
        f"<b>Supervisor:</b> {supervisor_name}",
    ]
    for line in info_lines:
        story.append(Paragraph(line, styles["Normal"]))
    story.append(Spacer(1, 0.15 * inch))

    summary = attendance_summary_for_term(worker, term)
    story.append(Paragraph("Term totals", styles["SectionHeading"]))
    summary_data = [
        ["Category", "Count", "Limit", "Status"],
        [
            summary["absence"]["label"],
            str(summary["absence"]["count"]),
            str(summary["absence"]["limit"]),
            _status_label(summary) if summary["absence"]["exceeded"] else (
                "At limit" if summary["absence"]["at_limit"] else "OK"
            ),
        ],
        [
            summary["tardy"]["label"],
            str(summary["tardy"]["count"]),
            str(summary["tardy"]["limit"]),
            "OVER LIMIT" if summary["tardy"]["exceeded"] else (
                "At limit" if summary["tardy"]["at_limit"] else "OK"
            ),
        ],
        [
            summary["no_show"]["label"],
            str(summary["no_show"]["count"]),
            str(summary["no_show"]["limit"]),
            "OVER LIMIT" if summary["no_show"]["exceeded"] else (
                "At limit" if summary["no_show"]["at_limit"] else "OK"
            ),
        ],
    ]
    summary_table = Table(summary_data, repeatRows=1, colWidths=[1.5 * inch, 0.8 * inch, 0.8 * inch, 1.2 * inch])
    summary_table.setStyle(_table_style(colors.HexColor("#1e40af")))
    story.append(summary_table)

    records = (
        AttendanceRecord.objects.filter(worker=worker, term=term)
        .select_related("recorded_by")
        .order_by("record_date", "record_time", "created_at")
    )
    story.append(Paragraph("Attendance records", styles["SectionHeading"]))
    record_data = [["Date", "Category", "Detail", "Recorded by"]]
    if records:
        for record in records:
            recorded_by = record.recorded_by.get_full_name() or record.recorded_by.username
            time_part = f" {record.record_time:%I:%M %p}" if record.record_time else ""
            record_data.append(
                [
                    f"{record.record_date}{time_part}",
                    record.get_category_display(),
                    occurrence_label(record),
                    recorded_by,
                ]
            )
    else:
        record_data.append(["—", "No records this term", "", ""])

    record_table = Table(
        record_data,
        repeatRows=1,
        colWidths=[1.1 * inch, 0.9 * inch, 2.2 * inch, 1.3 * inch],
    )
    record_table.setStyle(_table_style(colors.HexColor("#334155")))
    story.append(record_table)

    doc.build(story)
    return buffer.getvalue()
