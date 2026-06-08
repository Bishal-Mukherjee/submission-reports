from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
from functools import partial
import os

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
C_NAVY    = colors.HexColor('#1a3a5c')
C_TEAL    = colors.HexColor('#2e7d9e')
C_SKY     = colors.HexColor('#a8c5da')
C_LIGHT   = colors.HexColor('#dbeaf5')
C_TEXT    = colors.HexColor('#1a202c')
C_MUTED   = colors.HexColor('#718096')
C_ROW_ALT = colors.HexColor('#f7fafc')
C_BORDER  = colors.HexColor('#e2e8f0')
C_WHITE   = colors.white


# ---------------------------------------------------------------------------
# Canvas callbacks
# ---------------------------------------------------------------------------

def _draw_first_page(canvas, doc):
    """Cover page: footer only — main content is rendered via flowables."""
    w, h = A4
    canvas.saveState()
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(0.75 * inch, 0.58 * inch, w - 0.75 * inch, 0.58 * inch)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(C_MUTED)
    canvas.drawCentredString(w / 2, 0.38 * inch,
                             f'Generated on {datetime.now().strftime("%d %B %Y")}')
    canvas.restoreState()


def _draw_later_pages(canvas, doc, report_title):
    """Content pages: slim navy header bar + footer rule."""
    w, h = A4
    canvas.saveState()

    # Header bar
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, h - 0.42 * inch, w, 0.42 * inch, fill=1, stroke=0)

    # Header text
    canvas.setFont('Helvetica', 8.5)
    canvas.setFillColor(C_WHITE)
    canvas.drawString(0.75 * inch, h - 0.28 * inch, report_title)
    canvas.drawRightString(w - 0.75 * inch, h - 0.28 * inch, f'Page {doc.page}')

    # Footer rule + text
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(0.75 * inch, 0.58 * inch, w - 0.75 * inch, 0.58 * inch)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(C_MUTED)
    canvas.drawCentredString(w / 2, 0.38 * inch,
                             f'Generated on {datetime.now().strftime("%d %B %Y")}')
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Summary table helpers
# ---------------------------------------------------------------------------

def _format_summary_cell(value):
    if isinstance(value, float):
        return f'{value:.1f}'
    if isinstance(value, int):
        return f'{value:,}'
    return str(value)


def _build_summary_table(doc_w, section):
    """Build a styled summary table from a section definition."""
    columns = section.get('columns', ['Category', 'Count'])
    rows = section.get('data', [])

    table_data = [columns]
    for row in rows:
        formatted_row = []
        for index, cell in enumerate(row):
            if index == 0:
                formatted_row.append(str(cell).replace('_', ' '))
            else:
                formatted_row.append(_format_summary_cell(cell))
        table_data.append(formatted_row)

    if len(columns) == 3:
        col_widths = [doc_w * 0.58, doc_w * 0.21, doc_w * 0.21]
    else:
        col_widths = [doc_w * 0.72, doc_w * 0.28]

    data_table = Table(table_data, colWidths=col_widths)
    data_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1,  0), C_NAVY),
        ('TEXTCOLOR',     (0, 0), (-1,  0), C_WHITE),
        ('FONTNAME',      (0, 0), (-1,  0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1,  0), 10),
        ('TOPPADDING',    (0, 0), (-1,  0), 9),
        ('BOTTOMPADDING', (0, 0), (-1,  0), 9),
        ('LEFTPADDING',   (0, 0), (-1,  0), 12),
        ('RIGHTPADDING',  (0, 0), (-1,  0), 12),
        ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',      (0, 1), (-1, -1), 9.5),
        ('TOPPADDING',    (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('LEFTPADDING',   (0, 1), (-1, -1), 12),
        ('RIGHTPADDING',  (0, 1), (-1, -1), 12),
        ('TEXTCOLOR',     (0, 1), (-1, -1), C_TEXT),
        ('ALIGN',         (1, 0), (-1, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [C_WHITE, C_ROW_ALT]),
        ('BOX',           (0, 0), (-1, -1), 0.5, C_BORDER),
        ('LINEBELOW',     (0, 1), (-1, -1), 0.5, C_BORDER),
    ]))
    return data_table


def _append_summary_section(story, doc_w, section_heading_style, section):
    """Append a section heading and one or more summary tables to the story."""
    heading_table = Table(
        [[Paragraph(section['title'], section_heading_style)]],
        colWidths=[doc_w],
    )
    heading_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (0, 0), C_LIGHT),
        ('LINEBEFORE',    (0, 0), (0, 0), 3.5, C_TEAL),
        ('TOPPADDING',    (0, 0), (0, 0), 8),
        ('BOTTOMPADDING', (0, 0), (0, 0), 8),
        ('LEFTPADDING',   (0, 0), (0, 0), 10),
        ('RIGHTPADDING',  (0, 0), (0, 0), 10),
    ]))
    story.append(heading_table)
    story.append(Spacer(1, 0.08 * inch))
    story.append(_build_summary_table(doc_w, section))

    for extra_table in section.get('extra_tables', []):
        story.append(Spacer(1, 0.18 * inch))
        extra_heading = Table(
            [[Paragraph(extra_table['title'], section_heading_style)]],
            colWidths=[doc_w],
        )
        extra_heading.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (0, 0), C_LIGHT),
            ('LINEBEFORE',    (0, 0), (0, 0), 3.5, C_TEAL),
            ('TOPPADDING',    (0, 0), (0, 0), 8),
            ('BOTTOMPADDING', (0, 0), (0, 0), 8),
            ('LEFTPADDING',   (0, 0), (0, 0), 10),
            ('RIGHTPADDING',  (0, 0), (0, 0), 10),
        ]))
        story.append(extra_heading)
        story.append(Spacer(1, 0.08 * inch))
        story.append(_build_summary_table(doc_w, extra_table))


# ---------------------------------------------------------------------------
# Main report builder
# ---------------------------------------------------------------------------

def create_pdf_report(chart_files, output_path, observations, summary_data=None, report_type='sightings'):
    """Create a PDF report with charts and statistics.

    Args:
        chart_files: List of chart file paths
        output_path: Path to save the PDF
        observations: List of observation records
        summary_data: Summary data for tables
        report_type: Type of report - 'sightings' or 'reportings'
    """

    # Validate inputs
    if not chart_files:
        raise ValueError("No chart files provided")

    if not observations:
        raise ValueError("No observations provided")

    for chart_file in chart_files:
        if not os.path.exists(chart_file):
            raise FileNotFoundError(f"Chart file not found: {chart_file}")

    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    L_MARGIN = R_MARGIN = 0.75 * inch
    # topMargin is intentionally small: on content pages the canvas draws a
    # 0.42-inch header bar that lives entirely within the margin area.
    T_MARGIN = 0.65 * inch
    B_MARGIN = 0.75 * inch

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=L_MARGIN,
        rightMargin=R_MARGIN,
        topMargin=T_MARGIN,
        bottomMargin=B_MARGIN,
    )

    doc_w = A4[0] - L_MARGIN - R_MARGIN  # usable content width

    # -----------------------------------------------------------------------
    # Paragraph styles
    # -----------------------------------------------------------------------
    cover_title_style = ParagraphStyle(
        'CoverTitle',
        fontName='Helvetica-Bold',
        fontSize=30,
        textColor=C_WHITE,
        alignment=TA_CENTER,
        leading=38,
    )
    cover_sub_style = ParagraphStyle(
        'CoverSub',
        fontName='Helvetica',
        fontSize=13,
        textColor=C_SKY,
        alignment=TA_CENTER,
        leading=20,
    )
    stat_label_style = ParagraphStyle(
        'StatLabel',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        textColor=C_MUTED,
        alignment=TA_CENTER,
        leading=14,
        spaceAfter=4,
    )
    stat_value_style = ParagraphStyle(
        'StatValue',
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=C_NAVY,
        alignment=TA_CENTER,
        leading=22,
    )
    section_heading_style = ParagraphStyle(
        'SectionHeading',
        fontName='Helvetica-Bold',
        fontSize=11.5,
        textColor=C_NAVY,
        leading=16,
    )

    report_title = 'Reportings Report' if report_type == 'reportings' else 'Sightings Report'
    story = []

    # =======================================================================
    # COVER PAGE
    # =======================================================================

    # Dark header block — title sits inside a NAVY table cell
    cover_table = Table(
        [
            [Paragraph(report_title, cover_title_style)],
            [Paragraph('Data Analysis Report', cover_sub_style)],
        ],
        colWidths=[doc_w],
    )
    cover_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), C_NAVY),
        ('TOPPADDING',    (0, 0), (0,  0),  0.85 * inch),
        ('BOTTOMPADDING', (0, 0), (0,  0),  0.12 * inch),
        ('TOPPADDING',    (0, 1), (0,  1),  0),
        ('BOTTOMPADDING', (0, 1), (0,  1),  0.85 * inch),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0.5 * inch),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0.5 * inch),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(cover_table)

    # Teal accent strip below the dark header block
    accent = Table([['']], colWidths=[doc_w], rowHeights=[0.06 * inch])
    accent.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, 0), C_TEAL)]))
    story.append(accent)

    story.append(Spacer(1, 0.45 * inch))

    # Two-column stats card
    col_w = (doc_w - 0.1 * inch) / 2

    def _stat_cell(label, value):
        inner = Table(
            [[Paragraph(label, stat_label_style)],
             [Paragraph(value, stat_value_style)]],
            colWidths=[col_w - 0.4 * inch],
        )
        inner.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 0.22 * inch),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.22 * inch),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ]))
        return inner

    stats_table = Table(
        [[
            _stat_cell('GENERATED ON', datetime.now().strftime('%d %B %Y')),
            _stat_cell('TOTAL RECORDS', f'{len(observations):,}'),
        ]],
        colWidths=[col_w + 0.05 * inch, col_w + 0.05 * inch],
    )
    stats_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), C_LIGHT),
        ('BOX',           (0, 0), (-1, -1), 0.5, C_BORDER),
        ('INNERGRID',     (0, 0), (-1, -1), 0.5, C_BORDER),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0.2 * inch),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0.2 * inch),
    ]))
    story.append(stats_table)

    story.append(PageBreak())

    # =======================================================================
    # CONTENT PAGES — one chart + table per page
    # =======================================================================
    for i, chart_file in enumerate(chart_files):
        chart_name = os.path.basename(chart_file).lower()
        if '_pie.png' in chart_name:
            img_size = doc_w * 0.78
            img = Image(chart_file, width=img_size, height=img_size)
        else:
            img = Image(chart_file, width=doc_w, height=doc_w * 0.62)
        story.append(img)
        story.append(Spacer(1, 0.28 * inch))

        if summary_data and i < len(summary_data):
            _append_summary_section(story, doc_w, section_heading_style, summary_data[i])

        if (i + 1) < len(chart_files):
            story.append(PageBreak())

    later_cb = partial(_draw_later_pages, report_title=report_title)
    doc.build(story, onFirstPage=_draw_first_page, onLaterPages=later_cb)

    return output_path

