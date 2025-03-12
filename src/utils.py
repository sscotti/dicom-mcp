"""
Utility functions for DICOM MCP Server.
"""

from typing import Dict, Any, List

from pydicom.dataset import Dataset


def dataset_to_dict(dataset: Dataset) -> Dict[str, Any]:
    """Convert a DICOM dataset to a dictionary.
    
    Args:
        dataset: DICOM dataset
        
    Returns:
        Dictionary representation of the dataset
    """
    # Handle nested sequences
    if hasattr(dataset, "is_empty") and dataset.is_empty():
        return {}
    
    result = {}
    for elem in dataset:
        if elem.VR == "SQ":
            # Handle sequences
            result[elem.name] = [dataset_to_dict(item) for item in elem.value]
        else:
            # Handle regular elements
            if hasattr(elem, "name"):
                try:
                    if elem.VM > 1:
                        # Multiple values
                        result[elem.name] = list(elem.value)
                    else:
                        # Single value
                        result[elem.name] = elem.value
                except Exception:
                    # Fall back to string representation
                    result[elem.name] = str(elem.value)
    
    return result


def handle_c_find_response(responses) -> List[Dict[str, Any]]:
    """Process C-FIND responses and convert them to dictionaries.
    
    Args:
        responses: Iterator of (status, dataset) tuples from C-FIND
        
    Returns:
        List of dictionaries representing the results
    """
    results = []
    
    for (status, dataset) in responses:
        if status and status.Status == 0xFF00:  # Pending
            if dataset:
                results.append(dataset_to_dict(dataset))
    
    return results