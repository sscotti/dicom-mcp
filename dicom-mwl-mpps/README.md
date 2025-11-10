# DICOM MWL-MPPS Microservice

DICOM Modality Worklist (MWL) and Modality Performed Procedure Step (MPPS) server with REST API and web interface, development version.

## ✨ Features

- ✅ **DICOM MWL C-FIND SCP**
- ✅ **FastAPI REST Interface**
- ✅ **Web Dashboard** - HTML interface for viewing MWL/MPPS entries
- ✅ **MySQL Database Backend** - Persistent storage with proper schema
- ✅ **Docker Containerized**fessional Testing Suite** - pytest-based integration tests
- ✅ **Development Tools**

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- `make` (optional, but recommended)

### 1. Clone and Start

```bash
git clone <repository-url>
cd dicom-mwl-mpps

# Quick development setup (includes debugging and live reload)
make dev-setup
```

### 2. Verify Everything Works

```bash
# Check service health
make health

# View the web interface
open http://localhost:8000

# Create a test MWL entry and test DICOM functionality
make test-manual
```

### 3. Run Integration Tests

```bash
# Run the full test suite
make test
```

## 🏗️ Architecture

- **dicom-mwl-mpps**: Python DICOM service (pynetdicom/pydicom) - handles MWL/MPPS DIMSE operations
- **mwl-api**: FastAPI REST service - provides HTTP API and web interface  
- **mysql_db**: MySQL database - persistent storage for MWL/MPPS data
- **worklist/**: Shared volume - DICOM .wl files accessible by both services

## 📋 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard with statistics |
| `/health` | GET | Service health check |
| `/mwl` | GET | List MWL entries (web interface) |
| `/mpps` | GET | List MPPS entries (web interface) |
| `/mwl/create_from_json` | POST | Create MWL entry via JSON |
| `/docs` | GET | Interactive API documentation |

## 🛠️ Development Commands

The project includes a comprehensive Makefile for easy development:

```bash
# Get help with all available commands
make help

# Development workflow
make dev-setup          # Start with development settings
make logs               # View all service logs  
make shell              # Get shell access to DICOM service
make db-shell           # MySQL shell access

# Testing
make test               # Run integration tests
make test-manual        # Create test data and run manual DICOM tests

# Database operations  
make db-reset           # Reset database (WARNING: destroys data)
make db-backup          # Backup current database

# Production
make production         # Start in production mode
make health             # Check all service health
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file or set these environment variables:

```bash
# Database Configuration
DB_HOST=mysql_db
DB_USER=root  
DB_PASSWORD=root
DB_NAME=orthanc_ris
DB_PORT=3306

# DICOM Service Configuration
DICOM_AE_TITLE=MWL-MPPS-SCP
DICOM_PORT=104
DICOM_BIND_ADDRESS=0.0.0.0
DICOM_MAX_ASSOC=10

# API Configuration  
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false
API_CORS_ORIGINS=*

# Worklist Configuration
WORKLIST_DIR=/worklist
WORKLIST_MAX_AGE_DAYS=30

# Logging
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### Development vs Production

The project supports different environments:

- **Development**: Use `make dev-setup` - includes debugging, live reload, verbose logging
- **Production**: Use `make production` - optimized settings, no debug ports

## 📝 Usage Examples

### Create MWL Entry via REST API

```bash
curl -X POST http://localhost:8000/mwl/create_from_json \
  -H "Content-Type: application/json" \
  -d '{
    "AccessionNumber": "TEST123",
    "PatientID": "P1",
    "PatientName": "DOE^JOHN", 
    "PatientBirthDate": "19800101",
    "PatientSex": "M",
    "StudyInstanceUID": "1.2.3.4.5",
    "ScheduledProcedureStepSequence": [{
      "ScheduledProcedureStepStartDate": "20240625",
      "ScheduledStationAETitle": "ORTHANC"
    }]
  }'
```

### Query MWL via DICOM C-FIND

```bash
# Using findscu (if available)
findscu localhost 4104 -W -v -d \
  -k "AccessionNumber" \
  -k "PatientName" \
  -k "PatientID"
```

### MPPS Workflow via DICOM

```bash
# The test suite includes automated MPPS testing
make test

# Or create and run manual MPPS tests  
python3 docker/mwl-mpps/create_test_mpps.py
python3 docker/mwl-mpps/test_mpps/test_mpps_client.py localhost 4104 test_mpps/mpps_create.dcm
```

## 🧪 Testing

### Automated Integration Tests

The project includes a comprehensive pytest-based test suite:

```bash
# Run all tests
make test

# Run tests with verbose output
docker compose --profile test run --rm test-runner -v

# Test specific functionality
pytest docker/mwl-mpps/tests/test_mpps_integration.py::TestMWLMPPS::test_mpps_ncreate -v
```

### Manual Testing

```bash
# Create test data and verify DICOM functionality
make test-manual

# Check service health
make health

# View logs for debugging
make logs
```

## 🗄️ Database Schema

The system uses a clean, normalized MySQL schema:

- **`mwl`** - Modality Worklist entries with patient and procedure information
- **`mpps`** - Modality Performed Procedure Step tracking  
- **`dicom_tags`** - Complete DICOM tag reference (4900+ entries)

## 🔍 Monitoring & Health Checks

- **Health endpoint**: `GET /health` - Database connectivity check
- **Service logs**: `make logs` - View real-time logs from all services
- **Database monitoring**: `make db-shell` - Direct MySQL access
- **Web dashboard**: Shows MWL/MPPS statistics and system status

## 🚢 Deployment

### Docker Compose (Recommended)

```bash
# Production deployment
make production

# With custom configuration
docker compose -f docker-compose.yml up -d
```

### Service Ports

- **DICOM Server**: `4104` (mapped from container port 104)
- **REST API**: `8000`  
- **MySQL**: `3306` (development only)

## 🔧 Troubleshooting

### Common Issues

1. **Empty database errors**: Fixed! The API now handles empty databases gracefully
2. **Schema conflicts**: Fixed! Removed conflicting table definitions
3. **Port conflicts**: Use different ports in `.env` if needed
4. **Database initialization**: Use `make db-reset` to reinitialize

### Getting Help

```bash
# Check service health
make health

# View recent logs
make logs

# Reset everything (nuclear option)
make clean && make dev-setup
```

## 📄 License

This project is licensed under the **GNU General Public License v3.0 (GPLv3)**.

**Medical imaging software** - See [LICENSE](LICENSE) for full details.

## 👨‍💻 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and test: `make test`
4. Submit a pull request

---

**DICOM MWL-MPPS implementation ready for medical imaging workflows.**
