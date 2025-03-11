from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
from pydicom.dataset import Dataset

from pynetdicom import AE, debug_logger
from pynetdicom.sop_class import PatientRootQueryRetrieveInformationModelFind

debug_logger()

# Initialize FastMCP server
mcp = FastMCP("dicom")

# Constants
USER_AGENT = "dicom-app/1.0"

def format_study(study: dict) -> str:
    return f"""
Patient Name: {study.get('PatientName', 'Unknown')}
Patient ID: {study.get('PatientID', 'Unknown')}
Study Date: {study.get('StudyDate', 'Unknown')}
Study Description: {study.get('StudyDescription', 'Unknown')}
Study Instance UID: {study.get('StudyInstanceUID', 'Unknown')}
Modality: {study.get('ModalitiesInStudy', 'Unknown')}
Accession Number: {study.get('AccessionNumber', 'Unknown')}
"""

def make_study_request(PatientName:str):

    ae = AE()
    ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind)

    # Create our Identifier (query) dataset
    ds = Dataset()
    ds.PatientName = PatientName
    ds.QueryRetrieveLevel = 'PATIENT'
    ds.StudyDescription = ""
    ds.StudyInstanceUID = ""
    ds.PatientID = ""
    ds.StudyDate = ""
    ds.AccessionNumber = ""

    # List to store study dictionaries
    studies = []

    # Associate with the peer AE
    assoc = ae.associate("localhost", 4242)
    if assoc.is_established:
        # Send the C-FIND request
        responses = assoc.send_c_find(ds, PatientRootQueryRetrieveInformationModelFind)
        
        for status, identifier in responses:
            if status and status.Status == 0xFF00 and identifier is not None:
                # Convert the entire dataset to a dictionary
                study_dict = {}
                for elem in identifier:
                    if elem.keyword:  # Only process elements with defined keywords
                        study_dict[elem.keyword] = elem.value
                
                studies.append(study_dict)
            elif not status:
                print('Connection timed out, was aborted or received invalid response')

        # Release the association
        assoc.release()
        
    else:
        print('Association rejected, aborted or never connected')

    return studies

@mcp.tool()
def get_studies(PatientName:str):
    """Make a request to the dicom server to retrieve metadata about the medical studies belonging to the patient"""
    studies = make_study_request(PatientName)
    formatted_studies = [format_study(study) for study in studies]
    return (f"Found {len(studies)} studies\n---\n" + "\n---\n".join(formatted_studies))

if __name__ == "__main__":
    # Initialize and run the server
    #get_studies("Anonymized1")
    mcp.run(transport='stdio')