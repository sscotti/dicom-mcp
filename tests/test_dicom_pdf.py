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

# Import the same configuration variables and fixtures from test_dicom_mcp.py
from tests.test_dicom_mcp import (
    ORTHANC_HOST, ORTHANC_PORT, ORTHANC_WEB_PORT, ORTHANC_AET, 
    ORTHANC_USERNAME, ORTHANC_PASSWORD, dicom_config, dicom_client,
    wait_for_orthanc
)


@pytest.fixture(scope="session")
def upload_pdf_dicom():
    """Create and upload a DICOM with encapsulated PDF to Orthanc"""
    # Ensure Orthanc is ready
    assert wait_for_orthanc(), "Orthanc is not available"
    
    # First create a simple PDF
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    c.drawString(100, 750, "Test PDF Document")
    c.drawString(100, 730, "This is a sample PDF for DICOM encapsulation.")
    c.drawString(100, 710, "It contains some text that should be extracted.")
    c.drawString(100, 690, "The extraction functionality should work correctly.")
    c.save()
    pdf_data = pdf_buffer.getvalue()
    
    # Create a new SOP Instance UID
    sop_instance_uid = "1.2.3.4.5.6.7.8.9.3"  # Different from the image SOP Instance UID
    sop_class_uid = "1.2.840.10008.5.1.4.1.1.104.1"  # Encapsulated PDF Storage
    
    # Create the FileMetaDataset
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = sop_class_uid
    file_meta.MediaStorageSOPInstanceUID = sop_instance_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    
    # Simple dataset for testing
    ds = Dataset()
    # Set the file_meta attribute
    ds.file_meta = file_meta
    
    # Patient data
    ds.PatientName = "TEST^PATIENT"
    ds.PatientID = "TEST123"
    ds.PatientBirthDate = "19700101"
    ds.PatientSex = "O"
    
    # Study data
    ds.StudyInstanceUID = "1.2.3.4.5.6.7.8.9.0"  # Same as image Study UID
    ds.StudyDate = "20230101"
    ds.StudyTime = "120000"
    ds.StudyID = "TEST01"
    ds.StudyDescription = "Test Study with PDF"
    ds.AccessionNumber = "ACC123"
    
    # Series data - create a new series for the PDF
    ds.SeriesInstanceUID = "1.2.3.4.5.6.7.8.9.4"  # Different from image Series UID
    ds.SeriesNumber = 2
    ds.Modality = "DOC"  # Document
    ds.SeriesDescription = "PDF Report"
    
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
        
        assert response.status_code == 200, f"Failed to upload PDF DICOM: {response.text}"
        
        # Return the DICOM identifiers for later use
        return {
            "study_instance_uid": ds.StudyInstanceUID,
            "series_instance_uid": ds.SeriesInstanceUID,
            "sop_instance_uid": ds.SOPInstanceUID,
            "expected_text": "Test PDF Document This is a sample PDF for DICOM encapsulation."
        }
        
    finally:
        # Clean up
        os.unlink(temp_path)


def test_extract_pdf_text(dicom_client, upload_pdf_dicom):
    """Test extracting text from a PDF encapsulated in DICOM"""
    # Get the PDF DICOM identifiers
    pdf_info = upload_pdf_dicom
    
    # Call the extraction function
    result = dicom_client.extract_pdf_text_from_dicom(
        study_instance_uid=pdf_info["study_instance_uid"],
        series_instance_uid=pdf_info["series_instance_uid"],
        sop_instance_uid=pdf_info["sop_instance_uid"]
    )
    # Check the result
    assert result["success"], f"Text extraction failed: {result['message']}"
    assert result["text_content"], "No text was extracted from the PDF"
    
    # Check that the expected text is in the extracted content
    expected_text = pdf_info["expected_text"]
    # Remove newlines and extra spaces for comparison
    normalized_content = ' '.join(result["text_content"].replace('\n', ' ').split())
    assert expected_text in normalized_content, f"Expected text not found in extracted content"
    
    # Clean up the temporary file if it exists
    if result["file_path"] and os.path.exists(result["file_path"]):
        try:
            os.unlink(result["file_path"])
        except:
            pass  # Ignore errors when cleaning up