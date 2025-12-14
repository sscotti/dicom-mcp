# FHIR Server Configuration Guide

This guide explains how to configure and use different FHIR servers with the DICOM MCP server.

## Available FHIR Servers

### 1. Firely Test Server (Recommended for Development)

**URL**: `https://server.fire.ly`

**Features:**

- Public test server (no API key required)
- FHIR R4 compliant
- Reliable and always available
- Good for testing and development

**Configuration:**

```yaml
fhir_servers:
  firely:
    base_url: "https://server.fire.ly"
    description: "Firely FHIR Test Server (public, no API key needed)"

current_fhir: "firely"
```

**Reference**: [Firely Server](https://server.fire.ly)

### 2. SIIM Hackathon Server

**URL**: `https://hackathon.siim.org/fhir`

**Features:**

- SIIM-specific FHIR server
- Requires API key authentication
- May require VPN or network access

**Configuration:**

```yaml
fhir_servers:
  siim:
    base_url: "https://hackathon.siim.org/fhir"
    api_key: "${SIIM_API_KEY}"  # Set in .env file
    description: "SIIM Hackathon FHIR server"

current_fhir: "siim"
```

**Setup:**

1. Add `SIIM_API_KEY=your-key-here` to your `.env` file
2. Set `current_fhir: "siim"` in `configuration.yaml`

### 3. Local HAPI FHIR Server

**URL**: `http://localhost:8080/fhir`

**Features:**

- Full control over the server
- No network dependencies
- Good for local development and testing
- Can load test data

**Setup:**

1. **Start HAPI FHIR Server:**

```bash
cd tests
docker-compose -f docker-compose-fhir.yaml up -d
```

2. **Verify it's running:**

```bash
curl http://localhost:8080/fhir/metadata
```

3. **Configure in `configuration.yaml`:**

```yaml
fhir_servers:
  hapi_local:
    base_url: "http://localhost:8080/fhir"
    description: "Local HAPI FHIR server"

current_fhir: "hapi_local"
```

4. **Access HAPI UI:**

- HAPI JPA Server UI: <http://localhost:8080/hapi-fhir-jpaserver/>
- Base FHIR endpoint: <http://localhost:8080/fhir>

**Stop HAPI Server:**

```bash
docker-compose -f docker-compose-fhir.yaml down
```

## Using Multiple FHIR Servers

You can configure multiple FHIR servers in `configuration.yaml`:

```yaml
fhir_servers:
  firely:
    base_url: "https://server.fire.ly"
    description: "Firely FHIR Test Server"
  
  siim:
    base_url: "https://hackathon.siim.org/fhir"
    api_key: "${SIIM_API_KEY}"
    description: "SIIM Hackathon FHIR server"
  
  hapi_local:
    base_url: "http://localhost:8080/fhir"
    description: "Local HAPI FHIR server"

current_fhir: "firely"  # Switch to firely, siim, or hapi_local
```

## Switching FHIR Servers

You can switch between configured FHIR servers in two ways:

### Method 1: Dynamic Switching (Recommended - No Restart Required)

Use the `switch_fhir_server` tool to change servers without restarting:

```python
# Example: Switch to SIIM server
switch_fhir_server(server_name="siim")

# Verify the switch
verify_fhir_connection()
```

This is the preferred method as it doesn't require restarting the MCP server.

### Method 2: Configuration File (Requires Restart)

1. **Update `configuration.yaml`:**
   - Change `current_fhir: "server_name"` to the desired server

2. **Restart MCP Server:**
   - The MCP server needs to be restarted for the change to take effect

3. **Verify with tools:**
   - Use `list_fhir_servers` to see available servers
   - Use `verify_fhir_connection` to test the current server

## Available FHIR Tools

Once a FHIR server is configured, you'll have access to:

- `verify_fhir_connection` - Test FHIR server connectivity
- `list_fhir_servers` - List configured FHIR servers
- `switch_fhir_server` - Switch to a different FHIR server without restarting
- `fhir_search_patient` - Search for Patient resources
- `fhir_search_imaging_study` - Search for ImagingStudy resources
- `fhir_read_resource` - Read any FHIR resource by type and ID
- `fhir_create_resource` - Create new FHIR resources
- `fhir_update_resource` - Update existing FHIR resources

## Troubleshooting

### Connection Timeouts

If you see connection timeouts:

- Check network/firewall settings
- Verify the server URL is correct
- Test with `curl` to see if the server is reachable
- For SIIM, check if VPN or IP whitelisting is required

### SSL Errors

If you see SSL errors:

- The code already has SSL verification disabled for development
- Try HTTP instead of HTTPS if the server supports it
- Check if the server requires specific TLS versions

### API Key Issues

If authentication fails:

- Verify the API key is set in `.env` file
- Check that the environment variable name matches (`SIIM_API_KEY`)
- Ensure the API key format is correct for the server
