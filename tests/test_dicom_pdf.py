"""
Test extracting text from PDFs encapsulated in DICOM.
"""
import io
import os
import tempfile
import pytest
import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian
import re
from datetime import datetime
from dicom_mcp.dicom_client import DicomClient
# Import the same configuration variables and fixtures from test_dicom_mcp.py
from tests.test_dicom_mcp import (
    ORTHANC_HOST, ORTHANC_PORT, ORTHANC_WEB_PORT, ORTHANC_AET, 
    ORTHANC_USERNAME, ORTHANC_PASSWORD, dicom_config, dicom_client,
    wait_for_orthanc
)

# Helper function to wait for Orthanc
def wait_for_orthanc():
    """Check if Orthanc is available"""
    try:
        response = requests.get(f"http://{ORTHANC_HOST}:{ORTHANC_WEB_PORT}/system")
        return response.status_code == 200
    except:
        return False

def parse_date_from_report(date_string):
    """Parse dates from report format (DD-MM-YYYY) to DICOM format (YYYYMMDD)"""
    # Extract date in DD-MM-YYYY format and convert to YYYYMMDD
    try:
        dt = datetime.strptime(date_string, "%d-%m-%Y")
        return dt.strftime("%Y%m%d")
    except ValueError:
        # Return a default date if parsing fails
        return "20240101"

def extract_study_date(report_text):
    """Extract date from report title line"""
    date_match = re.search(r'\((\d{2}-\d{2}-\d{4})\)', report_text)
    if date_match:
        return parse_date_from_report(date_match.group(1))
    return "20240101"  # Default date

def create_pdf_from_report(report_text):
    """Create a PDF from the report text"""
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    
    # Simple formatting for the PDF
    y_position = 750
    for line in report_text.split('\n'):
        # Handle headers with larger font
        if line.startswith('# '):
            c.setFont("Helvetica-Bold", 14)
            c.drawString(100, y_position, line[2:])
            y_position -= 20
        elif line.startswith('## '):
            c.setFont("Helvetica-Bold", 12)
            c.drawString(100, y_position, line[3:])
            y_position -= 20
        elif line.startswith('---'):
            # Draw a line for separators
            c.line(100, y_position, 500, y_position)
            y_position -= 10
        elif line.strip():
            c.setFont("Helvetica", 10)
            # Wrap text if too long
            words = line.split()
            current_line = ""
            for word in words:
                test_line = current_line + " " + word if current_line else word
                if c.stringWidth(test_line, "Helvetica", 10) < 400:
                    current_line = test_line
                else:
                    c.drawString(100, y_position, current_line)
                    y_position -= 15
                    current_line = word
            if current_line:
                c.drawString(100, y_position, current_line)
                y_position -= 15
        else:
            # Empty line
            y_position -= 10
            
        # Check if we need a new page
        if y_position < 50:
            c.showPage()
            y_position = 750
    
    c.save()
    return pdf_buffer.getvalue()

@pytest.fixture(scope="session")
def upload_pdf_dicom():
    """Create and upload multiple DICOMs with encapsulated PDFs to Orthanc from markdown content"""
    # Ensure Orthanc is ready
    assert wait_for_orthanc(), "Orthanc is not available"
    
    # Read the markdown file content
    with open('tests/synthetic-pet-ct-reports.md', 'r') as file:
        markdown_content = file.read()
    
    # Split the content into individual reports
    reports = re.split(r'(?=# Rapport \d+:)', markdown_content)
    reports = [r for r in reports if r.strip()]  # Remove empty reports
    
    # Base study UID prefix - each report will get a unique study UID
    study_uid_prefix = "1.2.3.4.5.6.7.8.9"
    
    uploaded_reports = []
    
    for i, report_text in enumerate(reports, 1):
        # Extract report date
        study_date = extract_study_date(report_text)
        
        # Create PDF from report
        pdf_data = create_pdf_from_report(report_text)
        
        # Create a new SOP Instance UID and Series UID for each report
        sop_instance_uid = f"1.2.3.4.5.6.7.8.9.{10+i}"
        series_instance_uid = f"1.2.3.4.5.6.7.8.9.{20+i}"
        sop_class_uid = "1.2.840.10008.5.1.4.1.1.104.1"  # Encapsulated PDF Storage
        
        # Create the FileMetaDataset
        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = sop_class_uid
        file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
        file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        
        # Create the dataset
        ds = Dataset()
        ds.file_meta = file_meta
        
        # Patient data - same for all reports
        ds.PatientName = "John Doe"
        ds.PatientID = "DLBCL2024"
        ds.PatientBirthDate = "19700101"
        ds.PatientSex = "O"
        
        # Create unique Study UID for each study
        ds.StudyInstanceUID = f"{study_uid_prefix}.{100+i}"  # Unique study UID for each report
        ds.StudyDate = study_date
        ds.StudyTime = "120000"
        ds.StudyID = f"DLBCL{i}"
        
        # Extract title for study description
        title_match = re.search(r'# Rapport \d+: (.*?)[\n\r]', report_text)
        if title_match:
            ds.StudyDescription = f"PET/CT - {title_match.group(1)}"
        else:
            ds.StudyDescription = f"PET/CT Report {i}"
            
        ds.AccessionNumber = f"ACC{i}2024"
        
        # Series data
        ds.SeriesInstanceUID = series_instance_uid
        ds.SeriesNumber = i
        ds.Modality = "DOC"  # Document
        ds.SeriesDescription = f"PET/CT Report {i}"
        
        # Instance data
        ds.SOPInstanceUID = sop_instance_uid
        ds.SOPClassUID = sop_class_uid
        ds.InstanceNumber = 1
        
        # Add the PDF data
        ds.MIMETypeOfEncapsulatedDocument = "application/pdf"
        ds.EncapsulatedDocument = pdf_data
        
        # Save to file
        with tempfile.NamedTemporaryFile(suffix='.dcm', delete=False) as temp:
            ds.save_as(temp.name, write_like_original=False)
            temp_path = temp.name
        
        try:
            # Upload via HTTP
            with open(temp_path, 'rb') as f:
                dicom_data = f.read()
            
            # Try auth if credentials provided
            if ORTHANC_USERNAME and ORTHANC_PASSWORD:
                response = requests.post(
                    f"http://{ORTHANC_HOST}:{ORTHANC_WEB_PORT}/instances",
                    data=dicom_data,
                    auth=(ORTHANC_USERNAME, ORTHANC_PASSWORD),
                    headers={'Content-Type': 'application/dicom'}
                )
            else:
                response = requests.post(
                    f"http://{ORTHANC_HOST}:{ORTHANC_WEB_PORT}/instances",
                    data=dicom_data,
                    headers={'Content-Type': 'application/dicom'}
                )
            
            assert response.status_code == 200, f"Failed to upload PDF DICOM {i}: {response.text}"
            
            # Store the report info
            uploaded_reports.append({
                "report_number": i,
                "study_instance_uid": ds.StudyInstanceUID,
                "series_instance_uid": series_instance_uid,
                "sop_instance_uid": sop_instance_uid,
                "description": ds.StudyDescription
            })
            
            print(f"Uploaded report {i}: {ds.StudyDescription}")
            
        finally:
            # Clean up
            os.unlink(temp_path)
    
    return uploaded_reports
def test_extract_pdf_text(dicom_client:DicomClient, upload_pdf_dicom):
    """Test extracting text from a PDF encapsulated in DICOM"""
    # Get the PDF DICOM identifiers
    pdf_info = upload_pdf_dicom[0]
    
    # Call the extraction function
    result = dicom_client.extract_pdf_text_from_dicom(
        study_instance_uid=pdf_info["study_instance_uid"],
        series_instance_uid=pdf_info["series_instance_uid"],
        sop_instance_uid=pdf_info["sop_instance_uid"]
    )
    
    # Check the result
    assert result["success"], f"Text extraction failed: {result['message']}"
    assert result["text_content"], "No text was extracted from the PDF"
    
    # Clean up the temporary file if it exists
    if result["file_path"] and os.path.exists(result["file_path"]):
        try:
            os.unlink(result["file_path"])
        except:
            pass  # Ignore errors when cleaning up