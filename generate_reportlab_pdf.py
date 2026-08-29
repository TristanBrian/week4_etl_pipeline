from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent
PDF_FILENAME = "Week4_Technical_Brief_BrianKioko.pdf"
DOCS_PDF_PATH = BASE_DIR / "docs" / PDF_FILENAME
ROOT_PDF_PATH = BASE_DIR / PDF_FILENAME

def build_pdf_reportlab(target_path: Path):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    target_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(target_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )

    meta_style = ParagraphStyle(
        'MetaText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#334155')
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=6,
        spaceAfter=4
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#1e293b')
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#0f172a')
    )

    footer_style = ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#64748b'),
        alignment=1
    )

    story = []

    # Title
    story.append(Paragraph("Technical Brief: Executive Memo for Operations Leadership", title_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0f172a'), spaceBefore=2, spaceAfter=4))

    # Meta Header Table
    meta_data = [
        [
            Paragraph("<b>TO:</b> Operations Manager &amp; Executive Leadership", meta_style),
            Paragraph("<b>FROM:</b> Lead Data Operations Engineer (Brian Kioko)", meta_style)
        ],
        [
            Paragraph("<b>DATE:</b> August 29, 2026", meta_style),
            Paragraph("<b>SUBJECT:</b> Transitioning from Manual Spreadsheet Updates to Automated Pipeline", meta_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6))

    # Executive Summary
    summary_text = (
        "<b>Executive Summary:</b> Industrial decision-makers rely on daily sensor telemetry (pressure, temperature, operational status) "
        "to manage infrastructure risk and schedule field interventions. Historically, daily data ingestion relied on manual Excel updates—a "
        "process prone to human error, missed schedules, silent data corruption, and duplicate loading. This technical brief outlines the operational "
        "shift to an automated, industrialized Python ETL pipeline using an <b>irrigation system analogy</b> to explain why this automated architecture "
        "is safer, more reliable, and more valuable than manual spreadsheet management."
    )
    story.append(Paragraph(summary_text, body_style))

    # Section 1: Irrigation Analogy
    story.append(Paragraph("The Irrigation Analogy: Manual Buckets vs. Smart Automated Irrigation", h2_style))

    table_content = [
        [
            Paragraph("Dimension", table_header_style),
            Paragraph("Manual Excel Entry (\"Carrying Water in Buckets\")", table_header_style),
            Paragraph("Automated Data Pipeline (\"Smart Automated Irrigation\")", table_header_style)
        ],
        [
            Paragraph("Delivery Mechanism", table_cell_bold),
            Paragraph("Depends on individuals carrying buckets daily. If someone forgets or is delayed, crops suffer without water.", table_cell_style),
            Paragraph("Scheduled via cron / Task Scheduler at 6:00 AM daily. Clean data is consistently ready before business hours.", table_cell_style)
        ],
        [
            Paragraph("Data Quality &amp; Filtration", table_cell_bold),
            Paragraph("Unfiltered water poured directly on crops. Polluted or out-of-range values pass silently into reporting.", table_cell_style),
            Paragraph("Built-in filtration (<b>Great Expectations Quality Gate</b>). Out-of-bounds readings immediately trip shutoff valve (<code>sys.exit</code>).", table_cell_style)
        ],
        [
            Paragraph("Over-Watering / Idempotency", table_cell_bold),
            Paragraph("Accidental double-pasting or re-running floods crops with duplicate rows appended to database tables.", table_cell_style),
            Paragraph("Smart metering (<b>Idempotent Snapshot Loading</b>). Re-runs replace only that day's target snapshot cleanly.", table_cell_style)
        ],
        [
            Paragraph("Auditability &amp; Visibility", table_cell_bold),
            Paragraph("No log of who poured what water when. Tracing reporting discrepancies is tedious and error-prone.", table_cell_style),
            Paragraph("Full event logging (<code>pipeline.log</code>) and auto-generated Data Docs. Extracted, filtered, and loaded rows are tracked.", table_cell_style)
        ]
    ]

    analogy_table = Table(table_content, colWidths=[110, 215, 215])
    analogy_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,1), (-1,1), colors.white),
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (0,3), (-1,3), colors.white),
        ('BACKGROUND', (0,4), (-1,4), colors.HexColor('#f8fafc')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(analogy_table)
    story.append(Spacer(1, 6))

    # Section 2: Technical Safeguards
    story.append(Paragraph("Technical Safeguards &amp; Business Risk Mitigation", h2_style))
    
    bullet_1 = (
        "&bull; <b>Quality Gate Halt on Corrupted Data:</b> Validation rules enforce schema integrity (non-null IDs, valid status enums) "
        "and physical domain bounds (0 &le; pressure &le; 200 PSI, -20 &le; temp &le; 120&deg;C). If validation fails, the pipeline halts immediately, "
        "preventing corrupted readings from polluting executive dashboards."
    )
    story.append(Paragraph(bullet_1, body_style))

    bullet_2 = (
        "&bull; <b>Absolute Path Resolution for Cron Compatibility:</b> Dynamic base resolution (<code>BASE_DIR = Path(__file__).resolve().parent</code>) "
        "eliminates relative path failures when invoked headlessly via system schedulers, guaranteeing production stability."
    )
    story.append(Paragraph(bullet_2, body_style))

    bullet_3 = (
        "&bull; <b>Idempotent Load Step:</b> Database insertion drops existing daily records for the target <code>snapshot_date</code> "
        "before inserting refreshed data in an atomic transaction, preventing duplicate metrics on pipeline retries."
    )
    story.append(Paragraph(bullet_3, body_style))

    # Section 3: Business Impact & Next Steps
    story.append(Paragraph("Business Impact &amp; Next Steps", h2_style))
    
    roi_text = (
        "<b>Business Value Realization:</b> Eliminates hours spent daily on manual copy-pasting, restores complete trust in operations "
        "reporting, and provides fail-safe execution with automated error logging."
    )
    roi_box = Table([[Paragraph(roi_text, body_style)]], colWidths=[540])
    roi_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0f9ff')),
        ('LINEBEFORE', (0,0), (0,0), 3, colors.HexColor('#0284c7')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(roi_box)
    story.append(Spacer(1, 4))

    next_steps_text = (
        "<b>Strategic Next Steps:</b> (1) Authorize deployment of the 6:00 AM daily production cron schedule. "
        "(2) Connect quality gate halt events to real-time Slack/Email alerts for on-call data engineers."
    )
    story.append(Paragraph(next_steps_text, body_style))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cbd5e1'), spaceBefore=6, spaceAfter=4))
    story.append(Paragraph("Industrial Data Operations Pipeline (IDOP) &bull; Week 4 Technical Brief &bull; Prepared by Brian Kioko", footer_style))

    doc.build(story)

if __name__ == "__main__":
    build_pdf_reportlab(DOCS_PDF_PATH)
    build_pdf_reportlab(ROOT_PDF_PATH)
    print("ReportLab PDF compiled successfully!")
