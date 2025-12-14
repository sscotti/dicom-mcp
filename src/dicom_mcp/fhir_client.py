"""
FHIR Client.

This module provides a clean interface for FHIR REST API operations,
abstracting the details of FHIR networking via HTTP.
"""
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime


class FhirClient:
    """FHIR REST API client that handles communication with FHIR servers."""
    
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        """Initialize FHIR client.
        
        Args:
            base_url: FHIR server base URL (e.g., "https://hackathon.siim.org/fhir")
            api_key: Optional API key for authentication (sent as apikey header)
        """
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Accept": "application/fhir+json",
            "Content-Type": "application/fhir+json"
        }
        
        if api_key:
            self.headers["apikey"] = api_key
    
    def search_resource(
        self, 
        resource_type: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Search for FHIR resources.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "ImagingStudy", "Observation")
            params: Search parameters (e.g., {"name": "Smith", "birthdate": "1990-01-01"})
        
        Returns:
            FHIR Bundle resource containing search results
        
        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        url = f"{self.base_url}/{resource_type}"
        response = httpx.get(url, headers=self.headers, params=params or {}, timeout=30.0, verify=False, follow_redirects=True)
        response.raise_for_status()
        return response.json()
    
    def read_resource(
        self, 
        resource_type: str, 
        resource_id: str
    ) -> Dict[str, Any]:
        """Read a specific FHIR resource by ID.
        
        Args:
            resource_type: FHIR resource type (e.g., "Patient", "ImagingStudy")
            resource_id: The logical ID of the resource
        
        Returns:
            The requested FHIR resource
        
        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        url = f"{self.base_url}/{resource_type}/{resource_id}"
        response = httpx.get(url, headers=self.headers, timeout=30.0, verify=False, follow_redirects=True)
        response.raise_for_status()
        return response.json()
    
    def create_resource(
        self, 
        resource: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new FHIR resource or process a Bundle.
        
        Args:
            resource: The FHIR resource to create (must include "resourceType")
                     For Bundles, use type "transaction" or "batch" to process entries
        
        Returns:
            The created FHIR resource with server-assigned ID, or Bundle response
        
        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        resource_type = resource.get("resourceType")
        if not resource_type:
            raise ValueError("Resource must include 'resourceType' field")
        
        # Bundles (transaction, batch) are posted to base endpoint
        if resource_type == "Bundle":
            bundle_type = resource.get("type", "").lower()
            if bundle_type in ("transaction", "batch"):
                # Transaction/batch bundles go to base endpoint
                url = self.base_url
            else:
                # Collection bundles can be posted as regular resources
                url = f"{self.base_url}/Bundle"
        else:
            # Regular resources go to their type endpoint
            url = f"{self.base_url}/{resource_type}"
        
        response = httpx.post(url, headers=self.headers, json=resource, timeout=60.0, verify=False, follow_redirects=True)
        response.raise_for_status()
        return response.json()
    
    def update_resource(
        self, 
        resource: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing FHIR resource.
        
        Args:
            resource: The FHIR resource to update (must include "resourceType" and "id")
        
        Returns:
            The updated FHIR resource
        
        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        resource_type = resource.get("resourceType")
        resource_id = resource.get("id")
        
        if not resource_type:
            raise ValueError("Resource must include 'resourceType' field")
        if not resource_id:
            raise ValueError("Resource must include 'id' field for updates")
        
        url = f"{self.base_url}/{resource_type}/{resource_id}"
        response = httpx.put(url, headers=self.headers, json=resource, timeout=30.0, verify=False, follow_redirects=True)
        response.raise_for_status()
        return response.json()
    
    def verify_connection(self) -> tuple[bool, str]:
        """Verify connectivity to the FHIR server using a capability statement.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            url = f"{self.base_url}/metadata"
            
            # Create a client with more lenient settings
            client = httpx.Client(
                timeout=60.0,
                verify=False,
                follow_redirects=True
            )
            
            try:
                response = client.get(url, headers=self.headers)
                response.raise_for_status()
                metadata = response.json()
                fhir_version = metadata.get("fhirVersion", "unknown")
                return True, f"FHIR server connection successful (FHIR version: {fhir_version})"
            finally:
                client.close()
                
        except httpx.TimeoutException:
            return False, f"Connection to FHIR server timed out. Check network/firewall settings or server availability."
        except httpx.ConnectError as e:
            return False, f"Failed to connect to FHIR server: {str(e)}"
        except httpx.RemoteProtocolError as e:
            return False, f"Server disconnected: {str(e)}. This may indicate network/firewall issues or the server requires specific authentication/headers."
        except httpx.RequestError as e:
            return False, f"Failed to connect to FHIR server: {str(e)}"
        except httpx.HTTPStatusError as e:
            return False, f"FHIR server returned error: {e.response.status_code} {e.response.text}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

