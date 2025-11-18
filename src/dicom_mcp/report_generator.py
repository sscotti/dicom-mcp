"""PDF report generation utilities for radiology reports."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


def generate_radiology_report_pdf(report_data: Dict[str, Any]) -> bytes:
    """Generate a professional radiology report PDF.
    
    Args:
        report_data: Dictionary containing report fields from database:
            - report_number: Report identifier
            - report_status: Status (Preliminary/Final/etc)
            - report_datetime: Report date/time
            - report_text: Findings/body text
            - impression: Clinical impression
            - accession_number: Study accession
            - study_date: Study date
            - study_description: Study description
            - mrn: Patient MRN
            - given_name: Patient first name
            - family_name: Patient last name
            - date_of_birth: Patient DOB
            - sex: Patient sex
            - author_given_name: Radiologist first name (optional)
            - author_family_name: Radiologist last name (optional)
            - credentials: Radiologist credentials (optional)
            
    Returns:
        PDF bytes
    """
    # Create PDF buffer
    buffer = io.BytesIO()
    
    # Create document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
    )
    
    # Container for elements
    story = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=12,
        alignment=1,  # Center
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=6,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        spaceAfter=6,
        fontName='Helvetica'
    )
    
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['BodyText'],
        fontSize=9,
        textColor=colors.HexColor('#555555'),
        fontName='Helvetica'
    )
    
    # Header: Institution name
    story.append(Paragraph("MEDICAL IMAGING CENTER", title_style))
    story.append(Paragraph("Department of Radiology", info_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Report title with status
    status = report_data.get('report_status', 'Preliminary')
    status_color = {
        'Preliminary': colors.orange,
        'Final': colors.green,
        'Amended': colors.blue,
        'Cancelled': colors.red
    }.get(status, colors.grey)
    
    # Report title with status (escape HTML in status text)
    from reportlab.lib.utils import simpleSplit
    report_title_text = f"RADIOLOGY REPORT - {status.upper()}"
    report_title_para = Paragraph(report_title_text, heading_style)
    story.append(report_title_para)
    story.append(Spacer(1, 0.1*inch))
    
    # Patient demographics table
    patient_name = f"{report_data.get('family_name', 'Unknown').upper()}, {report_data.get('given_name', 'Unknown')}"
    dob = report_data.get('date_of_birth', '')
    if dob:
        dob = str(dob)  # Convert date object to string if needed
    
    demographics_data = [
        ['Patient Name:', patient_name, 'MRN:', report_data.get('mrn', 'N/A')],
        ['Date of Birth:', dob, 'Sex:', report_data.get('sex', 'U')],
        ['Accession #:', report_data.get('accession_number', 'N/A'), 'Report #:', report_data.get('report_number', 'N/A')]
    ]
    
    demographics_table = Table(demographics_data, colWidths=[1.3*inch, 2.2*inch, 0.9*inch, 1.6*inch])
    demographics_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#555555')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#555555')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    story.append(demographics_table)
    story.append(Spacer(1, 0.15*inch))
    
    # Study information
    study_date = report_data.get('study_date', '')
    if study_date:
        study_date = str(study_date)
    
    study_info_data = [
        ['Study:', report_data.get('study_description', 'N/A')],
        ['Study Date:', study_date],
        ['Modality:', report_data.get('modality_code', 'N/A')]
    ]
    
    study_table = Table(study_info_data, colWidths=[1.3*inch, 4.7*inch])
    study_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#555555')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    story.append(study_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Findings section
    story.append(Paragraph("FINDINGS:", heading_style))
    
    # Format report text - preserve paragraphs
    report_text = report_data.get('report_text', 'No findings recorded.')
    for paragraph in report_text.split('\n\n'):
        if paragraph.strip():
            story.append(Paragraph(paragraph.strip(), body_style))
    
    story.append(Spacer(1, 0.15*inch))
    
    # Impression section
    story.append(Paragraph("IMPRESSION:", heading_style))
    
    impression = report_data.get('impression', 'No impression recorded.')
    for paragraph in impression.split('\n\n'):
        if paragraph.strip():
            story.append(Paragraph(paragraph.strip(), body_style))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Signature block
    author_name = "Staff Radiologist"
    if report_data.get('author_family_name'):
        author_name = f"{report_data.get('author_given_name', '')} {report_data.get('author_family_name', '')}"
        if report_data.get('provider_type'):
            author_name += f", {report_data.get('provider_type')}"
        if report_data.get('department'):
            author_name += f" ({report_data.get('department')})"
    
    report_datetime = report_data.get('report_datetime', datetime.now())
    if isinstance(report_datetime, str):
        report_datetime_str = report_datetime
    else:
        report_datetime_str = report_datetime.strftime('%Y-%m-%d %H:%M')
    
    # Signature block (no HTML in table cells)
    signature_data = [
        ['Electronically signed by:'],
        [author_name],
        [f"Date/Time: {report_datetime_str}"]
    ]
    
    signature_table = Table(signature_data, colWidths=[6*inch])
    signature_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),  # Bold author name
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#555555')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    story.append(signature_table)
    
    # Footer note
    story.append(Spacer(1, 0.2*inch))
    footer_text = "This report was electronically generated and is legally binding without a handwritten signature."
    story.append(Paragraph(f"<i>{footer_text}</i>", info_style))
    
    # Build PDF
    doc.build(story)
    
    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes

