from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import os

def create_pdf_report(chart_files, output_path, observations, summary_data=None, report_type='sightings'):
    """Create a PDF report with charts and statistics
    
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
    
    # Verify all chart files exist
    for chart_file in chart_files:
        if not os.path.exists(chart_file):
            raise FileNotFoundError(f"Chart file not found: {chart_file}")
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=32,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=40,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    # === FIRST PAGE - Title Page ===
    # Add some top spacing
    story.append(Spacer(1, 2.5*inch))
    
    # Title - dynamic based on report type
    report_title = "Reportings Report" if report_type == 'reportings' else "Sightings Report"
    title = Paragraph(report_title, title_style)
    story.append(title)
    story.append(Spacer(1, 0.8*inch))
    
    # Date - centered
    date_info = Paragraph(f"<b>Report Generated</b><br/>{datetime.now().strftime('%B %d, %Y')}<br/>{datetime.now().strftime('%I:%M %p')}", info_style)
    story.append(date_info)
    story.append(Spacer(1, 0.5*inch))
    
    # Dataset info - centered
    dataset_info = Paragraph(f"<b>Total Observations</b><br/>{len(observations)} records", info_style)
    story.append(dataset_info)
    
    # End of title page
    story.append(PageBreak())
    
    # === SUBSEQUENT PAGES - One chart + table per page ===
    for i, chart_file in enumerate(chart_files):
        # Add chart image
        img = Image(chart_file, width=6.5*inch, height=4.55*inch)
        story.append(img)
        story.append(Spacer(1, 0.4*inch))
        
        # Add summary table if available
        if summary_data and i < len(summary_data):
            table_title = Paragraph(f"<b>{summary_data[i]['title']}</b>", styles['Heading3'])
            story.append(table_title)
            story.append(Spacer(1, 0.15*inch))
            
            # Create table data
            table_data = [['Category', 'Frequency']]
            for category, freq in summary_data[i]['data']:
                table_data.append([str(category).replace('_', ' ').title(), str(freq)])
            
            # Create table
            summary_table = Table(table_data, colWidths=[4*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ]))
            story.append(summary_table)
        
        # Add page break after each chart-table pair (except the last one)
        if (i + 1) < len(chart_files):
            story.append(PageBreak())
    
    # Build PDF
    doc.build(story)
    
    return output_path
