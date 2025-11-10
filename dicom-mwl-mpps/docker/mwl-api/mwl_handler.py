import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import generate_uid
import json
import logging
from datetime import datetime

def create_mwl_from_json(json_data):
    """
    Create a DICOM MWL dataset from JSON data using recursion
    """
    ds = Dataset()
    
    def set_dataset_value(dataset, key, value):
        """Recursively set DICOM dataset values"""
        if isinstance(value, dict):
            # Create a sequence
            seq = []
            seq_item = Dataset()
            for k, v in value.items():
                set_dataset_value(seq_item, k, v)
            seq.append(seq_item)
            setattr(dataset, key, seq)
        elif isinstance(value, list):
            # Handle sequences with multiple items
            seq = []
            for item in value:
                seq_item = Dataset()
                if isinstance(item, dict):
                    for k, v in item.items():
                        set_dataset_value(seq_item, k, v)
                seq.append(seq_item)
            setattr(dataset, key, seq)
        else:
            # Set simple value
            setattr(dataset, key, value)

    # Process each key-value pair in the JSON
    for key, value in json_data.items():
        try:
            set_dataset_value(ds, key, value)
        except Exception as e:
            logging.error(f"Error setting {key}: {str(e)}")
            raise

    # Add required MWL attributes if not present
    if not hasattr(ds, 'StudyInstanceUID'):
        ds.StudyInstanceUID = generate_uid()
    
    if not hasattr(ds, 'ScheduledProcedureStepStartDate'):
        ds.ScheduledProcedureStepStartDate = datetime.now().strftime('%Y%m%d')
    
    if not hasattr(ds, 'ScheduledProcedureStepStartTime'):
        ds.ScheduledProcedureStepStartTime = datetime.now().strftime('%H%M%S')

    return ds

def create_mwl_file(json_data, output_path=None):
    """
    Create a DICOM MWL file from JSON data
    """
    try:
        ds = create_mwl_from_json(json_data)
        
        # Add file meta information
        file_meta = Dataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.31'  # Modality Worklist Information Model
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.ImplementationClassUID = generate_uid()
        file_meta.TransferSyntaxUID = '1.2.840.10008.1.2.1'  # Explicit VR Little Endian
        
        # Create the final dataset
        final_ds = FileDataset(output_path if output_path else "", {}, file_meta=file_meta, preamble=b"\0" * 128)
        final_ds.update(ds)
        
        # Save to file if path provided
        if output_path:
            final_ds.save_as(output_path, enforce_file_format=True)
        
        return final_ds
    except Exception as e:
        logging.error(f"Error creating MWL file: {str(e)}")
        raise

def handle_mwl_request(output, query):
    """
    Handle MWL C-FIND requests
    """
    try:
        # Convert query to Dataset
        query_ds = Dataset()
        for tag, value in query.items():
            setattr(query_ds, tag, value)
        
        # TODO: Implement your matching logic here
        # This is where you would query your database or file system
        # and return matching MWL entries
        
        return []  # Return empty list for now
    except Exception as e:
        logging.error(f"Error handling MWL request: {str(e)}")
        raise

