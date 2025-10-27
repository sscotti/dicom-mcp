"""
OpenAI Client for DICOM MCP Integration.

This module provides an OpenAI client that can use DICOM MCP tools
for medical image analysis and DICOM server interactions.
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from .config import load_config
from .dicom_client import DicomClient

logger = logging.getLogger(__name__)

class OpenAIDicomClient:
    """OpenAI client integrated with DICOM MCP tools."""
    
    def __init__(self, config_path: str):
        """Initialize the OpenAI DICOM client.
        
        Args:
            config_path: Path to the DICOM MCP configuration file
        """
        # Load .env file if it exists (backup in case config.py didn't load it)
        config_dir = Path(config_path).parent
        env_file = config_dir / '.env'
        if env_file.exists():
            load_dotenv(env_file, override=False)  # Don't override existing env vars
        elif Path('.env').exists():
            load_dotenv('.env', override=False)
        
        self.config = load_config(config_path)
        
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )
        
        self.openai_client = OpenAI(api_key=api_key)
        
        # Get OpenAI configuration
        openai_config = getattr(self.config, 'openai', None)
        if openai_config:
            self.model = openai_config.model
            self.max_tokens = openai_config.max_tokens
            self.temperature = openai_config.temperature
        else:
            # Fallback to defaults if no OpenAI config in YAML
            self.model = 'gpt-4o'
            self.max_tokens = 4000
            self.temperature = 0.1
        
        # Initialize DICOM client
        current_node = self.config.nodes[self.config.current_node]
        self.dicom_client = DicomClient(
            host=current_node.host,
            port=current_node.port,
            calling_aet=self.config.calling_aet,
            called_aet=current_node.ae_title
        )
        
        # Define available DICOM tools
        self.dicom_tools = self._define_dicom_tools()
        
        logger.info(f"OpenAI DICOM client initialized with model: {self.model}")
    
    def _define_dicom_tools(self) -> List[Dict[str, Any]]:
        """Define the DICOM tools available to OpenAI."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "verify_dicom_connection",
                    "description": "Test connectivity to the DICOM server",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_patients",
                    "description": "Search for patients in the DICOM server",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "patient_id": {
                                "type": "string",
                                "description": "Patient ID to search for"
                            },
                            "name_pattern": {
                                "type": "string",
                                "description": "Patient name pattern (supports wildcards like 'DOE*')"
                            },
                            "birth_date": {
                                "type": "string",
                                "description": "Patient birth date (YYYYMMDD format)"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_studies",
                    "description": "Search for studies for a specific patient",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "patient_id": {
                                "type": "string",
                                "description": "Patient ID to search studies for"
                            },
                            "study_date": {
                                "type": "string",
                                "description": "Study date (YYYYMMDD format)"
                            },
                            "modality": {
                                "type": "string",
                                "description": "Study modality (e.g., CT, MR, XR, US)"
                            },
                            "study_description": {
                                "type": "string",
                                "description": "Study description pattern"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_series",
                    "description": "Search for series within a study",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "study_instance_uid": {
                                "type": "string",
                                "description": "Study Instance UID to search series in"
                            },
                            "modality": {
                                "type": "string",
                                "description": "Series modality"
                            },
                            "series_description": {
                                "type": "string",
                                "description": "Series description pattern"
                            }
                        },
                        "required": ["study_instance_uid"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "extract_pdf_text_from_dicom",
                    "description": "Extract text content from a DICOM PDF report",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "study_instance_uid": {
                                "type": "string",
                                "description": "Study Instance UID"
                            },
                            "series_instance_uid": {
                                "type": "string",
                                "description": "Series Instance UID"
                            },
                            "sop_instance_uid": {
                                "type": "string",
                                "description": "SOP Instance UID"
                            }
                        },
                        "required": ["study_instance_uid", "series_instance_uid", "sop_instance_uid"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "move_series",
                    "description": "Move a DICOM series to another destination",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "study_instance_uid": {
                                "type": "string",
                                "description": "Study Instance UID"
                            },
                            "series_instance_uid": {
                                "type": "string",
                                "description": "Series Instance UID"
                            },
                            "destination_aet": {
                                "type": "string",
                                "description": "Destination AE Title"
                            }
                        },
                        "required": ["study_instance_uid", "series_instance_uid", "destination_aet"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_dicom_nodes",
                    "description": "List all configured DICOM nodes with their connection details including AE titles, hosts, ports, and descriptions",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "switch_dicom_node",
                    "description": "Switch the active DICOM node connection to a different configured node",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "node_name": {
                                "type": "string",
                                "description": "Name of the DICOM node to switch to"
                            }
                        },
                        "required": ["node_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_instances",
                    "description": "Find individual DICOM instances within a series",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "series_instance_uid": {
                                "type": "string",
                                "description": "Series Instance UID to search instances in"
                            },
                            "instance_number": {
                                "type": "string",
                                "description": "Instance number to search for"
                            },
                            "sop_instance_uid": {
                                "type": "string",
                                "description": "SOP Instance UID to search for"
                            }
                        },
                        "required": ["series_instance_uid"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "move_study",
                    "description": "Move an entire DICOM study to another destination",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "study_instance_uid": {
                                "type": "string",
                                "description": "Study Instance UID"
                            },
                            "destination_aet": {
                                "type": "string",
                                "description": "Destination AE Title"
                            }
                        },
                        "required": ["study_instance_uid", "destination_aet"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_attribute_presets",
                    "description": "Get all available attribute presets for DICOM queries",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]
    
    def _execute_dicom_function(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a DICOM function call."""
        try:
            if function_name == "verify_dicom_connection":
                success, message = self.dicom_client.verify_connection()
                return {"success": success, "message": message}
            
            elif function_name == "query_patients":
                results = self.dicom_client.query_patient(**arguments)
                return {"success": True, "results": results, "count": len(results)}
            
            elif function_name == "query_studies":
                results = self.dicom_client.query_study(**arguments)
                return {"success": True, "results": results, "count": len(results)}
            
            elif function_name == "query_series":
                results = self.dicom_client.query_series(**arguments)
                return {"success": True, "results": results, "count": len(results)}
            
            elif function_name == "extract_pdf_text_from_dicom":
                result = self.dicom_client.extract_pdf_text_from_dicom(**arguments)
                return result
            
            elif function_name == "move_series":
                result = self.dicom_client.move_series(**arguments)
                return result
            
            elif function_name == "list_dicom_nodes":
                # Return information about configured nodes
                current_node = self.config.current_node
                nodes = []
                for node_name, node in self.config.nodes.items():
                    nodes.append({
                        "name": node_name,
                        "host": node.host,
                        "port": node.port,
                        "ae_title": node.ae_title,
                        "description": node.description,
                        "is_current": node_name == current_node
                    })
                return {
                    "success": True,
                    "current_node": current_node,
                    "calling_aet": self.config.calling_aet,
                    "nodes": nodes
                }
            
            elif function_name == "switch_dicom_node":
                node_name = arguments.get("node_name")
                if node_name not in self.config.nodes:
                    return {"success": False, "error": f"Node '{node_name}' not found in configuration"}
                
                # Update current node and reinitialize DICOM client
                self.config.current_node = node_name
                current_node = self.config.nodes[node_name]
                self.dicom_client = DicomClient(
                    host=current_node.host,
                    port=current_node.port,
                    calling_aet=self.config.calling_aet,
                    called_aet=current_node.ae_title
                )
                return {
                    "success": True,
                    "message": f"Switched to DICOM node: {node_name}",
                    "current_node": node_name
                }
            
            elif function_name == "query_instances":
                results = self.dicom_client.query_instance(**arguments)
                return {"success": True, "results": results, "count": len(results)}
            
            elif function_name == "move_study":
                result = self.dicom_client.move_study(**arguments)
                return result
            
            elif function_name == "get_attribute_presets":
                from .attributes import get_attributes_for_level
                presets = {
                    "patient": get_attributes_for_level("patient"),
                    "study": get_attributes_for_level("study"), 
                    "series": get_attributes_for_level("series"),
                    "instance": get_attributes_for_level("instance")
                }
                return {"success": True, "presets": presets}
            
            else:
                return {"success": False, "error": f"Unknown function: {function_name}"}
        
        except Exception as e:
            logger.error(f"Error executing {function_name}: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def chat(self, message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Send a message to OpenAI with DICOM tool capabilities.
        
        Args:
            message: The user's message
            conversation_history: Previous conversation messages
            
        Returns:
            Dictionary containing the response and any tool calls made
        """
        # Build messages
        messages = []
        
        # System message with DICOM context
        system_message = """You are a medical AI assistant with access to DICOM server tools. You can:

1. Search for patients, studies, and series in DICOM servers
2. Extract text from DICOM PDF reports (radiology reports, etc.)
3. Move DICOM data between servers
4. Verify DICOM server connectivity

When analyzing medical data:
- Always prioritize patient safety and privacy
- Provide clear, accurate information
- Suggest appropriate follow-up actions when relevant
- Use proper medical terminology
- Be cautious about making diagnostic conclusions

Available DICOM tools:
- verify_dicom_connection: Test server connectivity
- query_patients: Search for patients by ID, name, or birth date
- query_studies: Find studies by patient ID, date, modality, or description
- query_series: Find series within a study
- query_instances: Find individual DICOM instances within a series
- extract_pdf_text_from_dicom: Extract text from DICOM PDF reports
- move_series: Transfer DICOM series to other destinations
- move_study: Transfer entire DICOM studies to other destinations
- list_dicom_nodes: List all configured DICOM servers
- switch_dicom_node: Change the active DICOM server connection
- get_attribute_presets: Show available query detail levels and attributes

Always use these tools when the user asks about medical images, reports, or DICOM data."""

        messages.append({"role": "system", "content": system_message})
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        try:
            # Make initial request to OpenAI
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.dicom_tools,
                tool_choice="auto",
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            # Handle tool calls
            if tool_calls:
                # Add assistant message with tool calls to conversation
                messages.append({
                    "role": "assistant",
                    "content": response_message.content,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        }
                        for tool_call in tool_calls
                    ]
                })
                
                # Execute tool calls
                tool_results = []
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"Executing DICOM tool: {function_name} with args: {arguments}")
                    
                    result = self._execute_dicom_function(function_name, arguments)
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "function_name": function_name,
                        "result": result
                    })
                    
                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(result),
                        "tool_call_id": tool_call.id
                    })
                
                # Get final response with tool results
                final_response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                
                return {
                    "success": True,
                    "response": final_response.choices[0].message.content,
                    "tool_calls": tool_results,
                    "conversation": messages
                }
            
            else:
                # No tool calls needed
                return {
                    "success": True,
                    "response": response_message.content,
                    "tool_calls": [],
                    "conversation": messages
                }
        
        except Exception as e:
            logger.error(f"Error in OpenAI chat: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "response": "I encountered an error processing your request. Please try again.",
                "tool_calls": [],
                "conversation": messages
            }
